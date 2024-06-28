import ee
ee.Authenticate()
ee.Initialize()
import geemap
import os

def addFile(file_path):
    
    file_extension = os.path.splitext(file_path)[1].lower()

    if file_extension == '.json' or file_extension == '.geojson':
        ee_object = geemap.geojson_to_ee(file_path)
    elif file_extension == '.shp':
        ee_object = geemap.shp_to_ee(file_path)
    else:
        raise ValueError("Unsupported file format. Supported formats: GeoJSON (.json, .geojson) and shapefile (.shp)")

    return ee_object

def exportImage(img, name, region, scale):
    try:
        export = geemap.download_ee_image(img,name,scale=scale,region=region,crs='EPSG:4326')
        return export
    except Exception as e:
        print("exportImage Error:", e)
        return None

def set_date_range(start_date_str, end_date_str, max_cloud_probability):
    start_date = ee.Date(start_date_str)
    end_date = ee.Date(end_date_str)
    return start_date, end_date, max_cloud_probability

def maskClouds(img) :
    clouds = ee.Image(img.get('cloud_mask')).select('probability')
    isNotCloud = clouds.lt(MAX_CLOUD_PROBABILITY)
    return img.updateMask(isNotCloud)

def maskEdges(s2_img):
    return s2_img.updateMask(
      s2_img.select('B8A').mask().updateMask(s2_img.select('B9').mask()))

def calculate_ndvi(image):
    
    ndvi = image.normalizedDifference(['B8', 'B4']).rename('ndvi')

    return ndvi

def main():

    try:

        geojson_path = "D:/Vaishnavi/daruka/yellowstone.shp"
        roi = addFile(geojson_path)
        region = roi.geometry()

        s2Sr= ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        s2Clouds = ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')

        global MAX_CLOUD_PROBABILITY
        START_DATE, END_DATE, MAX_CLOUD_PROBABILITY = set_date_range('2023-01-01', '2023-12-31', 20)

        criteria = ee.Filter.And(ee.Filter.bounds(roi), ee.Filter.date(START_DATE, END_DATE))
        s2Sr = s2Sr.filter(criteria).map(maskEdges)
        s2Clouds = s2Clouds.filter(criteria)

        filter_condition = ee.Filter.equals(leftField='system:index', rightField='system:index')

        s2SrWithCloudMask = ee.Join.saveFirst('cloud_mask').apply(
            primary=s2Sr,
            secondary=s2Clouds,
            condition=filter_condition
        )

        s2CloudMasked = ee.ImageCollection(s2SrWithCloudMask).map(maskClouds).median().clip(roi)

        dem = ee.Image('USGS/SRTMGL1_003').clip(roi)
        dem = dem.updateMask(dem.gt(0))

        # save outputs in the directory
        SAVE_DIRECTORY = "D:/Vaishnavi/daruka"
        if not os.path.exists(SAVE_DIRECTORY):
            os.makedirs(SAVE_DIRECTORY)

        ndvi_tif = os.path.join(SAVE_DIRECTORY, 'ndvi.tif')
        elevation_tif = os.path.join(SAVE_DIRECTORY, 'elevation.tif')

        ndvi_index = calculate_ndvi(s2CloudMasked)
        elevation = dem.select('elevation')

        exportImage(ndvi_index, ndvi_tif, region, 10)
        exportImage(elevation, elevation_tif, region, 30)

    except Exception as e:
        print("Error:", e)
        return None

main()
