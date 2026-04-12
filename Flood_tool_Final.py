#WELCOME! 

"""The steps below will help you use this tool and add the 
required USER INPUT PARAMETERS """

#1)First read the README.md document provided to download the apps and intall the extensions
#required. 

#2)Add the path to the miniconda environment created in Initial Setup to the
#conda_python_path variable(line 128). This will remain constant between analyses 
#and does not need to be changed. 

#3)Add the path to the downloaded CHIRPS data folder in the variable 
#chirps_folder (line 129)

#4)Create a folder where the outputs of this program will be stored and 
#store it in the variable 'output_dir' (line 126)
#ex:output_dir= r"C:/Users/chris/Documents/Paraguay"

#5)Obtain your desired DEM in 30m resolution. Name the file DEM, then save it to the output_dir. 

#6)Next find the projected CRS of your region and 
#store it in the 'target_crs' variable as a string. ex:'EPSG:3720' (line 123)

#5)Store the coordinates of the outlet point used in watershed delineation 
#in x_outlet and y_outlet(lines 121 & 122) They should be in the projected CRS and should have no commas in them.
#It is not necessary for them to lie exactly on stream raster pixels as a function will snap to the 
#nearest stream pixel from your coordinates. 

#7)Choose a threshold/thresholds and store them in threshold as a list (line 124)
#for example threshold=[3000,17000]. 
#The threshold will control subbasin size which will spatially grid the watershed area
#to show relative flood risk. A smaller threshold will give more detail than a larger 
#threshold up to a point. There is no wrong choice of thresholds but here are some recommendations.

"""Watershed size (km2)	Threshold recommendation 
                <5000	1000-3000
                5000-30000	3000-30000
                >30000	>30000"""


#8)A folder called 'Data' is provided with this package. Add its path to the data_dir variable 
#eg:r"C:/Users/Chris/Downloads/Data" (line 127)

#9)Add your GRASS executable path in the GRASS_path variable (line 130)

#This is OS specific 
#ex for Windows it may be : GRASS_path=r"C:/Program Files/GRASS GIS 8.4/grass84.bat"
#ex for Mac it may be :/Applications/GRASS-8.4.app/Contents/MacOS/Grass.sh
#ex for Linux it may be :/usr/bin/grass

#10) Choose any string to write in the LOCATION variable (line 131)
#this can be the location of your DEM ex LOCATION="Banff"
#remember to change this between projects 

#11)Choose a strahler threshold/s to analyse stream orders of the watershed and add 
#it to the strahler_threshold parameter. (line 125)
#This will not affect the flood analysis hence there is no wrong strahler threshold.

#11)Finally type execute()in the terminal to start the project



"""IMPORTANT NOTES (PLEASE READ)"""
#1)The entire process can take a long time and is heavily dependent on your system's RAM 
#So it is advisable to close RAM heavy windows in the background before you start.
#I have found changing to best performance on Windows helps speed up the process 
#To do that go to Settings>System>Power>Power Mode>Best Performance. 

#2)Although your cursor may only appear as a loading sign for a long time, the analysis is still ongoing.
#To verify this, open the output_dir and you should be able to see files added in the last few minutes atleast.
#In general here are the times you can expect the tool to take 

#Watershed Size(sqkm)	 Time 
    #<5000	2-6 mins
    #5000-30000	6-40 mins
    #>30000	> 40+mins
    
#Once again speeds are highly RAM dependent. 

#3)Ensure atleast 5-6 GB of free disk space before using the tool. 

#4)If the tool fails and you encounter errors, read the troubleshooting below or 
#contact me via qasimd1234@gmail.com

"""Troubleshooting"""
#It is possible that your user provided outlet points are not close enough to the intended 
#stream or confluence point for the watershed delineation and a stray stream pixel is used for delineation
#resulting in an erroneous watershed. 
#This is especially common in urban areas where stream paths are engineered. 
#If this does happen:
#Add the accumulation layer from the output_dir folder to the map
#zoom in to your intended point of delineation
#Use the identify features button to click at the point ensure a relatively high accumulation value exists there. 
#Update your outlet coordinates
#Delete all layers from the map, then all files from the output_dir folder except the DEM.tif 
#Then repeat the process with the updates outlet coordinates 



#IMPORTS
import os, shutil, glob, math, time, gzip
import requests
import numpy as np
import pandas as pd
import dask
import netCDF4
import rasterio 
import subprocess
import xarray as xr
import rioxarray
from osgeo import gdal
from qgis.core import (
    QgsProject, QgsRasterLayer, QgsCoordinateReferenceSystem,
    QgsCoordinateTransform, QgsPointXY, QgsGeometry, QgsFeature,
    QgsVectorLayer, QgsGraduatedSymbolRenderer, QgsRendererRange,
    QgsSymbol, QgsVectorLayerSimpleLabeling
)
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from qgis.PyQt.QtCore import QVariant
from PyQt5.QtGui import QColor


# USER INPUT PARAMETERs
x_outlet=
y_outlet=
target_crs=
threshold=
strahler_threshold=
output_dir= 
data_dir=
conda_python_path=
chirps_folder=
GRASS_path=
LOCATION=


#Program script and file paths (do not change)
dem_path=os.path.join(output_dir,"DEM.tif")
soil_thickness_path=os.path.join(data_dir,"average_soil_and_sedimentary-deposit_thickness.tif")
Ksat_path=os.path.join(data_dir,"Global_Ksat_1Km_s100....100cm_v1.0.tif")
rainfall_script = os.path.join(data_dir,"new_rainfall_processing.py")
HAND_script_path = os.path.join(data_dir,"hand_grass_script.py")
strahler_script_path=os.path.join(data_dir,"strahler_grass_script.py")
grass_location_path = os.path.join(output_dir, LOCATION, "PERMANENT")




# LAYER STYLES (QML)
STYLE_DIR = os.path.join(data_dir,"styles")
STYLES ={"fsi": "FSI_style.qml",
    "risk": "Flood_risk_style.qml",
    "strahler": "Strahler_style.qml",
    "basin": "Basin_outlines.qml",
    "dem": "Clipped_DEM_style.qml",
    "outlet": "Outlet_style.qml",
    "watershed": "Watershed_vector_style.qml",
    "hillshade": "Hillshade_style.qml",
    "landcover":"Landcover_legend.qml",
    "stream_vector":"Stream_vector_style.qml"}

STYLE_PATHS ={key: os.path.join(STYLE_DIR, filename)
    for key, filename in STYLES.items()}



def execute():
    start_time = time.perf_counter()
    reproj_path=GRASS_location_creation()
    stream_paths, basin_paths,drainage_path, TWI_path,accum_path=run_watershed(reproj_path,output_dir, threshold)
    watershed_rast_path=watershed_delin(stream_paths,drainage_path,output_dir, target_crs,x_outlet,y_outlet)
    watershed_vector_path, basin_vector_paths, stream_vector_paths, basin_vector_objects,DEM_clipped_path,accum_clipped_path=postprocess_watershed(accum_path,watershed_rast_path,basin_paths,stream_paths,output_dir,reproj_path,threshold)
    mosaic_path=ESA_Worldcover_tiles(DEM_clipped_path,output_dir)
    print("Approximately 50% of the way there!")
    annual_rain_reproj_path, P95_reproj_path=run_rainfall(rainfall_script,DEM_clipped_path, output_dir,conda_python_path,target_crs,basin_vector_paths,basin_vector_objects)
    landcover_inflitration_exposure(annual_rain_reproj_path, P95_reproj_path,mosaic_path,watershed_vector_path, basin_vector_paths,basin_vector_objects,output_dir,DEM_clipped_path,target_crs)
    Soil_transmissivity(Ksat_path,soil_thickness_path,basin_vector_objects,basin_vector_paths,watershed_vector_path)
    stream_5500_output_path=HAND(accum_clipped_path,HAND_script_path, DEM_clipped_path,output_dir, basin_vector_paths, basin_vector_objects)
    drainage_density(stream_5500_output_path,basin_vector_paths,basin_vector_objects)
    TWI_and_shapefactor (TWI_path,watershed_vector_path,DEM_clipped_path,threshold,output_dir,basin_vector_paths,basin_vector_objects)
    FSI_and_Flood_Risk (basin_vector_paths,basin_vector_objects)
    layer_styling_and_misc(basin_vector_objects, threshold, output_dir,watershed_vector_path,DEM_clipped_path)
    stream_strahler_ordering(accum_clipped_path,watershed_vector_path, strahler_script_path,DEM_clipped_path,strahler_threshold,output_dir)
    end_time = time.perf_counter()
    elapsed = end_time - start_time
    minutes, seconds = divmod(elapsed, 60)
    print(f"Total runtime: {int(minutes)} min {seconds:.1f} sec")
    Final_message(threshold)

def GRASS_location_creation():
    
    #Reprojecting the DEM 
    dem = QgsRasterLayer(dem_path, "DEM")
    reproj_path = os.path.join(output_dir, "DEM_reproj.tif")
    print("Reprojecting DEM")
    reproj = processing.run("gdal:warpreproject",
    {"INPUT": dem,
    "TARGET_CRS": target_crs,
    "RESAMPLING": 0,
    "TARGET_RESOLUTION": 30,
    "MULTITHREADING": True,
    "OPTIONS": "TILED=YES|COMPRESS=LZW|BIGTIFF=YES",
    "OUTPUT": reproj_path})
    
    GISDBASE = output_dir

    ##The'GRASS_path' variable stores the GRASS GIS executable path.
    #This is os specific 
    #ex for Windows: GRASS_path=r"C:/Program Files/GRASS GIS 8.4/grass84.bat"
    #ex for Mac:/Applications/GRASS-8.4.app/Contents/MacOS/Grass.sh
    #ex for Linux:/usr/bin/grass
    
    #The string stored in LOCATION can be any name eg:"Colorado" 
    #however it should be different for different projects

    env=os.environ.copy()
    subprocess.run([GRASS_path,"-c",reproj_path,os.path.join(GISDBASE, LOCATION),
    "--exec", "g.region", "-p"],
    env=env)

    print("GRASS location created!")
    return reproj_path


def ESA_Worldcover_tiles(DEM_clipped_path,output_dir):
    #This function will download and mosaic the ESA  worldcover tiles that 
    #span thedelineated watershed extent in EPSG 4326
    
    clipped_DEM=QgsRasterLayer(DEM_clipped_path,"Clipped_DEM")
    extent=clipped_DEM.extent()
    
    transform = QgsCoordinateTransform(
    clipped_DEM.crs(),
    QgsCoordinateReferenceSystem("EPSG:4326"),
    QgsProject.instance() )
    
    bbox_4326 = transform.transformBoundingBox(extent)
    
    x_min=bbox_4326.xMinimum()
    x_max=bbox_4326.xMaximum()
    y_min=bbox_4326.yMinimum()
    y_max=bbox_4326.yMaximum()
    
    tile_size=3 #each tile from ESA Worlcover is a square that spans 3 degrees in each direction

    lats = range(int(math.floor(y_min/ tile_size) * tile_size),
        int(math.floor(y_max / tile_size) * tile_size) + tile_size,
        tile_size)
        
    lons = range(int(math.floor(x_min/ tile_size) * tile_size),
        int(math.floor(x_max / tile_size) * tile_size) + tile_size,
        tile_size)
        
    tiles = []

    for lat in lats:
        for lon in lons:
            ns = "N" if lat >= 0 else "S"
            ew = "E" if lon >= 0 else "W"
            tiles.append(f"{ns}{abs(lat):02d}{ew}{abs(lon):03d}")

    base_url = ("https://esa-worldcover.s3.eu-central-1.amazonaws.com/"
    "v200/2021/map/")
    
    out_paths=[]
    for tile in tiles:
        filename = f"ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"
        url = base_url + filename
        out_path = os.path.join(output_dir, filename)
        out_paths.append(out_path)
        print(f"Downloading {filename}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

    print("All downloads complete.")
    
    #Mosaic Worldcover tiles if more than 1 exist
    if len(out_paths)>1:
        mosaic_path=os.path.join(output_dir, "Worldcover_mosaic.tif")
        virtual_rast=processing.run("gdal:buildvirtualraster",
        {'INPUT':out_paths,
        'RESOLUTION':0,
        'SEPARATE':False,
        'RESAMPLING':0,
        'SRC_NODATA':0,
        'OUTPUT':"TEMPORARY_OUTPUT"})['OUTPUT']
        
        processing.run("gdal:translate",
        {"INPUT":virtual_rast,
        "DATA_TYPE": 1,
        "OPTIONS": "COMPRESS=LZW|TILED=YES|BIGTIFF=YES",
        "OUTPUT": mosaic_path})
    else:
        mosaic_path=out_paths[0]
    
    print("Landcover acquistion complete!")
    return mosaic_path
    
def run_watershed(reproj_path,output_dir, threshold):
    #This function runs r.watershed for different outputs 
    #Running r.watershed for drainage ,accumulation and TWI 
    #separately as they are invariant to threshold
    TWI_path=os.path.join(output_dir, "TWI.tif")
    drainage_path=os.path.join(output_dir, "Drainage.tif")
    accum_path=os.path.join(output_dir,"Accumulation.tif")
    processing.run("grass:r.watershed", 
    {'elevation': reproj_path,
    'threshold':1000 ,#any threshold works here 
    'convergence':5,
    'memory':8000,
    '-s':False,
    "MULTITHREADING": True,
    "OPTIONS": "TILED=YES|COMPRESS=LZW|BIGTIFF=YES",
    'tci':TWI_path,
    'accumulation':accum_path,
    'drainage':drainage_path})
    print("Accumulation and drainage computed!")
    
    #Now running r.watershed for each threshold
    #to obtain  stream and basin rasters
    stream_paths=[]
    basin_paths=[]
    for t in threshold:
        
        basin_path=os.path.join(output_dir, f"Basins_{t}.tif")
        stream_path=os.path.join(output_dir,f"Streams_{t}.tif")
        ws=processing.run("grass:r.watershed", 
        {'elevation': reproj_path,
        'threshold': int(t),
        'convergence':5,
        'memory':8000,
        '-s':True,
        "MULTITHREADING": True,
        "OPTIONS": "TILED=YES|COMPRESS=LZW|BIGTIFF=YES",
        'stream':stream_path,
        'basin':basin_path})
        
        stream_paths.append(stream_path)
        basin_paths.append(basin_path)
    
    print("r.watershed processing complete!")
    return stream_paths, basin_paths,drainage_path, TWI_path, accum_path

def watershed_delin(stream_paths,drainage_path, output_dir, target_crs,x_outlet,y_outlet):
    #This function runs r.water.outlet using the users x and y
    #outlet inputs and snapping them to the closest stream raster pixel
    
    #First creating point layer from x_outlet, y_outlet
    outlet_layer = QgsVectorLayer("Point", "Stream_Outlet_Point", "memory")
    outlet_layer.setCrs(QgsCoordinateReferenceSystem(target_crs))
    prov = outlet_layer.dataProvider()
    feat = QgsFeature()
    feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x_outlet, y_outlet)))
    prov.addFeature(feat)
    outlet_layer.updateExtents()
   
    
    stream_path=stream_paths[0]
    #Any stream raster can be used in delineation assuming the outlet is 
    #chosen at a high enough accumulation
    
    #Vectorizing stream raster into pixels
    stream_points = processing.run("native:pixelstopoints",
    {"INPUT_RASTER": stream_path,
    "RASTER_BAND": 1,
    "FIELD_NAME": "value",
    "OUTPUT": "TEMPORARY_OUTPUT"})["OUTPUT"]

    #Snapping outlet point to nearest stream pixel 
    #This makes sure the users inputs for the outlet point 
    #actually lie on a stream raster pixel
    
    tolerance = 300 #initial tolerance 
    max_tolerance = 5000
    step = 200

    snapped_layer = None
    success = False

    while tolerance <= max_tolerance:
        result = processing.run(
        "native:snapgeometries",{
        "INPUT": outlet_layer,
        "REFERENCE_LAYER": stream_points,
        "TOLERANCE": tolerance,
        "BEHAVIOR": 3,  # snap to closest point
        "OUTPUT": "TEMPORARY_OUTPUT"})

        snapped_layer = result["OUTPUT"]

        # Extract snapped point
        feat = next(snapped_layer.getFeatures())
        pt = feat.geometry().asPoint()

        x_snap, y_snap = pt.x(), pt.y()

        # Check if snapping actually moved the point
        if abs(x_snap - x_outlet) > 0.01 or abs(y_snap - y_outlet) > 0.01:
            success = True
            print(f"Snapped to closest raster pixel at= {tolerance} m")
            break

        tolerance += step
        
    if not success:
        raise RuntimeError("Outlet point could not be snapped to any stream pixel")

    
    stream_outlet_path = os.path.join(output_dir, "Stream_Outlet_Point.gpkg")
    processing.run("native:savefeatures",{
    "INPUT": snapped_layer,
    "OUTPUT":stream_outlet_path})
    stream_outlet = QgsVectorLayer(stream_outlet_path, "Stream_Outlet_Point", "ogr")
    stream_outlet.loadNamedStyle(STYLE_PATHS["outlet"])
    stream_outlet.triggerRepaint()
    QgsProject.instance().addMapLayer(stream_outlet)

    #Running r.water.outlet on the snapped coordinates
    watershed_rast_path=os.path.join(output_dir,"Watershed.tif")
    ot=processing.run("grass:r.water.outlet",
    {"input": drainage_path,
    "coordinates": f"{x_snap},{y_snap}",
    "output": watershed_rast_path})

    #Adding stream outlet point to map 
    print("Watershed delineation complete!")

    return watershed_rast_path

def postprocess_watershed(accum_path,watershed_rast_path,basin_paths,stream_paths,output_dir,reproj_path,threshold):
    #This function vectorizes and clips watershed and stream layers 
    #to be used later in other functions 
    
    #Vectorizing watershed layer
    vec=processing.run("grass:r.to.vect",
    {'input':watershed_rast_path,
    'type':2,
    'column':'value',
    'output':'TEMPORARY_OUTPUT',})
    
    #Fixing geometries
    watershed_vector_path=os.path.join(output_dir,"Watershed_vector.gpkg")
    fix=processing.run("native:fixgeometries", 
    {'INPUT':vec['output'],
    'METHOD':1,
    'OUTPUT':watershed_vector_path})
    
    #Adding watershed_vec layer to map 
    QgsProject.instance().addMapLayer(QgsVectorLayer(fix["OUTPUT"],"Watershed_vector"))
    
    #Clipping DEM to watershed_vector and adding to map 
    DEM_clipped_path=os.path.join(output_dir,"Clipped_DEM.tif")
    clip_1=processing.run("gdal:cliprasterbymasklayer",
    {'INPUT':reproj_path,
    'MASK':watershed_vector_path,
    'OUTPUT':DEM_clipped_path})
    clipped_DEM=QgsRasterLayer(DEM_clipped_path,"Clipped_DEM")
    QgsProject.instance().addMapLayer(clipped_DEM)
    
    #Clipping accumulation to clipped_DEM
    accum_clipped_path=os.path.join(output_dir,"Accumulation_clipped.tif")
    clip=processing.run("gdal:cliprasterbymasklayer",
    {'INPUT':accum_path,
    'MASK':watershed_vector_path,
    'TARGET_CRS':target_crs,
    'CROP_TO_CUTLINE':True,
    'OUTPUT':accum_clipped_path})
    
    #Clipping stream rasters and subbasin rasters to Watershed_vector
    basin_vector_paths=[]
    basin_vector_objects=[]
    stream_vector_paths=[]
    for t, stream_path, basin_path in zip(threshold, stream_paths,basin_paths):

        #Clipping basins
        clip_2=processing.run("gdal:cliprasterbymasklayer",
        {'INPUT':basin_path,
        'MASK':watershed_vector_path,
        'OUTPUT':'TEMPORARY_OUTPUT'})
        
        #Vectorize clipped basins
        basin_vector_path=os.path.join(output_dir,f"Basin_vector_{t}.gpkg")
        basin_vec=processing.run("grass:r.to.vect",
        {'input':clip_2['OUTPUT'],
        'type':2,
        'column':'value',
        'output':'TEMPORARY_OUTPUT'})['output']
        
        #Fixing geometries of basin vector files and 
        #adding to map
        fix_2=processing.run("native:fixgeometries",
        {'INPUT':basin_vec,
        'METHOD':1,
        'OUTPUT':basin_vector_path})
        basin_vector_paths.append(basin_vector_path)
        basin_vector_object=QgsVectorLayer(basin_vector_path,f"Basin_vector{t}","ogr")
        basin_vector_objects.append(basin_vector_object)
        QgsProject.instance().addMapLayer(basin_vector_object)
        
        #Clipping streams
        clip=processing.run("gdal:cliprasterbymasklayer",
        {'INPUT':stream_path,
        'MASK':watershed_vector_path,
        'OUTPUT':'TEMPORARY_OUTPUT'})
        
        #Vectorize clipped streams and add to map
        stream_vector_path=os.path.join(output_dir,f"Stream_vector_{t}.gpkg")
        stream_vec=processing.run("grass:r.to.vect",
        {'input':clip['OUTPUT'],
        'type':0,
        'column':'value',
        'output':stream_vector_path})
        stream_vector_paths.append(stream_vector_path)
        
        #Styling stream_vectors
        stream_vector_layer=QgsVectorLayer(stream_vector_path,f"Stream_vector{t}","ogr")
        QgsProject.instance().addMapLayer(stream_vector_layer)
        stream_vector_layer.loadNamedStyle(STYLE_PATHS["stream_vector"])
        stream_vector_layer.triggerRepaint()
    
    #Calculating subbasin areas and deleting trivial,pixel sized subbasins
    for basin_vector_object in basin_vector_objects:
        basin_vector_object.startEditing()
        basin_vector_object.dataProvider().addAttributes([QgsField("Area_m2",QVariant.Double)])
        basin_vector_object.updateFields()
        for f in basin_vector_object.getFeatures():
            f["Area_m2"] = f.geometry().area()
            basin_vector_object.updateFeature(f)
        Largest_basin_area=max(float(f["Area_m2"])for f in basin_vector_object.getFeatures())
        for f in basin_vector_object.getFeatures():
            if float(f["Area_m2"])<0.0005*Largest_basin_area:
                basin_vector_object.deleteFeature(f.id())
        basin_vector_object.commitChanges()
        
        #Creating Basin ID's for each basin feature to be used when 
        #joining zonal stats later'
        basin_vector_object.startEditing()
        field = QgsField("Basin_ID", QVariant.Int)
        basin_vector_object.dataProvider().addAttributes([field])
        basin_vector_object.updateFields()
        
        basin_id = 1

        for feature in basin_vector_object.getFeatures():
            feature["Basin_ID"] = basin_id
            basin_vector_object.updateFeature(feature)
            basin_id += 1
        basin_vector_object.commitChanges()
        
    print("Raster vecorization and misc complete!")
    
    return watershed_vector_path, basin_vector_paths, stream_vector_paths, basin_vector_objects, DEM_clipped_path,accum_clipped_path

def run_rainfall(rainfall_script,DEM_clipped_path, output_dir,conda_python_path,target_crs,basin_vector_paths,basin_vector_objects):

    #This function uses the folder with the dowloaded CHIRPS data and clips the 
    #data to the watershed extent. Then it calls on an external script 
    #to calculate the mean of annual pentad maxima (rainfall accumulated over 5 days)
    # over 25 years (1995-2020). It then creates
    #a raster showing that. Then zonal statistics is used on the raster to see the 
    #variation of the rainfall in the watershed
    clipped_DEM = QgsRasterLayer(DEM_clipped_path, "Clipped_DEM")
    extent = clipped_DEM.extent()

    transform = QgsCoordinateTransform(
    clipped_DEM.crs(),
    QgsCoordinateReferenceSystem("EPSG:4326"),
    QgsProject.instance())

    bbox_4326 = transform.transformBoundingBox(extent)

    x_min = bbox_4326.xMinimum()
    x_max = bbox_4326.xMaximum()
    y_min = bbox_4326.yMinimum()
    y_max = bbox_4326.yMaximum()

    P95_output_path = os.path.join(output_dir, "P95_rainfall_rast.tif")
    Annual_rain_output_path=os.path.join(output_dir,"Annual_rainfall_rast.tif")
    env = os.environ.copy()
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)

    cmd = [
    conda_python_path,
    rainfall_script,
    str(x_min),
    str(x_max),
    str(y_min),
    str(y_max),
    chirps_folder,
    P95_output_path,
    Annual_rain_output_path]

    result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    env=env)

    if result.returncode != 0:
        raise RuntimeError("Rainfall backend failed.")
    
    print("Rainfall raster calculated!")
    
    #Reprojecting the pentad raster to project CRS
    #and resampling to 30m 
    P95_raster_4326 = QgsRasterLayer(P95_output_path, "temp")
    P95_reproj_path=os.path.join(output_dir,"P95_reproj.tif")
    reproj = processing.run("gdal:warpreproject",
    {"INPUT": P95_raster_4326,
    "TARGET_CRS": target_crs,
    "TARGET_RESOLUTION": 30,
    "MULTITHREADING": True,
    "OPTIONS": "TILED=YES|COMPRESS=LZW|BIGTIFF=YES",
    "RESAMPLING": 1,
    "NODATA":-9999,
    "OUTPUT":P95_reproj_path})
    
    #Zonal statistics to find mean P95 per subbasin
    for basin_vector_path,basin_vector_object in zip(basin_vector_paths,basin_vector_objects):
        mean_P95=processing.run("native:zonalstatisticsfb",
        {'INPUT':basin_vector_path,
        'INPUT_RASTER':P95_reproj_path,
        'RASTER_BAND':1,
        'COLUMN_PREFIX':'_',
        'STATISTICS':[2],
        'OUTPUT':"TEMPORARY_OUTPUT"})
        
        #Joining and normalising 995 Rainfall 
        vector_join (basin_vector_object,mean_P95['OUTPUT'],
        "P95_rainfall(mm/day)","_mean")

        normalize(basin_vector_object,"P95_rainfall(mm/day)","P95_rain_norm")
        
    #Reprojecting the annual rainfall raster to project CRS
    #and resampling to 30m
    annual_rainfall_raster_4326 = QgsRasterLayer(Annual_rain_output_path, "temp")
    annual_rain_reproj_path=os.path.join(output_dir,"Annual_rainfall_rast_reproj.tif")
    reproj = processing.run("gdal:warpreproject",
    {"INPUT": annual_rainfall_raster_4326,
    "TARGET_CRS": target_crs,
    "TARGET_RESOLUTION": 30,
    "MULTITHREADING": True,
    "OPTIONS": "TILED=YES|COMPRESS=LZW|BIGTIFF=YES",
    "RESAMPLING": 1,
    "NODATA":-9999,
    "OUTPUT":annual_rain_reproj_path})
    
    #Zonal statistics to find mean annual rainfall per subbasin
    for basin_vector_path,basin_vector_object in zip(basin_vector_paths,basin_vector_objects):
        mean_annual=processing.run("native:zonalstatisticsfb",
        {'INPUT':basin_vector_path,
        'INPUT_RASTER':annual_rain_reproj_path,
        'RASTER_BAND':1,
        'COLUMN_PREFIX':'_',
        'STATISTICS':[2],
        'OUTPUT':"TEMPORARY_OUTPUT"})
        
        #Joining annual Rainfall 
        vector_join (basin_vector_object,mean_annual['OUTPUT'],
        "Annual_rainfall_mm/year","_mean")
    
    print("Watershed rainfall computation done!")
    return annual_rain_reproj_path, P95_reproj_path
    
def landcover_inflitration_exposure(annual_rain_reproj_path, P95_reproj_path, mosaic_path,watershed_vector_path,basin_vector_paths,basin_vector_objects,output_dir,DEM_clipped_path,target_crs):
    #This function approximates infiltration per basin and finds relative exposure 
    #based on landcover.
    #First the landcover raster is clipped to the watershed,then it is reclassified
    #so each of the 11 landcover types have a CN value. Mean CN values are calculated 
    #per basin and are adjusted based on the mean slope to account for the effect of terrain on runoff
    # generation, where steeper slopes reduce infiltration potential and increase effective runoff.

    #Running r.slope.aspect for slope raster
    slope_path=os.path.join(output_dir,"Slope_raster.tif")
    slope=processing.run("grass:r.slope.aspect",
    {'elevation':DEM_clipped_path,
     'format':1,
     'slope':slope_path})

    #Calculating average slope per basin 
    for basin_vector_path,basin_vector_object in zip(basin_vector_paths,basin_vector_objects):
        avg_slope=processing.run("native:zonalstatisticsfb",
        {'INPUT':basin_vector_path,
         'INPUT_RASTER':slope['slope'],
         'RASTER_BAND':1,
         'COLUMN_PREFIX':'_',
         'STATISTICS':[2],
         'OUTPUT':'TEMPORARY_OUTPUT'})
        
        #Appending average slope to attribute table
        vector_join (basin_vector_object,avg_slope['OUTPUT'],
        "Mean_slope(%)","_mean")

    print("Calculated average slope per basin!")
    

    #Clipping, reprojecting and styling landcover to watershed
    #landcover is originally at 10m resolution so it is resampled to
    #30m to match DEM resolution
    landcover_path=os.path.join(output_dir,"Landcover.tif")
    clip=processing.run("gdal:cliprasterbymasklayer",
    {'INPUT':mosaic_path,
    'MASK':watershed_vector_path,
    'TARGET_CRS':target_crs,
    'SET_RESOLUTION': True,
    'X_RESOLUTION': 30,
    'Y_RESOLUTION': 30,
    'RESAMPLING':0,
    'OUTPUT':landcover_path})
    
    #Adding landcover to map and adding legend
    landcover_layer=QgsRasterLayer(landcover_path,"Landcover")
    QgsProject.instance().addMapLayer(landcover_layer)
    style_path = os.path.normpath(STYLE_PATHS["landcover"])
    landcover_layer.loadNamedStyle(style_path)
    landcover_layer.triggerRepaint()
    

    #Reclassifying the landcover to approximate CN values
    landcover_to_CN_path=os.path.join(output_dir,"reclassified_landcover_CN.tif")
    reclass=processing.run("native:reclassifybytable",
    {'INPUT_RASTER':landcover_layer,
    'RASTER_BAND':1,
    'TABLE':
    #   val    #CN   #Landcover type
    [10,10,55, #Treecover
    20,20,65, #Shrubland
    30,30,70, #Grassland
    40,40,80, #Cropland
    50,50,90, #Builtup 
    60,60,85, #Bare/sparse vegetation
    70,70,95, #Snow and ice 
    80,80,100, #Permanent water bodies 
    90,90,75, #Herbaceous wetlands
    95,95,70, #Mangroves 
    100,100,60], #Moss and lichen
    'NO_DATA':-9999,
    'RANGE_BOUNDARIES':2,
    'DATA_TYPE':5,
    'OUTPUT':landcover_to_CN_path})
    
    #Now we do multiple raster calculations to ultimately 
    #arrive at a Runoff (Q) and Runoff coefficient a (C)
    
    #these are the layer objects we start with
    CN_layer_object=QgsRasterLayer(landcover_to_CN_path,"CN")
    Slope_layer_object=QgsRasterLayer(slope_path,"Slope")
    Annual_rainfall_layer_object=QgsRasterLayer(annual_rain_reproj_path,"Annualrain")
    P95_rainfall_layer_object=QgsRasterLayer(P95_reproj_path,"P95rain")
    
    #and these are paths that the raster calculator will write to 
    CN_slope_adj_path = os.path.join(output_dir,"CN_slope_adj.tif")
    CN_rain_adj_path = os.path.join(output_dir,"CN_rain_adj.tif")
    S_path=os.path.join(output_dir,"S.tif")
    Q_raster_path = os.path.join(output_dir,"Q_raster.tif")
    runoff_coeff_path=os.path.join(output_dir,"Runoff_coeff.tif")
    runoff_volume_path=os.path.join(output_dir,"runoff_volume.tif")
    
    #Step 1: We adjust the CN values based on slope
    entries=[]
    e = QgsRasterCalculatorEntry()
    e.ref = 'CN@1'
    e.raster = CN_layer_object
    e.bandNumber = 1
    entries.append(e)
    
    f=QgsRasterCalculatorEntry()
    f.ref = 'Slope@1'
    f.raster = Slope_layer_object
    f.bandNumber = 1
    entries.append(f)
    
    expression = """
    CN@1 +
    ((Slope@1 > 5) * (Slope@1 <= 10) * 2) +
    ((Slope@1 > 10) * (Slope@1 <= 20) * 5) +
    ((Slope@1 > 20) * 8)
    """

    calc_1 = QgsRasterCalculator(
    expression,
    CN_slope_adj_path,
    'GTiff',
    CN_layer_object.extent(),
    CN_layer_object.width(),
    CN_layer_object.height(),
    entries)
    
    result = calc_1.processCalculation()
    #Output layer object from step 1
    CN_slope_adj_layer_object = QgsRasterLayer(CN_slope_adj_path,"CN_slope_adj")
    
    #Step 2: We use annual rainfall to decide which Antecedant 
    #Moisture condition is prevalent (I,II or III)and adjust 
    #CN based on that 
    entries=[]
    e = QgsRasterCalculatorEntry()
    e.ref = 'CN_slope_adj@1'
    e.raster = CN_slope_adj_layer_object
    e.bandNumber = 1
    entries.append(e)

    f = QgsRasterCalculatorEntry()
    f.ref = 'Annualrain@1'
    f.raster = Annual_rainfall_layer_object
    f.bandNumber = 1
    entries.append(f)
    expression = """
    min(max((
    (Annualrain@1 < 350) *((CN_slope_adj@1 )/(2.281 - 0.01281*CN_slope_adj@1))
    +((Annualrain@1 >= 350) * (Annualrain@1 < 550) *(CN_slope_adj@1))
    +((Annualrain@1 >= 550) *((CN_slope_adj@1 )/(0.427 + 0.00573*CN_slope_adj@1))))
    ,1),100)"""
    
    calc_2 = QgsRasterCalculator(
    expression,
    CN_rain_adj_path,
    'GTiff',
    CN_slope_adj_layer_object.extent(),
    CN_slope_adj_layer_object.width(),
    CN_slope_adj_layer_object.height(),
    entries)

    result = calc_2.processCalculation()
    #Output layer object from step 2
    CN_rain_adj_layer_object = QgsRasterLayer(CN_rain_adj_path,"CN_rain_adj")
    
    #Step 3: We calculate Runoff Q based on a design storm based on the 
    #raster values of P95.
    #Q is calculated from Q=(P-0.2S)^2/(P+0.8S)
    #Where S =(25400/CN_rain_adj)-254
    
    entries=[]
    e = QgsRasterCalculatorEntry()
    e.ref = 'CN_rain_adj@1'
    e.raster = CN_rain_adj_layer_object
    e.bandNumber = 1
    entries.append(e)
    
    expression = """
    (25400 / CN_rain_adj@1) - 254"""
    
    calc_3=QgsRasterCalculator(
    expression,
    S_path,
    'GTiff',
    CN_rain_adj_layer_object.extent(),
    CN_rain_adj_layer_object.width(),
    CN_rain_adj_layer_object.height(),
    entries)
    
    result = calc_3.processCalculation()
    S_layer_object=QgsRasterLayer(S_path,"S")
    
    entries=[]
    e = QgsRasterCalculatorEntry()
    e.ref = 'S@1'
    e.raster = S_layer_object
    e.bandNumber = 1
    entries.append(e)
    
    f = QgsRasterCalculatorEntry()
    f.ref = 'P95rain@1'
    f.raster = P95_rainfall_layer_object
    f.bandNumber = 1
    entries.append(f)
    
    expression = """
    (P95rain@1 > 0.2*S@1) *
    (
    ((P95rain@1 - 0.2*S@1)^2)/
    (P95rain@1 + 0.8*S@1)
    )"""
    
    calc_4 = QgsRasterCalculator(
    expression,
    Q_raster_path,
    'GTiff',
    P95_rainfall_layer_object.extent(),
    P95_rainfall_layer_object.width(),
    P95_rainfall_layer_object.height(),
    entries)

    result = calc_4.processCalculation()
    #Output layer object from step 3
    Q_layer_object = QgsRasterLayer(Q_raster_path,"Q")
    
    #Step 4: Finally we compute the runoff coefficient raster 
    #and runoff volume raster 
    entries=[]
    e = QgsRasterCalculatorEntry()
    e.ref = 'Q@1'
    e.raster = Q_layer_object
    e.bandNumber = 1
    entries.append(e)

    f = QgsRasterCalculatorEntry()
    f.ref = 'P95rain@1'
    f.raster = P95_rainfall_layer_object
    f.bandNumber = 1
    entries.append(f)
    
    expression = """
    (P95rain@1 > 0) * (Q@1 / P95rain@1)"""
    
    calc_5 = QgsRasterCalculator(
    expression,
    runoff_coeff_path,
    'GTiff',
    Q_layer_object.extent(),
    Q_layer_object.width(),
    Q_layer_object.height(),
    entries)

    result = calc_5.processCalculation()

    # Runoff coefficient output layer
    runoff_coeff_layer_object = QgsRasterLayer(runoff_coeff_path,"Runoff_coeff")
    
    entries=[]
    e = QgsRasterCalculatorEntry()
    e.ref = 'Q@1'
    e.raster = Q_layer_object
    e.bandNumber = 1
    entries.append(e)
    
    expression="""(Q@1/1000)*900""" #to get units in m^3/pixel
    calc_6 = QgsRasterCalculator(
    expression,
    runoff_volume_path,
    'GTiff',
    Q_layer_object.extent(),
    Q_layer_object.width(),
    Q_layer_object.height(),
    entries)
    
    
    result = calc_6.processCalculation()
    
    runoff_volume_layer=QgsRasterLayer(runoff_volume_path,"Runoff_vol")
    
    
    #Now we use zonal statistics to find mean runoff coeffiecient per basin
    #and total runoff volume per basin
    for basin_vector_path,basin_vector_object in zip(basin_vector_paths,basin_vector_objects):
        avg_C=processing.run("native:zonalstatisticsfb",
        {'INPUT':basin_vector_path,
        'INPUT_RASTER':runoff_coeff_layer_object,
        'RASTER_BAND':1,
        'COLUMN_PREFIX':'_',
        'STATISTICS':[2],
        'OUTPUT':'TEMPORARY_OUTPUT'})

        #Appending average runoff coeff to attribute table
        vector_join(basin_vector_object,avg_C['OUTPUT'],
        "Mean_runoff_coeff","_mean")
        
        #Normalising average runoff coeff
        normalize(basin_vector_object,"Mean_runoff_coeff","Runoff_coeff_norm")
        
        Total_runoff_vol=processing.run("native:zonalstatisticsfb",
        {'INPUT':basin_vector_path,
        'INPUT_RASTER':runoff_volume_layer,
        'RASTER_BAND':1,
        'COLUMN_PREFIX':'_',
        'STATISTICS':[1],
        'OUTPUT':'TEMPORARY_OUTPUT'})

        #Appending total runoff to attribute table
        vector_join(basin_vector_object,Total_runoff_vol['OUTPUT'],
        "Runoff_volume(m^3)","_sum")

    print("Calculated runoff volume per basin!")

    #Reclassifying landcover to be used later in Flood Risk
    reclass_2=processing.run("native:reclassifybytable",
    {'INPUT_RASTER':landcover_layer,
     'RASTER_BAND':1,
     'TABLE':
    #   val   #Risk(0-1)   #Landcover type
    [10,10,0.2, #Treecover
    20,20,0.2, #Shrubland
    30,30,0.3, #Grassland
    40,40,0.7, #Cropland
    50,50,1,   #Builtup 
    60,60,0, #Bare/sparse vegetation
    70,70,0,   #Snow and ice 
    80,80,0,   #Permanent water bodies 
    90,90,0.1, #Herbaceous wetlands
    95,95,0.1, #Mangroves 
    100,100,0.1],#Moss and lichen 
    'NO_DATA':-9999,
    'RANGE_BOUNDARIES':2,
    'DATA_TYPE':5,
    'OUTPUT':'TEMPORARY_OUTPUT'})

    #Calculating average exposure per basin in each basin vector file
    for basin_vector_path,basin_vector_object,t in zip(basin_vector_paths,basin_vector_objects,threshold):
        exposure_path=os.path.join(output_dir,f"exposure_{t}.gpkg")
        expo=processing.run("native:zonalstatisticsfb",
        {'INPUT':basin_vector_path,
        'INPUT_RASTER':reclass_2['OUTPUT'],
        'RASTER_BAND':1,
        'COLUMN_PREFIX':'_',
        'STATISTICS':[0,1],# this calculates count and sum of pixels 
        'OUTPUT':exposure_path})
        
        exposure_layer=QgsVectorLayer(exposure_path,"exposure")
        exposure_layer.startEditing()
        exposure_layer.dataProvider().addAttributes([QgsField("Exposure", QVariant.Double)])
        exposure_layer.updateFields()
        
        for f in exposure_layer.getFeatures():
            f["Exposure"] = f["_sum"] / f["_count"]
            exposure_layer.updateFeature(f)
            
        exposure_layer.commitChanges()
        
        #Appending the sum and count columns to calculate exposure.
        vector_join(basin_vector_object,exposure_layer,
        "Exposure","Exposure")

    print("Calculated average exposure per basin!")


def drainage_density(stream_5500_output_path,basin_vector_paths,basin_vector_objects):

    #Intersecting the 5500 stream vector with basin vectors
    for basin_vector_path, basin_vector_object in zip(basin_vector_paths,basin_vector_objects):
        intersect=processing.run("native:intersection",
        {'INPUT':stream_5500_output_path,
        'OVERLAY':basin_vector_path,
        'INPUT_FIELDS':[],'OVERLAY_FIELDS':[],
        'OVERLAY_FIELDS_PREFIX':'',
        'OUTPUT':'TEMPORARY_OUTPUT'})
        
        stream_seg=intersect['OUTPUT']
        #Finding length of each stream segment in intersected output
        stream_seg.startEditing()
        prov=stream_seg.dataProvider()
        prov.addAttributes([QgsField("seg_length",QVariant.Double)])
        stream_seg.updateFields()
        
        for f in stream_seg.getFeatures():
            geom = f.geometry()
            if geom is not None and not geom.isEmpty():
                f["seg_length"] = geom.length()
                stream_seg.updateFeature(f)
            else:
                f["seg_length"] = 0
                stream_seg.updateFeature(f)
        stream_seg.commitChanges()
        
        #Dissolving to find stream length per basin
        dissolve=processing.run("gdal:dissolve",
        {'INPUT':stream_seg,
        'FIELD':'Basin_ID',
        'COMPUTE_STATISTICS':True,
        'STATISTICS_ATTRIBUTE':'seg_length',
        'OUTPUT':'TEMPORARY_OUTPUT'})
        
        dissolve_layer=QgsVectorLayer(dissolve['OUTPUT'],"dissolve")
        
        #Appending total stream length 
        vector_join(basin_vector_object,dissolve_layer,
        "Total_stream_len","sum")

        #Compute drainage density
        basin_vector_object.startEditing()
        prov = basin_vector_object.dataProvider()
        prov.addAttributes([QgsField("Drainage_density(km/km2)", QVariant.Double)])
        basin_vector_object.updateFields()
        for f in basin_vector_object.getFeatures():
            if (f.attribute("Total_stream_len") not in (None, QVariant())
            and f.attribute("Area_m2") not in (None, QVariant())
            and f.attribute("Area_m2") > 0):
                f["Drainage_density(km/km2)"] = (f["Total_stream_len"] / f["Area_m2"])*1000
            else:
                f["Drainage_density(km/km2)"] = 0
            basin_vector_object.updateFeature(f)
        basin_vector_object.commitChanges()

        
        #Normalising Drainage density 
        normalize(basin_vector_object,"Drainage_density(km/km2)","Drainage_density_norm")
    print("Drainage density calculations complete!")

def Soil_transmissivity(Ksat_path,soil_thickness_path,basin_vector_objects,basin_vector_paths,watershed_vector_path):
    
    soil_thickness_clip=processing.run("gdal:cliprasterbymasklayer",
    {'INPUT':soil_thickness_path,
    'MASK':watershed_vector_path,
    'TARGET_CRS':target_crs,
    'RESAMPLING':0,
    'OUTPUT':"TEMPORARY_OUTPUT"})
    
    Ksat_clip=processing.run("gdal:cliprasterbymasklayer",
    {'INPUT':Ksat_path,
    'MASK':watershed_vector_path,
    'TARGET_CRS':target_crs,
    'RESAMPLING':0,
    'OUTPUT':"TEMPORARY_OUTPUT"})
    
    for basin_vector_path, basin_vector_object in zip(basin_vector_paths,basin_vector_objects):
        
        soil_thickness_zonal=processing.run("native:zonalstatisticsfb",
        {'INPUT':basin_vector_path,
        'INPUT_RASTER':soil_thickness_clip['OUTPUT'],
        'RASTER_BAND':1,
        'COLUMN_PREFIX':'_',
        'STATISTICS':[2],# mean
        'OUTPUT':"TEMPORARY_OUTPUT"})
        
        vector_join(basin_vector_object,soil_thickness_zonal['OUTPUT'],
        "soil_thickness(m)","_mean")
        
        Ksat_zonal=processing.run("native:zonalstatisticsfb",
        {'INPUT':basin_vector_path,
        'INPUT_RASTER':Ksat_clip['OUTPUT'],
        'RASTER_BAND':1,
        'COLUMN_PREFIX':'_',
        'STATISTICS':[2],# mean
        'OUTPUT':"TEMPORARY_OUTPUT"})
        
        vector_join(basin_vector_object,Ksat_zonal['OUTPUT'],
        "log(Ksat)","_mean")
        
        min_soil_thickness=0.1 #to prevent math errors from taking log(0))
        basin_vector_object.startEditing()
        basin_vector_object.dataProvider().addAttributes([QgsField("Transmissivity(m/day)",QVariant.Double)])
        basin_vector_object.updateFields()
        for f in basin_vector_object.getFeatures():
            soil_thickness=f["soil_thickness(m)"]
            Ksat=f["log(Ksat)"]
            if soil_thickness==0:
                soil_thickness=min_soil_thickness
            if (soil_thickness not in (None, QVariant())
            and Ksat not in (None, QVariant())):
                val=((10**Ksat)*soil_thickness)/100
                f["Transmissivity(m/day)"]=val
            else:
                f["Transmissivity(m/day)"]=0
            basin_vector_object.updateFeature(f)
        basin_vector_object.commitChanges()
        normalize(basin_vector_object,"Transmissivity(m/day)","Transmissivity_norm")
        normalize(basin_vector_object,"Area_m2","Area_norm")
        
def TWI_and_shapefactor(TWI_path,watershed_vector_path,DEM_clipped_path,threshold,output_dir,basin_vector_paths,basin_vector_objects):
    
    #This function calculates TWI(topographic wetness index) and shape factor (Kc) as
    #proxies for spatial wetness and basin elongation respectively.
     
     TWI_object=QgsRasterLayer(TWI_path,"TWI_object")

     ds = gdal.Open(TWI_path)
     band = ds.GetRasterBand(1)
     arr = band.ReadAsArray().astype(float)
     nodata = band.GetNoDataValue()
     if nodata is not None:
         arr = arr[arr != nodata]
     twi_crit = np.nanpercentile(arr,90)
     
     #Creating a binary raster of pixels where TWI>TWI_crit
     binary_raster_path=os.path.join(output_dir,"Binary_raster_TWI")
     entries=[]
     e = QgsRasterCalculatorEntry()
     e.ref = 'twi@1'
     e.raster = TWI_object
     e.bandNumber = 1
     entries.append(e)
     
     calc = QgsRasterCalculator(
     f"twi@1>{twi_crit}",
     binary_raster_path ,
     'GTiff',
     TWI_object.extent(),
     TWI_object.width(),
     TWI_object.height(),
     entries)

     calc.processCalculation()
     pixel_area=TWI_object.rasterUnitsPerPixelX()*TWI_object.rasterUnitsPerPixelY()
     
     #Calculating fraction of area per subbasin where TWI>TWIcrit
     for basin_vector_path,basin_vector_object in zip(basin_vector_paths,basin_vector_objects):
         #First finding number of pixels in each subbasin where TWI>TWI_crit
         TWI_sum=processing.run("native:zonalstatisticsfb",
         {'INPUT':basin_vector_path,
         'INPUT_RASTER':binary_raster_path,
         'RASTER_BAND':1,
         'COLUMN_PREFIX':'_',
         'STATISTICS':[1],
         'OUTPUT':'TEMPORARY_OUTPUT'})
         
         #Then adding an attribute column for TWI_exceed_frac
         #TWI_exceed_frac=(Area where TWI>TWI_crit)/(Basin Area)
         TWI_sum_object=(TWI_sum['OUTPUT'])
         TWI_sum_object.startEditing()
         TWI_sum_object.dataProvider().addAttributes([QgsField("TWI_exceed_frac",QVariant.Double)])
         TWI_sum_object.updateFields()
         for f in TWI_sum_object.getFeatures():
            if (f.attribute("_sum") not in (None, QVariant())):
                f["TWI_exceed_frac"]=(f["_sum"]*pixel_area)/f["Area_m2"]
            else:
                f["TWI_exceed_frac"]=0
            TWI_sum_object.updateFeature(f)
         TWI_sum_object.commitChanges()
         
         #Appending and normalising TWI_exceed fraction to basin_vector_layer
         vector_join (basin_vector_object,TWI_sum_object,
         "TWI_exceed_frac","TWI_exceed_frac")
        
         normalize(basin_vector_object,"TWI_exceed_frac","TWI_exceedance_norm")
     
     print("TWI calculations complete!")
      
     #Shape parameter calculations
     for basin_vector_path,basin_vector_object in zip(basin_vector_paths,basin_vector_objects):
         basin_vector_object.startEditing()
         basin_vector_object.dataProvider().addAttributes([QgsField("Shape_factor/Kc",QVariant.Double)])
         basin_vector_object.updateFields()
         for f in basin_vector_object.getFeatures():
             f["Shape_factor/Kc"]=f.geometry().length()/(2*math.sqrt(math.pi*f["Area_m2"]))
             basin_vector_object.updateFeature(f)
         basin_vector_object.commitChanges()
         
         #normalising Kc
         normalize(basin_vector_object,"Shape_factor/Kc","Shapefactor/Kc_norm")
     
     print("Shape factor calcualtions complete!")

def FSI_and_Flood_Risk(basin_vector_paths, basin_vector_objects):
    # This function calculates FSI (Flood Susceptibility Index) using a weighted 
    # linear combination of the five geomorphic and hydrologic parameters
    # (Shape_factor(Kc), Drainage_density, Infiltration potential, 
    # TWI (Topographic wetness index) and mean slope) 
    # in their normalised forms.
    # The weights reflect the relative influence of each parameter on flood
    # generation.
    # FSI is then rainfall-adjusted using P95 rainfall.
    # Flood Risk is finally estimated by combining the rainfall-adjusted
    # FSI with normalized exposure for each subbasin.
    
    for basin_vector_object in basin_vector_objects:
        normalize(basin_vector_object,"Mean_slope(%)","Slope_norm")

    for basin_vector_path, basin_vector_object in zip(basin_vector_paths, basin_vector_objects):
        basin_vector_object.startEditing()
        basin_vector_object.dataProvider().addAttributes([
        QgsField("FSI_geomorph", QVariant.Double),
        QgsField("FSI_rainfall", QVariant.Double),
        QgsField("Flood_Risk", QVariant.Double),
        QgsField("Hillslope_FSI_Contribution_%",QVariant.Double),
        QgsField("Area_km2",QVariant.Double)])
        basin_vector_object.updateFields()
        
        for f in basin_vector_object.getFeatures():
            
            area_km2=f["Area_m2"]/1000000
            f["Area_km2"]=area_km2
            
            #RGP= Runoff generating potential
            RGP=(
            (0.3*f["TWI_exceedance_norm"]+
            0.35*f["Runoff_coeff_norm"]+
            0.15*f["Slope_norm"])+
            0.2*(1-f["Transmissivity_norm"]))
            
            #RFP= Routing and floodplain potential
            RFP=(
            0.35*f["Drainage_density_norm"]+
            0.35*f["HAND_frac_norm"]+
            0.1*f["Transmissivity_norm"]+
            0.2*(1-f["Shapefactor/Kc_norm"])
            )
            
            Riverine_index=RFP/(RFP+RGP)
            #(1-0) values closer to 1 indicate more riverine regime
            
            f["FSI_geomorph"]=((1-Riverine_index)*RGP)+ (Riverine_index*RFP)
            
            f["Hillslope_FSI_Contribution_%"]=(((1-Riverine_index)*RGP)/f["FSI_geomorph"])*100
            #simply the proportion of FSI_geomorph contributed by hillslope parameters
            
            #Now for rain adjustments 
            # For daily CHIRPS, we use a smaller boost factor for hillslope regimes
            # Studies suggest 20-30% underestimation of extremes see methodology for reference
            hillslope_rain_boost_factor = 1.25
            
            f["FSI_rainfall"]=(
            ((1-Riverine_index)*RGP*f["P95_rain_norm"]*hillslope_rain_boost_factor)+
            ((Riverine_index*RFP)*f["P95_rain_norm"])
            )
            
            f["Flood_Risk"]=f["FSI_rainfall"]*f["Exposure"]
            basin_vector_object.updateFeature(f)
        
        basin_vector_object.commitChanges()
    print("FSI and Flood Risk calculations complete!")
    

def layer_styling_and_misc(basin_vector_objects, threshold, output_dir,watershed_vector_path,DEM_clipped_path):
    #This function helps clean up intermediate attribute columns in the basin vectors 
    #to show what is relevant and styles them to show FSI and flood risk spatially. 
    #It also styles other layers for visual effect
    
    METRIC_STYLES ={"FSI": STYLE_PATHS["fsi"],
    "Flood_Risk": STYLE_PATHS["risk"]}

    for t,b in zip(threshold,basin_vector_objects):
         source=b
         
         for metric, style_path in METRIC_STYLES.items():
            #Duplicating the basin vector layers and choosing relevant attributes to keep 
            basin_final_path=os.path.join(output_dir,f"{metric}_basins_final_{t}.gpkg")
            fields_mapping = [
            {"name": "fid", "expression": "\"fid\"", "type": 4, "length": 0, "precision": 0},
            {"name": "Basin_ID", "expression": "\"Basin_ID\"", "type": 2, "length": 0, "precision": 0},
            {"name": "Area_km2", "expression": "\"Area_km2\"", "type": 6, "length": 0, "precision": 3},
            {"name": "P95_rainfall(mm/day)", "expression": "\"P95_rainfall(mm/day)\"", "type": 6, "length": 0, "precision": 2},
            {"name": "Mean_runoff_coeff", "expression": "\"Mean_runoff_coeff\"", "type": 6, "length": 0, "precision": 2},
            {"name": "Runoff_volume(m^3)", "expression": "\"Runoff_volume(m^3)\"", "type": 6, "length": 0, "precision": 2},
            {"name": "Mean_slope(%)", "expression": "\"Mean_slope(%)\"", "type": 6, "length": 0, "precision": 4},
            {"name": "Flood_Risk", "expression": "\"Flood_Risk\"", "type": 6, "length": 0, "precision": 4},
            {"name": "FSI_geomorph", "expression": "\"FSI_geomorph\"", "type": 6, "length": 0, "precision": 4},
            {"name": "Hillslope_FSI_Contribution_%", "expression": "\"Hillslope_FSI_Contribution_%\"", "type": 6, "length": 0, "precision": 2},
            {"name": "FSI_rainfall", "expression": "\"FSI_rainfall\"", "type": 6, "length": 0, "precision": 4},
            {"name": "Exposure", "expression": "\"Exposure\"", "type": 6, "length": 0, "precision": 4},
            {"name": "HAND_frac", "expression": "\"HAND_frac\"", "type": 6, "length": 0, "precision": 4},
            {"name": "Drainage_density(km/km2)", "expression": "\"Drainage_density(km/km2)\"", "type": 6, "length": 0, "precision": 4},
            {"name": "TWI_exceed_frac", "expression": "\"TWI_exceedance_norm\"", "type": 6, "length": 0, "precision": 4},
            {"name": "Shape_factor/Kc", "expression": "\"Shape_factor/Kc\"", "type": 6, "length": 0, "precision": 4},
            {"name": "Transmissivity(m/day)", "expression": "\"Transmissivity(m/day)\"", "type": 6, "length": 0, "precision": 4}]
            
            processing.run("native:refactorfields",
            {"INPUT": source,
            "FIELDS_MAPPING": fields_mapping,
            "OUTPUT": basin_final_path})
            
            basin_final=QgsVectorLayer(basin_final_path,f"{metric}_{t}","ogr")
            #styling basins based on FSI and Flood risk and adding to map 
            basin_final.loadNamedStyle(style_path)
            basin_final.triggerRepaint()
            QgsProject.instance().addMapLayer(basin_final)
    
    #Based on the watershed extent and range of values the number of classes for both
    #FSI and flood risk may need to be changed in the layer styling panel for 
    #appropriate representation. The default number of classes is 8 
    
    #Styling and duplicating Clipped_DEM to create hillshade 
    clipped_DEM = QgsProject.instance().mapLayersByName("Clipped_DEM")[0]
    clipped_DEM.loadNamedStyle(STYLE_PATHS["dem"])
    clipped_DEM.triggerRepaint()

    hillshade=clipped_DEM.clone()
    hillshade.setName("Hillshade")
    QgsProject.instance().addMapLayer(hillshade)
    hillshade.loadNamedStyle(STYLE_PATHS["hillshade"])
    hillshade.triggerRepaint()
    
    #styling watershed vector 
    watershed_vec=QgsProject.instance().mapLayersByName("Watershed_vector")[0]
    watershed_vec.loadNamedStyle(STYLE_PATHS["watershed"])
    watershed_vec.triggerRepaint()


def HAND(accum_clipped_path,HAND_script_path, DEM_clipped_path,output_dir, basin_vector_paths, basin_vector_objects):
    #This function calculates the HAND raster from GRASS and then the 
    #HAND fraction per basin which is (area where HAND<5m)/(Total basin area)
    #read more in methodology
    
    threshold = 5500

    cmd = [
        GRASS_path,
        grass_location_path,
        "--exec",
        "python",
        HAND_script_path,
        DEM_clipped_path,
        output_dir,
        str(threshold),
        accum_clipped_path]

    subprocess.run(cmd, check=True)
    
    HAND_output_path = os.path.join(output_dir, "HAND.tif")
    stream_5500_output_path = os.path.join(output_dir, "streams_5500.gpkg")
    
    HAND_layer_object=QgsRasterLayer(HAND_output_path,"HAND")
    
    #Creating a binary raster of pixels where HAND<5m
    binary_raster_path=os.path.join(output_dir,"Binary_raster_HAND.tif")
    entries=[]
    e = QgsRasterCalculatorEntry()
    e.ref = 'HAND@1'
    e.raster = HAND_layer_object
    e.bandNumber = 1
    entries.append(e)

    calc = QgsRasterCalculator(
    "if( (HAND@1 < 5) AND (HAND@1 > 0), 1, 0)",
    binary_raster_path ,
    'GTiff',
    HAND_layer_object.extent(),
    HAND_layer_object.width(),
    HAND_layer_object.height(),
    entries)
    
    result = calc.processCalculation()
    pixel_area=HAND_layer_object.rasterUnitsPerPixelX()*HAND_layer_object.rasterUnitsPerPixelY()
    
    #Calculating area of HAND<5m/Total basin area 
    for basin_vector_path,basin_vector_object in zip(basin_vector_paths,basin_vector_objects):
        #First finding number of pixels in each subbasin where HAND<5m
        HAND_sum=processing.run("native:zonalstatisticsfb",
        {'INPUT':basin_vector_path,
        'INPUT_RASTER':binary_raster_path,
        'RASTER_BAND':1,
        'COLUMN_PREFIX':'_',
        'STATISTICS':[1],
        'OUTPUT':'TEMPORARY_OUTPUT'})
        
        #Then adding an attribute column for HAND<5m/Total basin area
        HAND_sum_object=(HAND_sum['OUTPUT'])
        HAND_sum_object.startEditing()
        HAND_sum_object.dataProvider().addAttributes([QgsField("HAND_frac",QVariant.Double)])
        HAND_sum_object.updateFields()
        for f in HAND_sum_object.getFeatures():
            if (f.attribute("_sum") not in (None, QVariant())):
                f["HAND_frac"]=(f["_sum"]*pixel_area)/f["Area_m2"]
            else:
                f["HAND_frac"]=0
            HAND_sum_object.updateFeature(f)
        HAND_sum_object.commitChanges()
         
        #Appending and normalising HAND_fraction to basin_vector_layer
        vector_join (basin_vector_object,HAND_sum_object,
        "HAND_frac","HAND_frac")
        
        normalize(basin_vector_object,"HAND_frac","HAND_frac_norm")
    
    print("HAND calculations complete!")
    return stream_5500_output_path


def stream_strahler_ordering(accum_clipped_path,watershed_vector_path,strahler_script_path,DEM_clipped_path,strahler_threshold,output_dir):
    
    #This function uses GRASS to compute strahler order for streams 
    #for the strahler_threshold which can be a list eg:[10000,20000]
    #It is for visualisation and does not influence the flood related processing 
    
    cmd = [GRASS_path,
    grass_location_path,
    "--exec",
    "python",
    strahler_script_path,
    DEM_clipped_path,
    output_dir,
    accum_clipped_path,
    ] + [str(t) for t in strahler_threshold]

    subprocess.run(cmd, check=True)
    
    output_paths = []

    for t in strahler_threshold:
        strahler_output_path=os.path.join(output_dir,f"Strahler_streams_{t}.gpkg")
        #Adding strahler_vec to map 
        strahler_layer=QgsVectorLayer(strahler_output_path,f"Strahler_streams_{t}","ogr")
        QgsProject.instance().addMapLayer(strahler_layer)
        
        #Styling the strahler layer
        strahler_layer.loadNamedStyle(STYLE_PATHS["strahler"])
        strahler_layer.triggerRepaint()

def Folder_cleanup(output_dir):
    #This function deletes intermediate rasters after all calculations are done
    #to save disk space. 

    basin_vector_paths=[]
    stream_vector_paths=[]
    flood_risk_paths=[]
    fsi_paths=[]
    for t in threshold:
        basin_vector_path=os.path.join(output_dir,f"Basin_vector_{t}.gpkg")
        stream_vector_path=os.path.join(output_dir,f"Stream_vector_{t}.gpkg")
        fsi_path= os.path.join(output_dir,f"FSI_basins_final_{t}.gpkg")
        flood_risk_path= os.path.join(output_dir,f"Flood_Risk_basins_final_{t}.gpkg")
        basin_vector_paths.append(basin_vector_path)
        stream_vector_paths.append(stream_vector_path)
        flood_risk_paths.append(flood_risk_path)
        fsi_paths.append(fsi_path)
    
    strahler_paths=[]
    for t in strahler_threshold:
        strahler_output_path=os.path.join(output_dir,f"Strahler_streams_{t}.gpkg")
        strahler_paths.append(strahler_output_path)


    paths_to_keep=[
    os.path.join(output_dir,"Watershed_vector.gpkg"),
    os.path.join(output_dir,"Stream_Outlet_Point.gpkg"),
    os.path.join(output_dir,"Landcover.tif"),
    os.path.join(output_dir,"DEM.tif"),
    os.path.join(output_dir,"Clipped_DEM.tif"),
    ]
    
    paths_to_keep.extend(fsi_paths+flood_risk_paths+stream_vector_paths+
    basin_vector_paths+strahler_paths)
    
    delete_extensions = (".tif", ".gpkg")
    
    for filename in os.listdir(output_dir):
        file_path = os.path.join(output_dir, filename)
        if os.path.isfile(file_path):
            if filename.lower().endswith(delete_extensions):
                if file_path not in paths_to_keep:
                    os.remove(file_path)
    
    shutil.rmtree(grass_location_path)
  
def vector_join (vect_layer_object,stat_layer,vect_stat_title,temp_title):
    #This function joins an attribute column (temp_title)on a temporary
    #vector layer (stat_layer)to an existing vector layer on file (vect_layer)
    stat_lookup={}
    for f in stat_layer.getFeatures():
        stat_lookup[f["Basin_ID"]]=f[temp_title]

    vect_layer_object.startEditing()
    provider = vect_layer_object.dataProvider()
    provider.addAttributes([QgsField(vect_stat_title, QVariant.Double)])
    vect_layer_object.updateFields()
    
    for f in vect_layer_object.getFeatures():
        basin_id = f["Basin_ID"]
        if basin_id in stat_lookup:
            f[vect_stat_title] = stat_lookup[basin_id]
            vect_layer_object.updateFeature(f)
    vect_layer_object.commitChanges()

def normalize(layer_object,field,normalised_title):
    #This function will normalise the fields used in calculations
    # to a scale of 0-1 for computing FSI and Flood Risk. 
    values=[]
    layer_object.startEditing()
    for f in layer_object.getFeatures():
        val=f.attribute(field)
        if (val is None or val == NULL or 
        (isinstance(val, QVariant)and val.isNull())):
            continue
        values.append(val)
    if not values:
        layer_object.commitChanges()
        raise ValueError(f"No valid values found for field '{field}'")
    layer_object.dataProvider().addAttributes([QgsField(normalised_title, QVariant.Double)])
    layer_object.updateFields()
    min_value=min(values)
    max_value=max(values)
    for f in layer_object.getFeatures():
        x=f.attribute(field)
        if (x is None or x == NULL or 
        (isinstance(x, QVariant)and x.isNull())):
            mean_value = sum(values) / len(values)
            x = mean_value
        val=(x-min_value)/(max_value-min_value)
        f[normalised_title]=val
        layer_object.updateFeature(f)
    layer_object.commitChanges()

def Final_message(threshold):
    """
    Prints a message showing the recommended layer order for the user
    to manually reorder the layers
    """
    order_list = []
    order_list.extend([
    "Hillshade",
    "Clipped_DEM",
    "Watershed_vector",
    "Landcover"])
    for t in threshold:
        order_list.append(f"Basin_vector{t}")
        order_list.append(f"Stream_vector{t}")
    for t in threshold:
        order_list.append(f"FSI_{t}")
        order_list.append(f"Flood_Risk_{t}")
    order_list.append("Any strahler_streams layer/stream_vector")
    order_list.append("Stream_Outlet_Point")
    order_list.reverse()
    print("\n✅The project is now complete!")
    print("Please reorder your layers in the following order (top → bottom) in QGIS:\n")
    for i, name in enumerate(order_list, start=1):
        print(f"{i}. {name}")
    print()
    print("Once that is done, click on the FSI_basins_final, Flood_Risk_basins_final and Clipped_DEM layers")
    print("and click classify in the layers styling panel for each layer to interpret results.")
    print("In the layer styling panel for strahler layers, click on the interpolated line "
    "\nand click the refresh button beside Min and Max value and adjust the width to your preference")
    print("Investigate the spatial distributions of other parameters such as rainfall and TWI in either the Flood_Risk or FSI layers"
    "\nThere is also annual rainfall and soil thickness data in the Basin_vector layers "
    "\nYou can also drag rasters from the output_dir like the S_raster showing maximum storage or the"
    "n\Binary_raster_HAND to see areas where elevation is withing 5m of drainage")
    print("In general get creative and explore different data")
    print("If you have finished viewing/ are not concerned with the intermediary rasters and would like to free up space in your output_dir"
    "\ntype Folder_cleanup(output_dir) in the terminal")
    print("\nFor a purely hydrological render of the watershed keep these layers on in this order"
    "\nStream_Outlet_Point"
    "\nAny strahler_vector layer"
    "\nWatershed_vector"
    "\nClipped_DEM"
    "\nHillshade"
    "\nand turn all other layers off."
    "\nAdjust the layer rendering (gamma/brightness/saturation) settings"
    "\non Clipped_DEM and Hillshade to your preference."
    "\nThank you!")



    
    




    
    





