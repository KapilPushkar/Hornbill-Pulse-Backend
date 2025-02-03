import numpy as np
import os
import calendar
import matplotlib.pyplot as plt
from shapely.geometry import Polygon
import rasterio
from rasterio.mask import mask
from pyproj import Transformer
from shapely.ops import transform
from app.services.copernicus_api import CDSEApi
from functools import lru_cache
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import seaborn as sns
from statistics import mean
from scipy.interpolate import PchipInterpolator
import pdfkit
import shutil
from ..repositories.land import LandRepository
from typing import List
from ..repositories.vegetation import VegetationRepository
from bson import ObjectId

def get_empty_stats():
    return {
        'mean_ndvi': 0,
        'max_ndvi': 0,
        'min_ndvi': 0,
        'total_pixels': 0,
        'water_contained_pixels': 0,
        'bare_soil_pixels': 0,
        'grass_pixels': 0,
        'dense_shrub_pixels': 0,
        'tree_pixels': 0
    }

@lru_cache(maxsize=1)
def get_copernicus_client():
    return CDSEApi()

def calculate_vegetation_stats(bands, coordinates):
    if not bands or not coordinates:
        return get_empty_stats()
    try:
        swapped_coordinates = [[coord[1], coord[0]] for coord in coordinates]
        polygon = Polygon(swapped_coordinates)

        with rasterio.open(bands['B04']) as red:
            transformer = Transformer.from_crs("EPSG:4326", red.crs, always_xy=True)
            def transform_func(x, y):
                return transformer.transform(x, y)
            polygon_transformed = transform(transform_func, polygon)
            red_masked, _ = mask(red, [polygon_transformed], crop=True)
            red_band = red_masked[0].astype(float)
            
        with rasterio.open(bands['B08']) as nir:
            transformer = Transformer.from_crs("EPSG:4326", nir.crs, always_xy=True)
            def transform_func(x, y):
                return transformer.transform(x, y)
            polygon_transformed = transform(transform_func, polygon)
            nir_masked, _ = mask(nir, [polygon_transformed], crop=True)
            nir_band = nir_masked[0].astype(float)
            
        ndvi = np.where(
            (nir_band + red_band) > 0,
            (nir_band - red_band) / (nir_band + red_band + 1e-8),
            -2
        )
        valid_pixels = ndvi[ndvi != -2]
        total_pixels = valid_pixels.size
        water_contained_condition = np.logical_and(valid_pixels >= -1, valid_pixels < 0)
        water_contained_pixels = np.sum(water_contained_condition)
        bare_soil_condition = np.logical_and(valid_pixels >= 0, valid_pixels < 0.2)
        bare_soil_pixels = np.sum(bare_soil_condition)
        grass_condition = np.logical_and(valid_pixels >= 0.2, valid_pixels < 0.4)
        grass_pixels = np.sum(grass_condition)
        dense_shrub_condition = np.logical_and(valid_pixels >= 0.4, valid_pixels < 0.6)
        dense_shrub_pixels = np.sum(dense_shrub_condition)
        tree_condition = np.logical_and(valid_pixels >= 0.6, valid_pixels < 1)
        tree_pixels = np.sum(tree_condition)
        vegetation_pixels = grass_pixels + dense_shrub_pixels + tree_pixels
        
        if total_pixels>0:
            stats = {
                'mean_ndvi': round(float(np.mean(valid_pixels)), 3),
                'max_ndvi': round(float(np.max(valid_pixels)), 3),
                'min_ndvi': round(float(np.min(valid_pixels)), 3),
                'total_pixels': total_pixels,
                'water_contained_pixels': water_contained_pixels,
                'bare_soil_pixels': bare_soil_pixels,
                'grass_pixels': grass_pixels,
                'dense_shrub_pixels': dense_shrub_pixels,
                'tree_pixels': tree_pixels,
                'vegetation_pixels': vegetation_pixels
            }
        else:
            stats = get_empty_stats()
        return stats
        
    except Exception as e:
        return get_empty_stats()

def get_bands_directory(product_id, year, month):
    base_dir = "satellite_images/bands"
    year_month_dir = os.path.join(base_dir, f"{product_id}_{year}_{month:02d}")
    os.makedirs(year_month_dir, exist_ok=True)
    return year_month_dir

class VegetationService:
    def __init__(self):
        self.repository = VegetationRepository()

async def generate_land_analysis_report(userId: str, land_id: str, coordinates: List[List[float]]):
    land_repository = LandRepository()
    await land_repository.update_one({"_id": ObjectId(land_id)}, {"$set": {"status": "Processing"}})

    current_year = datetime.now().year
    yearly_data = {}
    
    for year in range(current_year-3, current_year+1):
        monthly_data = await get_monthly_vegetation_stats(coordinates, year)
        yearly_data[str(year)] = monthly_data
    
    vegetation_stats = {
        "land_id": land_id,
        "yearly_data": yearly_data,
        "created_at": datetime.utcnow()
    }
    
    vegetation_repository = VegetationRepository()
    stored_stats = await vegetation_repository.create(vegetation_stats)
    
    # report_path = generate_html_report(land_id, yearly_data)
    
    # if stored_stats:
    #     await vegetation_repository.update_report_path(
    #         str(stored_stats["_id"]), 
    #         report_path
    #     )
    await land_repository.update_one({"_id": ObjectId(land_id)}, {"$set": {"status": "Processed"}})
    
    return "Vegetation analysis report generated"

async def get_monthly_vegetation_stats(coordinates: List[List[float]], year: int = 2024):
    client = get_copernicus_client()
    monthly_data = []
    
    for month in range(1, 13):
        _, last_day = calendar.monthrange(year, month)
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day}"
        
        try:
            processed_results = client.process_area_temporal(
                coordinates, 
                start_date, 
                end_date,
                band_names=['B04', 'B08']
            )
            
            if processed_results:
                first_date = list(processed_results.keys())[0]
                bands = processed_results[first_date]
                
                stats = calculate_vegetation_stats(bands, coordinates)
                stats['month'] = calendar.month_name[month]
                monthly_data.append(stats)
                
                for band_path in bands.values():
                    if os.path.exists(band_path):
                        os.remove(band_path)
            else:
                print(f"No data available for {calendar.month_name[month]} {year}")
                stats = get_empty_stats()
                stats['month'] = calendar.month_name[month]
                monthly_data.append(stats)
                
        except Exception as e:
            print(f"Error processing {calendar.month_name[month]}: {e}")
            stats = get_empty_stats()
            stats['month'] = calendar.month_name[month]
            monthly_data.append(stats)
    
    return monthly_data

def plot_vegetation_trends(monthly_data, output_path="satellite_images/vegetation_trends.png"):
    months = [data['month'] for data in monthly_data]
    veg_percentages = [data['vegetation_percentage'] for data in monthly_data]
    mean_ndvis = [data['mean_ndvi'] for data in monthly_data]
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    ax1.plot(months, veg_percentages, marker='o', color='green')
    ax1.set_title('Area under vegetation')
    ax1.set_xlabel('Month')
    ax1.set_ylabel('Vegetation Coverage (%)')
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax1.tick_params(axis='x', rotation=45)
    
    for i, v in enumerate(veg_percentages):
        ax1.text(i, v, str(v), ha='center', va='bottom')
    
    ax2.plot(months, mean_ndvis, marker='o', color='blue')
    ax2.set_title('Density of vegetation')
    ax2.set_xlabel('Month')
    ax2.set_ylabel('NDVI')
    ax2.grid(True, linestyle='--', alpha=0.7)
    ax2.tick_params(axis='x', rotation=45)
    
    for i, v in enumerate(mean_ndvis):
        ax2.text(i, v, str(v), ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    
    return output_path

def calculate_percentage(pixels, total_pixels):
    return round((pixels / total_pixels * 100), 2) if total_pixels > 0 else 0

def calculate_quarterly_average(monthly_data):
    quarters = {
        'Q1': monthly_data[0:3],
        'Q2': monthly_data[3:6],
        'Q3': monthly_data[6:9],
        'Q4': monthly_data[9:12]
    }
    
    quarterly_stats = {}
    for quarter, months in quarters.items():
        if not months:
            continue
            
        stats = {
            'water_contained': mean([m['water_contained_pixels'] for m in months]),
            'bare_soil': mean([m['bare_soil_pixels'] for m in months]),
            'grass': mean([m['grass_pixels'] for m in months]),
            'dense_shrub': mean([m['dense_shrub_pixels'] for m in months]),
            'tree': mean([m['tree_pixels'] for m in months]),
            'total_pixels': mean([m['total_pixels'] for m in months])
        }
        
        for key in ['water_contained', 'bare_soil', 'grass', 'dense_shrub', 'tree']:
            stats[f'{key}_percentage'] = calculate_percentage(stats[key], stats['total_pixels'])
            
        quarterly_stats[quarter] = stats
    
    return quarterly_stats

def generate_quarterly_trend_graphs(yearly_data, output_dir, userId):
    quarters = ['Q1', 'Q2', 'Q3', 'Q4']
    metrics = {
        'water_contained_percentage': 'Water Contained Areas (-1.0 to 0.0)',
        'bare_soil_percentage': 'Bare Soil or Sparse Vegetation (0.0 to 0.2)',
        'grass_percentage': 'Moderate Vegetation (0.2 to 0.4)',
        'dense_shrub_percentage': 'Healthy Vegetation (0.4 to 0.6)',
        'tree_percentage': 'Very Dense Vegetation (0.6 to 1.0)',
        'vegetation_percentage': 'Vegetation Coverage (0.0 to 1.0)'
    }
    
    graph_paths = {}
    
    for metric, title in metrics.items():
        plt.figure(figsize=(12, 8))
        
        x = np.arange(len(quarters))
        x_smooth = np.linspace(0, len(quarters)-1, 100)
        
        for year in yearly_data.keys():
            values = [yearly_data[year][q][metric] for q in quarters]
            
            pchip = PchipInterpolator(x, values)
            values_smooth = pchip(x_smooth)
            
            plt.plot(x_smooth, values_smooth, '-', label=f'{year}')
            plt.plot(x, values, 'o', markersize=8)
        
        plt.title(f'Quarterly Trends - {title}', fontsize=14, pad=20)
        plt.xlabel('Quarter', fontsize=12)
        plt.ylabel('Percentage', fontsize=12)
        plt.xticks(x, quarters)
        plt.legend(fontsize=10)
        plt.grid(True, linestyle='--', alpha=0.7)
        
        plt.margins(y=0.1)
        
        plt.tight_layout()
        
        output_path = os.path.join(output_dir, f'quarterly_trends_{metric}_{userId}.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        graph_paths[metric] = output_path
    
    return graph_paths

def generate_monthly_heatmap(yearly_data, output_path):
    months = list(calendar.month_name)[1:]
    years = list(yearly_data.keys())
    
    metrics = {
        'water_contained_percentage': ('Water Contained Areas (-1.0 to 0.0)', 'Blues'),
        'bare_soil_percentage': ('Bare Soil or Sparse Vegetation (0.0 to 0.2)', 'YlOrRd'),
        'grass_percentage': ('Moderate Vegetation (0.2 to 0.4)', 'Greens'),
        'dense_shrub_percentage': ('Healthy Vegetation (0.4 to 0.6)', 'Greens'),
        'tree_percentage': ('Very Dense Vegetation (0.6 to 1.0)', 'Greens'),
        'vegetation_percentage': ('Vegetation Coverage (0.0 to 1.0)', 'Greens')
    }
    
    for metric, (title, colormap) in metrics.items():
        data = []
        for year in years:
            year_data = []
            for month_data in yearly_data[year]:
                total_pixels = month_data['total_pixels']
                if metric == 'water_contained_percentage':
                    pixels = month_data['water_contained_pixels']
                elif metric == 'bare_soil_percentage':
                    pixels = month_data['bare_soil_pixels']
                elif metric == 'grass_percentage':
                    pixels = month_data['grass_pixels']
                elif metric == 'dense_shrub_percentage':
                    pixels = month_data['dense_shrub_pixels']
                elif metric == 'tree_percentage':
                    pixels = month_data['tree_pixels']
                elif metric == 'vegetation_percentage':
                    pixels = month_data['vegetation_pixels']
                percentage = calculate_percentage(pixels, total_pixels)
                year_data.append(percentage)
            data.append(year_data)
            
        plt.figure(figsize=(12, len(years) * 0.5 + 2))
        sns.heatmap(data, annot=True, fmt='.1f', xticklabels=months, 
                   yticklabels=years, cmap=colormap)
        plt.title(f'{title} Heatmap')
        plt.tight_layout()
        plt.savefig(f'{output_path}_{metric}.png')
        plt.close()
        
    return output_path

def generate_html_report(path_unique_id: str, yearly_data, output_dir="satellite_images"):
    os.makedirs(output_dir, exist_ok=True)
    
    temp_dir = os.path.join(output_dir, f'temp_{path_unique_id}')
    images_dir = os.path.join(temp_dir, f'report_images_{path_unique_id}')
    os.makedirs(images_dir, exist_ok=True)
    
    quarterly_yearly_data = {}
    for year, monthly_data in yearly_data.items():
        quarterly_yearly_data[year] = calculate_quarterly_average(monthly_data)
    
    quarterly_graphs = generate_quarterly_trend_graphs(
        quarterly_yearly_data, 
        images_dir,
        path_unique_id
    )
    
    heatmap_base = os.path.join(images_dir, f'monthly_heatmap_{path_unique_id}')
    generate_monthly_heatmap(yearly_data, heatmap_base)
    
    relative_quarterly_graphs = {
        metric: os.path.relpath(path, temp_dir)
        for metric, path in quarterly_graphs.items()
    }
    relative_heatmap_base = os.path.relpath(heatmap_base, temp_dir)
    
    env = Environment(loader=FileSystemLoader('app/templates'))
    template = env.get_template('vegetation_report.html')
    
    template_data = {
        'years': list(yearly_data.keys()),
        'monthly_data': yearly_data,
        'quarterly_data': quarterly_yearly_data,
        'quarterly_graphs': relative_quarterly_graphs,
        'heatmap_base': relative_heatmap_base,
        'metrics': {
            'water_contained_percentage': 'Water Contained Areas (-1.0 to 0.0)',
            'bare_soil_percentage': 'Bare Soil or Sparse Vegetation (0.0 to 0.2)',
            'grass_percentage': 'Moderate Vegetation (0.2 to 0.4)',
            'dense_shrub_percentage': 'Healthy Vegetation (0.4 to 0.6)',
            'tree_percentage': 'Very Dense Vegetation (0.6 to 1.0)',
            'vegetation_percentage': 'Vegetation Coverage (0.0 to 1.0)'
        },
        'calculate_percentage': calculate_percentage
    }
    
    html_content = template.render(**template_data)
    
    temp_html_path = os.path.join(temp_dir, f'vegetation_report_{path_unique_id}.html')
    with open(temp_html_path, 'w') as f:
        f.write(html_content)
    
    pdf_path = os.path.join(output_dir, f'vegetation_report_{path_unique_id}.pdf')
    options = {
        'enable-local-file-access': None,
        'page-size': 'A4',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
        'encoding': "UTF-8",
    }
    
    try:
        pdfkit.from_file(temp_html_path, pdf_path, options=options)
        shutil.rmtree(temp_dir)
        
        return pdf_path
    except Exception as e:
        print(f"Error generating PDF: {e}")
        shutil.rmtree(temp_dir)
        raise e
    
    finally:
        try:
            shutil.rmtree(temp_dir)
            print(f"Cleaned up temporary files in {temp_dir}")
        except Exception as cleanup_error:
            print(f"Error cleaning up temporary files: {cleanup_error}")
