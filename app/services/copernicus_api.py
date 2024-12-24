import requests
import os
import numpy as np
import rasterio
from rasterio.mask import mask
from shapely.geometry import box, Polygon
import zipfile
import glob
from PIL import Image
import time
import boto3
from botocore.config import Config
import shutil
from pyproj import Transformer
from shapely.ops import transform
import matplotlib.pyplot as plt
import calendar
from app.core.config import settings
from rasterio.merge import merge
from rasterio.warp import calculate_default_transform, reproject, Resampling

class CDSEApi:
    def __init__(self):
        self.base_url = settings.CDSE_BASE_URL
        self.s3_url = settings.CDSE_S3_URL
        self.token_url = settings.CDSE_TOKEN_URL

        self._access_token = None
        self._refresh_token = None
        self.username = settings.CDSE_USERNAME
        self.password = settings.CDSE_PASSWORD
        self.s3_access_key = settings.CDSE_S3_ACCESS_KEY
        self.s3_secret_key = settings.CDSE_S3_SECRET_KEY
        self.token_expires_time = None
        self.refresh_token_expires_time = None
        
    def _get_token(self):
        if self.token_expires_time and time.time() < self.token_expires_time:
            return self._access_token
        
        data = {
            'client_id': 'cdse-public',
            'username': self.username,
            'password': self.password,
            'grant_type': 'password'
        }
        
        if self.refresh_token_expires_time and time.time() < self.refresh_token_expires_time:
            data = {
                'client_id': 'cdse-public',
                'refresh_token': self._refresh_token,
                'grant_type': 'refresh_token'
            }
        
        response = requests.post(self.token_url, data=data)
        if response.status_code == 200:
            self._access_token = response.json()['access_token']
            self.token_expires_time = time.time() + response.json()['expires_in']
            
            if 'refresh_token' in response.json() and 'refresh_expires_in' in response.json() and self._refresh_token != response.json()['refresh_token']:
                self._refresh_token = response.json()['refresh_token']
                self.refresh_token_expires_time = time.time() + response.json()['refresh_expires_in']
            return self._access_token
        else:
            raise Exception(f"Failed to get access token: {response.text}")
    
    def search_images(self, coordinates, start_date, end_date, max_cloud_cover=30, limit=10):
        coords_str = ','.join([f"{coord[1]} {coord[0]}" for coord in coordinates])
        wkt = f"POLYGON(({coords_str}))"
        
        filter_query = f"Collection/Name eq 'SENTINEL-2' and OData.CSC.Intersects(area=geography'SRID=4326;{wkt}') and ContentDate/Start gt {start_date}T00:00:00.000Z and ContentDate/Start lt {end_date}T23:59:59.999Z and Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/Value le {max_cloud_cover})"
        
        params = {
            '$filter': filter_query,
            '$orderby': 'ContentDate/Start desc',
            '$top': limit
        }
        
        headers = {
            'Authorization': f'Bearer {self._get_token()}',
            'Accept': 'application/json'
        }
        response = requests.get(f"{self.base_url}/Products", params=params, headers=headers)
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            raise Exception(f"Search failed: {response.text}")

    def get_bands(self, s3_path, band_names=['B04', 'B08'], bands_dir="satellite_images/bands/other"):
        if isinstance(band_names, str):
            band_names = [band_names]
        print(f"S3 Path: {s3_path}")
        
        bands = {}
        required_bands = band_names
        
        all_cached = True
        for band_name in required_bands:
            band_file = os.path.join(bands_dir, f"{band_name}.jp2")
            if os.path.exists(band_file):
                print(f"✓ Using cached {band_name} from {band_file}")
                bands[band_name] = band_file
            else:
                all_cached = False
        
        if all_cached:
            return bands
        
        s3_client = boto3.client(
            's3',
            region_name='eu-central-1',
            config=Config(signature_version='s3v4'),
            endpoint_url=self.s3_url,
            aws_access_key_id=self.s3_access_key,
            aws_secret_access_key=self.s3_secret_key
        )
        
        try:
            granules = s3_client.list_objects_v2(Bucket='eodata', Prefix=s3_path)
            
            for band_name in required_bands:
                if band_name not in bands:
                    band_file = os.path.join(bands_dir, f"{band_name}.jp2")
                    
                    print(f"⬇ Downloading band {band_name}...")
                    band_found = False
                    
                    for obj in granules.get('Contents', []):
                        if 'IMG_DATA' in obj['Key'] and not 'QI_DATA' in obj['Key']:
                            file_name = obj['Key'].split('/')[-1]
                            if f'_{band_name}.jp2' in file_name or f'_{band_name}_10m.jp2' in file_name:
                                s3_client.download_file(
                                    Bucket='eodata',
                                    Key=obj['Key'],
                                    Filename=band_file
                                )
                                bands[band_name] = band_file
                                print(f"✓ Successfully downloaded {band_name}")
                                band_found = True
                                break
                    
                    if not band_found:
                        print(f"✗ Could not find {band_name} in the product")
            
            missing_bands = [band for band in required_bands if band not in bands]
            if missing_bands:
                raise Exception(f"Missing required bands: {missing_bands}")
            
            return bands
        
        except Exception as e:
            print(f"Error downloading bands: {e}")
            raise

    def get_bands_directory(self, product_id, year, month):
        base_dir = "satellite_images/bands"
        year_month_dir = os.path.join(base_dir, f"{product_id}_{year}_{month:02d}")
        os.makedirs(year_month_dir, exist_ok=True)
        return year_month_dir


    def get_bands_mosaic(self, product_ids, year, month, s3_paths, band_names=['B04', 'B08'], output_dir="satellite_images/merged"):
        os.makedirs(output_dir, exist_ok=True)
        merged_bands = {}

        for band_name in band_names:
            print(f"Processing {band_name} across all tiles...")
            band_files = []
            
            for s3_path in s3_paths:
                bands_dir = self.get_bands_directory(product_ids[0], year, month)
                temp_bands = self.get_bands(s3_path.lstrip('/eodata/'), band_names=[band_name], bands_dir=bands_dir)
                if band_name in temp_bands:
                    band_files.append(temp_bands[band_name])

            if not band_files:
                raise Exception(f"No valid files found for band {band_name}")

            output_path = os.path.join(output_dir, f"merged_{band_name}.jp2")
            
            raster_to_mosaic = []
            for band_file in band_files:
                raster = rasterio.open(band_file)
                raster_to_mosaic.append(raster)

            mosaic, output_transform = merge(raster_to_mosaic)

            out_meta = raster_to_mosaic[0].meta.copy()
            out_meta.update({
                "height": mosaic.shape[1],
                "width": mosaic.shape[2],
                "transform": output_transform
            })

            with rasterio.open(output_path, "w", **out_meta) as dest:
                dest.write(mosaic)

            for raster in raster_to_mosaic:
                raster.close()

            merged_bands[band_name] = output_path
            print(f"✓ Successfully merged {band_name}")

        return merged_bands

    def clip_to_aoi(self, raster_path, coordinates, output_path=None):
        swapped_coordinates = [[coord[1], coord[0]] for coord in coordinates]
        polygon = Polygon(swapped_coordinates)
        
        if output_path is None:
            output_path = raster_path.replace('.jp2', '_clipped.jp2')
        
        with rasterio.open(raster_path) as src:
            transformer = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
            def transform_func(x, y):
                return transformer.transform(x, y)
            
            polygon_transformed = transform(transform_func, polygon)
            
            try:
                out_image, out_transform = mask(src, [polygon_transformed], crop=True)
                out_meta = src.meta.copy()
                
                out_meta.update({
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform
                })
                
                with rasterio.open(output_path, "w", **out_meta) as dest:
                    dest.write(out_image)
                    
                return output_path
                
            except Exception as e:
                print(f"Error during clipping: {str(e)}")
                print(f"Polygon bounds: {polygon.bounds}")
                print(f"Raster bounds: {src.bounds}")
                raise

    def group_images_by_date(self, search_results):
        grouped_images = {}
        
        sorted_results = sorted(
            search_results.get('value', []),
            key=lambda x: x['ContentDate']['Start'],
            reverse=True
        )
        
        processed_tiles = {}
        
        for item in sorted_results:
            date = item['ContentDate']['Start'].split('T')[0]
            tile_id = item['S3Path'].split('_T')[-1].split('_')[0] 
            
            if date not in grouped_images:
                grouped_images[date] = {}
                processed_tiles[date] = set()
                
            if tile_id not in processed_tiles[date]:
                grouped_images[date][item['Id']] = item['S3Path']
                processed_tiles[date].add(tile_id)
                
        return grouped_images

    def process_area_temporal(self, coordinates, start_date, end_date, band_names=['B04', 'B08'], 
                             max_cloud_cover=30, limit=1):
        try:
            year = int(start_date.split('-')[0])
            month = int(start_date.split('-')[1])
            
            search_limit = limit * 10
            for max_cloud_cover in [30, 40, 50, 60, 70, 80, 90]:
                results = self.search_images(coordinates, start_date, end_date, 
                                       max_cloud_cover=max_cloud_cover, limit=search_limit)
                if len(results.get('value', [])) > 0:
                    break
            
            if not results.get('value'):
                print(f"No images found for period {start_date} to {end_date}")
                return {}

            grouped_images = self.group_images_by_date(results)
            
            dates = sorted(grouped_images.keys(), reverse=True)
            dates = dates[:limit]
            
            processed_results = {}
            for date in dates:
                print(f"\nProcessing date: {date}")
                tile_paths = grouped_images[date]
                
                try:
                    product_ids = list(tile_paths.keys())
                    s3_paths = list(tile_paths.values())
                    bands_dir = self.get_bands_directory(product_ids[0], year, month)
                    
                    unique_tiles = set()
                    for path in s3_paths:
                        tile_id = path.split('_T')[-1].split('_')[0]
                        unique_tiles.add(tile_id)
                    
                    if len(unique_tiles) == 1:
                        print(f"Single unique tile found ({list(unique_tiles)[0]}), skipping mosaic...")
                        bands = self.get_bands(
                            s3_paths[0].lstrip('/eodata/'),
                            band_names=band_names,
                            bands_dir=bands_dir
                        )
                    else:
                        print(f"Multiple unique tiles found {unique_tiles}, creating mosaic...")
                        bands = self.get_bands_mosaic(
                            product_ids,
                            year,
                            month,
                            s3_paths,
                            band_names=band_names,
                            output_dir=bands_dir
                        )
                    
                    if not bands:
                        print(f"No valid bands found for date {date}")
                        continue
                    
                    processed_results[date] = bands
                    
                    if len(processed_results) >= limit:
                        break
                    
                except Exception as e:
                    print(f"Error processing date {date}: {str(e)}")
                    continue
            
            return processed_results
            
        except Exception as e:
            print(f"Error in process_area_temporal: {str(e)}")
            return {}