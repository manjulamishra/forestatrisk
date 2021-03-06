#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ==============================================================================
# author          :Ghislain Vieilledent
# email           :ghislain.vieilledent@cirad.fr, ghislainv@gmail.com
# web             :https://ecology.ghislainv.fr
# python_version  :>=2.7
# license         :GPLv3
# ==============================================================================

# Annual product legend
# 0. Other land-cover
# 1. Undisturbed forest at the beginning of the archive (1985-2007)
# 2. Old regrowth
# 3. Young regrowth
# 4. Deforested in 1986-2013
# 5. Deforested in 2014-2016
# 6. Disturbed in 2014-2016
# 7. Loss for water
# 8. Loss for plantation
# 9. NoData and Forest at the beginning of the archive
# 10. NoData and NonForest at the beginning of the archive

# Imports
from __future__ import division, print_function  # Python 3 compatibility
import ee
import time
import os
from google.cloud import storage

# Initialize
ee.Initialize()


# ee_roadless.run_task
def run_task(iso3, extent_latlong, scale=30, proj=None,
             gs_bucket=None):
    """Compute forest-cover change with Google EarthEngine.

    Compute the forest-cover change from Global Forest Change data
    with Python and GEE API. Export the results to Google Cloud
    Storage.

    Notes for GOOGLE EARTH ENGINE (abbreviated GEE):
    - GEE account is needed: https://earthengine.google.com.
    - GEE API Python client is needed: \
    https://developers.google.com/earth-engine/python_install.

    :param iso3: Country ISO 3166-1 alpha-3 code.
    :param extent_latlong: List/tuple of region extent in lat/long
    (xmin, ymin, xmax, ymax).
    :param scale: Resolution in meters per pixel. Default to 30.
    :param proj: The projection for the export.
    :param gs_bucket: Name of the google storage bucket to export to.

    :return: Google EarthEngine task.

    """

    # Region
    region = ee.Geometry.Rectangle(extent_latlong, proj="EPSG:4326",
                                   geodesic=False)
    region = region.buffer(10000).bounds()
    export_coord = region.getInfo()["coordinates"]

    # Path to roadless products
    path = "users/vancuch/"

    # Roadless annual product (AP)
    AP = ee.ImageCollection(path + "collectionPeriod_AnnualChanges")
    AP = AP.mosaic().toByte().clip(region)

    # Forest in 2017
    # ap_2017 = AP.select(["Jan2017"])
    # forest2017 = ap_2017.eq(1)

    # Note to be deleted: with version Janv2018 of Christelle product, forest
    # at year Y if 1, 13 or 14.

    # ap_allYear
    ap_allYear = AP.where(AP.neq(1), 0)

    # Forest in 2015
    ap_2015_2017 = ap_allYear.select(range(29, 32))
    forest2015 = ap_2015_2017.reduce(ee.Reducer.sum())
    forest2015 = forest2015.gte(1)

    # Forest cover 2010
    ap_2010_2017 = ap_allYear.select(range(24, 32))
    forest2010 = ap_2010_2017.reduce(ee.Reducer.sum())
    forest2010 = forest2010.gte(1)

    # Forest cover 2005
    ap_2005_2017 = ap_allYear.select(range(19, 32))
    forest2005 = ap_2005_2017.reduce(ee.Reducer.sum())
    forest2005 = forest2005.gte(1)

    # Forest cover 2000
    ap_2000_2017 = ap_allYear.select(range(14, 32))
    forest2000 = ap_2000_2017.reduce(ee.Reducer.sum())
    forest2000 = forest2000.gte(1)

    # Forest raster with four bands
    forest = forest2000.addBands(forest2005).addBands(
        forest2010).addBands(forest2015)
    forest = forest.select([0, 1, 2, 3], ["forest2000", "forest2005",
                                          "forest2010", "forest2015"])
    forest = forest.set("system:bandNames", ["forest2000", "forest2005",
                                             "forest2010", "forest2015"])

    # maxPixels
    maxPix = 1e13

    # Export forest to cloud storage
    # ! region must be lat/long coordinates with Python API.
    task = ee.batch.Export.image.toCloudStorage(
        image=forest,
        description="roadless_" + iso3,
        bucket=gs_bucket,
        region=export_coord,
        scale=scale,
        maxPixels=maxPix,
        crs=proj,
        fileNamePrefix="roadless/forest_" + iso3)
    task.start()

    # Return task
    return(task)


# ee_roadless.check
def check(gs_bucket, iso3):
    """Function to check if the forest cover data are already present in
    the Google Cloud Storage (GCS) bucket.

    :param gs_bucket: the GCS bucket to look in.
    :param iso3: Country ISO 3166-1 alpha-3 code.

    :return: A boolean indicating the presence (True) of the data in
    the bucket.

    """

    # Connect to GCS bucket
    client = storage.Client()
    bucket = client.get_bucket(gs_bucket)
    # Filename to find
    fname = "roadless/forest_" + iso3
    # Get a list of the blobs
    iterator = bucket.list_blobs()
    blobs = list(iterator)
    # Loop on blobs
    present_in_bucket = False
    for b in blobs:
        if b.name.find(fname) == 0:
            present_in_bucket = True
            break
    # Return
    return(present_in_bucket)


# ee_roadless.download
def download(gs_bucket, iso3, path):
    """Download forest-cover data from Google Cloud Storage.

    Check that GEE tasks are completed. Download forest-cover data
    from Google Cloud Storage in the current working directory. This
    function uses the gsutil command
    (https://cloud.google.com/storage/docs/gsutil)

    :param gs_bucket: Name of the google storage bucket to download from.
    :param iso3: Country ISO 3166-1 alpha-3 code.
    :param path: Path to download files to.

    """

    # Data availability
    data_availability = check(gs_bucket, iso3)

    # Check task status
    while data_availability is False:
            # We wait 1 min
            time.sleep(60)
            # We reactualize the status
            data_availability = check(gs_bucket, iso3)

    # Commands to download results with gsutil
    cmd = ["gsutil cp gs://", gs_bucket,
           "/roadless/forest_", iso3, "*.tif ", path]
    cmd = "".join(cmd)
    os.system(cmd)

# End
