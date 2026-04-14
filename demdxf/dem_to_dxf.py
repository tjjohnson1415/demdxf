import numpy as np
from skimage import measure
from shapely.geometry import Point, LineString, Polygon, MultiPolygon, GeometryCollection
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
    dem_width = max(dem.shape) * 1000 # width of DEM in mm
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
        dem_points = np.array(line.coords) #convert shapely lines to numpy array
        model_points = dem_points * 1000 * scaling_factor #scale point to model scale
        
        scaled_line = LineString(model_points) #convert numpy array back to shapely lines
        
        try:
            polygon = Polygon(scaled_line.coords) #create a polygon from the line
        except:
            continue
        
        #check each polygon to make sure it is larger than 1 cm^2. Small polygons will not be added to the drawing
        if polygon.area < 100:
            continue
        
        msp.add_lwpolyline(model_points.tolist()) #add each polyline to the CAD drawing point by point

        #plot the contour lines
        x, y = line.xy
        plt.plot(x, y, color = 'red')
        

def extend_line_to_bbox(line, bbox):
    """
    Extend a contour line slightly outward so it intersects the bounding box.
    """
    # Scale the line around its centroid by a small factor
    # 1.02 = extend by 2%
    return scale(line, xfact=1.02, yfact=1.02, origin='center')
    
    
def split_bbox_by_contours(bbox_polygon, contour_lines):
    # Extend contours so they actually intersect the bounding box
    extended = [extend_line_to_bbox(line, bbox_polygon) for line in contour_lines]

    merged = unary_union(extended)
    result = split(bbox_polygon, merged)

    # Normalize output
    if isinstance(result, GeometryCollection):
        return list(result.geoms)
    else:
        return [result]


def create_dxf_drawings(dem, contour_interval, model_width, output_directory, simplify_tolerance = 1):
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
    
    #loop through each contour level
    for i, level in enumerate(contour_levels):
        contours = measure.find_contours(dem, level) #use sci-kit image to find the edges of features
        lines = [LineString((c - 1)[:, ::-1]) for c in contours] #convert contours into vector data. Trim off padded edges
    
        simplified_lines = [line.simplify(simplify_tolerance) for line in lines] #simplify geometry
        
        #add contours from the level above for stacking outline
        if i + 1 < len(contour_levels):
            next_contours = measure.find_contours(dem, contour_levels[i + 1]) #find edges of next level features
            next_lines = [LineString((c - 1)[:, ::-1]) for c in next_contours] #convert contours into vector data and trim off edges
            simplified_lines.extend([line.simplify(simplify_tolerance) for line in next_lines]) #simplify geometry
        
        #make sure lines exist before proceeding.
        if not simplified_lines:
            continue
        
        #create a new CAD drawing file. This file should be readable by CNC machines
        doc = ezdxf.new()
        doc.header['$INSUNITS'] = 3 #set drawing units to mm
        msp = doc.modelspace()
        
        #add lines to the drawing
        _process_and_add_lines_to_msp(simplified_lines, msp, scaling_factor)
        
        h, w = dem.shape
        '''
        bbox_dem_points = np.array([
            [0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1], [0, 0]
        ])
        bbox_model_points = bbox_dem_points * 1000 * scaling_factor
        msp.add_lwpolyline(bbox_model_points.tolist())
        '''

        # Create bounding box polygon in DEM coordinates
        bbox_poly = Polygon([
            (0, 0), (w - 1, 0), (w - 1, h - 1), (0, h - 1)
        ])
        
        # Split bounding box by contour lines
        bbox_pieces = split_bbox_by_contours(bbox_poly, simplified_lines)

        for piece in bbox_pieces:
            # If the piece is a MultiPolygon, iterate through its parts
            if isinstance(piece, MultiPolygon):
                polys = list(piece.geoms)
            else:
                polys = [piece]
        
            for poly in polys:
                # Skip empty or invalid geometries
                if not isinstance(poly, Polygon):
                    continue
                if poly.is_empty:
                    continue
        
                pts = np.array(poly.exterior.coords)
                pts_model = pts * 1000 * scaling_factor
                msp.add_lwpolyline(pts_model.tolist(), close=True)
            
        if msp: #only save CAD file if polylines were added
            output_path = f'{output_directory}/contours{int(level)}.dxf'
            doc.saveas(output_path)
            print(f'Drawing saved to {output_path}')
            pass
            
    #plot DEM and show plot
    display_dem(dem)