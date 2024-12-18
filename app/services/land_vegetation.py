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
from app.services.notification import send_fcm_notification

@lru_cache(maxsize=1)
def get_copernicus_client():
    return CDSEApi()

def calculate_vegetation_index(bands, coordinates):
    if not bands or not coordinates:
        return {
            'vegetation_percentage': 0,
            'mean_ndvi': 0,
            'max_ndvi': 0,
            'min_ndvi': 0,
            'total_pixels': 0,
            'vegetation_pixels': 0
        }
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
            0
        )

        valid_pixels = ndvi[ndvi != 0]
        total_pixels = valid_pixels.size
        vegetation_pixels = np.sum(valid_pixels > 0.2)
        
        if total_pixels>0:
            vegetation_percentage = (vegetation_pixels / total_pixels) * 100
            stats = {
                'vegetation_percentage': round(vegetation_percentage, 2),
                'mean_ndvi': round(float(np.mean(ndvi)), 3),
                'max_ndvi': round(float(np.max(ndvi)), 3),
                'min_ndvi': round(float(np.min(ndvi)), 3),
                'total_pixels': total_pixels,
                'vegetation_pixels': vegetation_pixels
            }
        else:
            stats = {
                'vegetation_percentage': 0,
                'mean_ndvi': 0,
                'max_ndvi': 0,
                'min_ndvi': 0,
                'total_pixels': 0,
                'vegetation_pixels': 0
            }
        return stats
        
    except Exception as e:
        return {
                'vegetation_percentage': 0,
                'mean_ndvi': 0,
                'max_ndvi': 0,
                'min_ndvi': 0,
                'total_pixels': 0,
                'vegetation_pixels': 0
            }

def search_images(coordinates, start_date, end_date, max_cloud_cover=30):
    client = get_copernicus_client()
    results = client.search_images(coordinates, start_date, end_date, max_cloud_cover=max_cloud_cover)
    if len(results['value']) == 0 and max_cloud_cover<90:
        return search_images(coordinates, start_date, end_date, max_cloud_cover=max_cloud_cover+10)
    return results

def get_bands_directory(product_id, year, month):
    base_dir = "satellite_images/bands"
    year_month_dir = os.path.join(base_dir, f"{product_id}_{year}_{month:02d}")
    os.makedirs(year_month_dir, exist_ok=True)
    return year_month_dir

def generate_land_analysis_report(userId, coordinates, fcm_token):
    current_year = datetime.now().year
    graph_paths = []
    for year in range(current_year-3, current_year+1):
        monthly_data = get_monthly_vegetation_stats(coordinates, year)
        print(monthly_data)
        graph_path = plot_vegetation_trends(monthly_data, f"satellite_images/vegetation_trends_{userId}_{year}.png")
        print(graph_path)
        graph_paths.append(graph_path)
    send_fcm_notification(fcm_token, "Land analysis report", "Your land analysis report is ready")

def get_monthly_vegetation_stats(coordinates, year=2024):
    client = get_copernicus_client()
    monthly_data = []
    
    for month in range(1, 13):
        _, last_day = calendar.monthrange(year, month)
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day}"
        
        try:
            results = search_images(coordinates, start_date, end_date, max_cloud_cover=30)
            
            if results['value']:
                product = results['value'][0]
                product_id = product['Id']
                product_s3_path = product['S3Path'].lstrip('/eodata/')
                bands_dir = get_bands_directory(product_id, year, month)
                bands = client.get_bands(product_s3_path, bands_dir=bands_dir)
                stats = calculate_vegetation_index(bands, coordinates)
                if stats:
                    stats['month'] = calendar.month_name[month]
                    monthly_data.append(stats)
                else:
                    monthly_data.append({
                        'month': calendar.month_name[month],
                        'vegetation_percentage': 0,
                        'mean_ndvi': 0,
                        'max_ndvi': 0,
                        'min_ndvi': 0
                    })
            else:
                print(f"No data available for {calendar.month_name[month]} {year}")
                monthly_data.append({
                    'month': calendar.month_name[month],
                    'vegetation_percentage': 0,
                    'mean_ndvi': 0,
                    'max_ndvi': 0,
                    'min_ndvi': 0
                })
        except Exception as e:
            print(f"Error processing {calendar.month_name[month]}: {e}")
            monthly_data.append({
                'month': calendar.month_name[month],
                'vegetation_percentage': 0,
                'mean_ndvi': 0,
                'max_ndvi': 0,
                'min_ndvi': 0
            })
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
