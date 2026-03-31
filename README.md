# demdxf
Open-source Python package for converting DEMs to CAD drawings (DXF) and related opeartions.

## demdxf.dem_preprocessing Functions
### `load_dem`
Loads a DEM from a file path using `rasterio`. Assumes the raster only has one band. If the raster has more than one band, it reads the first band.

Usage:

`load_dem(path)`

- `path`: file path

### `trim_dem`
Trims a DEM to a desired extent, using cell indices.

Usage:

`trim_dem(dem, xmin, xmax, ymin, ymax)`

- `dem`: DEM
- `xmin`: minimum x-coordinate
- `xmax`: maximum x-coordinate
- `ymin`: mininmum y-coordinate
- `ymax`: maximum y-coordinate

### `display_dem`
Plots the DEM using `matplotlib`.

Usage:

`display_dem(dem)`

- `dem`: DEM

## demdxf.dem_to_dxf Functions
### `create_dxf_drawings`
Converts a DEM to DXF drawings

Usage:

`create_dxf_drawings(dem, contour_interval, model_width, output_directory, [simplify_tolerance])`

- `dem`: DEM
- `contour_interval`: Desired contour interval in map units. Scaling does not currently work for map units other than meters.
- `model_width`: Width of the model in millimeters.
- `output_directory`: Directory to save DXF drawings for each contour interval in
- `simplify_tolerance`: Degree of simplification of contour geometry. Defaults to 1.

## demdxf.laz_to_tif Functions
### `laz_to_tif`
Converts a point cloud (LAZ) file to a DEM (TIF).

Usage:

`laz_to_tif(laz_file, output_path, [laz_crs])`

- `laz_file`: file path to LAZ file
- `output_path`: output file path. Must include ".tif"
- `laz_crs`: CRS of the LAZ file. This parameter is only necessary if the LAZ file does not already have a CRS. An error message will appear if a CRS cannot be found.