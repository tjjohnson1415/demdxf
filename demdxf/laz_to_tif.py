import laspy
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree
import rasterio
from rasterio.transform import from_origin

def _idw_interpolation(x, y, z, grid_x, grid_y, k = 10, power = 2):
    """
    x, y, z: point cloud arrays
    grid_x, grid_y: raster coordinates
    k: number of nearest neighbors
    power: IDW alpha parameter
    """

    #Build KDTree
    tree = cKDTree(np.vstack((x, y)).T)

    #Find the k nearest neighbors for each grid cell
    dist, idx = tree.query(np.vstack((grid_x.ravel(), grid_y.ravel())).T, k = k)

    #Avoid division by zero
    dist = np.where(dist == 0, 1e-12, dist)

    #Compute weights
    weights = 1 / dist**power

    #Compute weighted average
    z_vals = np.sum(weights * z[idx], axis = 1) / np.sum(weights, axis = 1)

    return z_vals.reshape(grid_x.shape)

def laz_to_tif(laz_file, output_path, laz_crs = None):

    laz = laspy.read(laz_file)
    x, y, z = laz.x, laz.y, laz.z

    xmin, xmax = x.min(), x.max()
    ymin, ymax = y.min(), y.max()
    tif_resolution = 1 #resolution of the raster in map units (meters)
    
    grid_x, grid_y = np.meshgrid(np.arange(xmin, xmax, tif_resolution), np.arange(ymin, ymax, tif_resolution))

    raster = _idw_interpolation(x, y, z, grid_x, grid_y)

    transform = from_origin(xmin, ymax, tif_resolution, tif_resolution)

    crs = laz.header.parse_crs()
    if not crs:
        if laz_crs:
            crs = laz_crs
        else:
            print('CRS of LAZ file not found. Please include it as the `las_crs` parameter.')
            pass

    with rasterio.open(
        output_path,
        'w',
        driver = 'GTiff',
        height = np.flipud(raster).shape[0],
        width = np.flipud(raster).shape[1],
        count = 1,
        dtype = 'float32',
        crs = crs,
        transform = transform
    ) as dst:
        dst.write(np.flipud(raster).astype('float32'), 1)
    