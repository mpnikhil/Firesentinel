#!/usr/bin/env python3
# This script crops the LANDFIRE GeoTIFF to a California bounding box
# California bounding box (approximate): -124.5, 32.5, -114.0, 42.0

import os
from osgeo import gdal

# Input and output file paths
input_tif = "/Users/aghatage/Documents/code/Firesentinel/dashboard/LF2023_FBFM13_240_CONUS/Tif/LC23_F13_240.tif"
output_tif = "/Users/aghatage/Documents/code/Firesentinel/dashboard/california_landfire.tif"

# California bounding box (west, south, east, north)
bbox = [-124.5, 32.5, -114.0, 42.0]

# Open the dataset
ds = gdal.Open(input_tif)
if ds is None:
    print(f"Error: Could not open {input_tif}")
    exit(1)

# Crop to California bounding box
gdal.Translate(
    output_tif,
    ds,
    projWin=[bbox[0], bbox[3], bbox[2], bbox[1]],  # [ulx, uly, lrx, lry]
    format="GTiff",
    creationOptions=["COMPRESS=LZW", "TILED=YES"]
)

print(f"Created cropped GeoTIFF for California: {output_tif}")