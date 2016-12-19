#!/usr/bin/python

# ==============================================================================
# author          :Ghislain Vieilledent
# email           :ghislain.vieilledent@cirad.fr, ghislainv@gmail.com
# web             :https://ghislainv.github.io
# python_version  :2.7
# license         :GPLv3
# ==============================================================================

# Import
import sys
import os
from osgeo import gdal
from glob import glob
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

# test
var_dir = "/home/ghislain/pyprojects/deforpy/data/"
output_file = "/home/ghislain/pyprojects/deforpy/output/var.pdf"
grid_size = (2, 2)
figsize = (8.27, 11.69)
dpi = 300


# plot_var
def plot_var(var_dir,
             output_file="output/var.pdf",
             grid_size=(3, 3),
             figsize=(8.27, 11.69),
             dpi=200):
    """Plot variable maps.

    This function plots variable maps.

    :param var_dir: path to variable directory.
    :param output_file: name of the plot file.
    :param grid_size: grid size per page.
    :param figsize: figure size in inches.
    :param dpi: resolution for output image.
    :return: list of Matplotlib figures.

    """

    # Raster list
    var_tif = var_dir + "/*.tif"
    raster_list = glob(var_tif)
    raster_list.sort()
    nrast = len(raster_list)

    # The PDF document
    pdf_pages = PdfPages(output_file)
    # Generate the pages
    grid_size = grid_size
    ny = grid_size[0]
    nx = grid_size[1]
    nplot_per_page = ny*nx
    # List of figures to be returned
    figures = []

    # Loop on raster files
    for i in range(nrast):

        # Create a figure instance (ie. a new page) if needed
        if i % nplot_per_page == 0:
            fig = plt.figure(figsize=figsize, dpi=dpi)

        # Open raster and get band
        r = gdal.Open(raster_list[i])
        b = r.GetRasterBand(1)
        ND = b.GetNoDataValue()
        if ND is None:
            print("NoData value is not specified \
            for input raster file %s" % raster_list[i])
            sys.exit(1)

        # Raster name
        base_name = os.path.basename(raster_list[i])
        index_dot = base_name.index(".")
        raster_name = base_name[:index_dot]

        # Raster info
        gt = r.GetGeoTransform()
        ncol = r.RasterXSize
        nrow = r.RasterYSize
        Xmin = gt[0]
        Xmax = gt[0] + gt[1] * ncol
        Ymin = gt[3] + gt[5] * nrow
        Ymax = gt[3]
        extent = [Xmin, Xmax, Ymin, Ymax]

        # Overviews
        if b.GetOverviewCount() == 0:
            # Build overviews
            print("Build overview")
            r.BuildOverviews("nearest", [8, 16, 32])
        # Get data from finest overview
        ov_band = b.GetOverview(0)
        ov_arr = ov_band.ReadAsArray()
        mov_arr = np.ma.array(ov_arr, mask=(ov_arr == ND))
        # Plot raster
        ax = plt.subplot2grid(grid_size,
                              ((i % (ny*nx))/nx, i % nx))
        ax.set_frame_on(False)
        ax.set_xticks([])
        ax.set_yticks([])
        plt.imshow(mov_arr, extent=extent)
        plt.title(raster_name)
        plt.axis("off")

        # Close the page if needed
        if (i + 1) % nplot_per_page == 0 or (i + 1) == nrast:
            plt.tight_layout()
            figures.append(fig)
            pdf_pages.savefig(fig)

    # Write the PDF document to the disk
    pdf_pages.close()
    return (figures)

# End