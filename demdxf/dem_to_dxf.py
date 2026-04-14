import numpy as np
from skimage import measure
from shapely.geometry import Point, LineString, Polygon, GeometryCollection
from shapely.affinity import scale
from shapely.ops import split, unary_union
import ezdxf
import matplotlib.pyplot as plt
from demdxf.dem_preprocessing import display_dem


def _get_contour_levels(dem, contour_interval):
    '''
    Function for getting a list of contour levels.
        dem - DEM
        contour_interval - interval between contours in meters
    '''
    lowest_contour = np.ceil(dem.min() / contour_interval) * contour_interval
    highest_contour = np.ceil(dem.max() / contour_interval) * contour_interval
    levels = np.arange(lowest_contour, highest_contour, contour_interval)

    return levels


def _get_scaling_factor(dem, model_width):
    '''
    Function for scaling the DEM to model size.
        dem - DEM
        model_width - width of model in the longer direction in millimeters
    '''
    dem_width = max(dem.shape) * 1000  # width of DEM in mm
    scaling_factor = model_width / dem_width

    return scaling_factor


def _process_and_add_lines_to_msp(lines, msp, scaling_factor):
    '''
    Function for adding shapely lines to a DXF modelspace
        lines - contour lines
        msp - ezdxf modelspace
        scaling_factor - scaling_factor determined by the `get_scaling_factor` function
    '''
    for line in lines:
        dem_points = np.array(line.coords)  # convert shapely lines to numpy array
        model_points = dem_points * 1000 * scaling_factor  # scale point to model scale

        scaled_line = LineString(model_points)  # convert numpy array back to shapely lines

        try:
            polygon = Polygon(scaled_line.coords)  # create a polygon from the line
        except Exception:
            continue

        # check each polygon to make sure it is larger than 1 cm^2. Small polygons will not be added
        if polygon.area < 100:  # mm²
            continue

        msp.add_lwpolyline(model_points.tolist())  # add each polyline to the CAD drawing

        # plot the contour lines
        x, y = line.xy
        plt.plot(x, y, color='red')


def extend_line_to_bbox(line):
    """
    Extend a contour line slightly outward so it is more likely to intersect the bounding box.
    """
    # Scale the line around its centroid by a small factor (2% outward)
    return scale(line, xfact=1.02, yfact=1.02, origin='center')


def split_bbox_line_by_contours(bbox_line, contour_lines):
    """
    Split the bounding box *line* using the contour lines.
    Returns a list of LineString segments.
    """
    # Extend contours so they are more likely to intersect the bbox
    extended = [extend_line_to_bbox(line) for line in contour_lines]

    merged = unary_union(extended)
    result = split(bbox_line, merged)

    # Normalize output to a list of geometries
    if isinstance(result, GeometryCollection):
        geoms = list(result.geoms)
    else:
        geoms = [result]

    # Keep only LineStrings
    segments = [g for g in geoms if isinstance(g, LineString) and not g.is_empty]

    return segments


def create_dxf_drawings(dem, contour_interval, model_width, output_directory, simplify_tolerance=1):
    '''
    Function for converting DEMs to DXF drawings
        dem - DEM
        contour_interval - contour interval in meters
        model_width - width of model in the longer direction in millimeters
        output_directory - directory to save drawings in
        simplify_tolerance - measure of how simplified the contours should be, default 1
    '''
    contour_levels = _get_contour_levels(dem, contour_interval)
    scaling_factor = _get_scaling_factor(dem, model_width)

    # loop through each contour level
    for i, level in enumerate(contour_levels):
        contours = measure.find_contours(dem, level)  # use sci-kit image to find the edges of features
        lines = [LineString((c - 1)[:, ::-1]) for c in contours]  # convert contours into vector data

        simplified_lines = [line.simplify(simplify_tolerance) for line in lines]  # simplify geometry

        # add contours from the level above for stacking outline
        if i + 1 < len(contour_levels):
            next_contours = measure.find_contours(dem, contour_levels[i + 1])
            next_lines = [LineString((c - 1)[:, ::-1]) for c in next_contours]
            simplified_lines.extend([line.simplify(simplify_tolerance) for line in next_lines])

        # make sure lines exist before proceeding
        if not simplified_lines:
            continue

        # create a new CAD drawing file
        doc = ezdxf.new()
        doc.header['$INSUNITS'] = 3  # set drawing units to mm
        msp = doc.modelspace()

        # add contour lines to the drawing
        _process_and_add_lines_to_msp(simplified_lines, msp, scaling_factor)

        h, w = dem.shape

        # Create bounding box as a LineString in DEM coordinates
        bbox_line = LineString([
            (0, 0),
            (w - 1, 0),
            (w - 1, h - 1),
            (0, h - 1),
            (0, 0)
        ])

        msp.add_lwpolyline(list(bbox_line.coords))

        '''
        # Split bounding box line by contour lines
        bbox_segments = split_bbox_line_by_contours(bbox_line, simplified_lines)

        # Minimum segment length in model units (mm) to keep (e.g., 10 mm)
        MIN_SEGMENT_LENGTH_MM = 10.0

        # Add each bbox segment to DXF, filtering out tiny ones
        for seg in bbox_segments:
            if not isinstance(seg, LineString) or seg.is_empty:
                continue

            pts = np.array(seg.coords)
            pts_model = pts * 1000 * scaling_factor
            seg_model = LineString(pts_model)

            # filter out very short segments
            #if seg_model.length < MIN_SEGMENT_LENGTH_MM:
                #continue

            msp.add_lwpolyline(pts_model.tolist())
        '''

        if msp:  # only save CAD file if polylines were added
            output_path = f'{output_directory}/contours{int(level)}.dxf'
            doc.saveas(output_path)
            print(f'Drawing saved to {output_path}')

    # plot DEM and show plot
    display_dem(dem)