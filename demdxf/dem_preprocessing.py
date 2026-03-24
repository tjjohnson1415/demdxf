import rasterio
import numpy as np
import matplotlib.pyplot as plt

def display_dem(dem):
    '''
    Function for plotting a DEM
        dem - DEM
    '''
    plt.imshow(dem, origin = 'lower', cmap = 'viridis')
    plt.show()

    print(f'Rows: {dem.shape[0]}, Columns: {dem.shape[1]}')

    return None


def load_dem(path):
    '''
    Function for loading a DEM.
        path - file path to locally stored DEM
    '''
    with rasterio.open(path) as src:
        data = src.read(1) # read the DEM
        try: # extract no data value if it exists
            nodata = src.nodata
        except:
            pass

    if nodata:
        mask = np.isclose(data, nodata, rtol = 1e-5, atol = 1e-5) # create a missing data mask
        data = np.ma.masked_array(data, mask) # mask out missing data

    data = np.flipud(data)

    display_dem(data)

    return data

def trim_dem(dem, xmin, xmax, ymin, ymax):
    '''
    Function for trimming a DEM to a desired extent
        dem - DEM
        xmin - minimum x-coordinate
        xmax - maximum x-coordinate
        ymin - minimum y-coordinate
        ymax - maximum y-coordinate
    '''
    trimmed = dem[ymin:ymax, xmin:xmax] # slice array to defined extent

    display_dem(trimmed)

    return trimmed