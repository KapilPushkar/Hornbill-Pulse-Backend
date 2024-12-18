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
    
    def search_images(self, coordinates, start_date, end_date, max_cloud_cover=30, limit=1):
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
                import pdb; pdb.set_trace()
                raise Exception(f"Missing required bands: {missing_bands}")
            
            return bands
        
        except Exception as e:
            print(f"Error downloading bands: {e}")
            raise