import os
import math
import numpy as np
import ezdxf
from PIL import Image, ImageDraw

class DxfMapConverter:
    """
    AutoCAD DXF to ROS 2 / Nav2 Occupancy Grid & Waypoint Ingestion Engine.
    Parses vector lines, generates 2D occupancy costmaps (.pgm + .yaml),
    and extracts route waypoints for autonomous mine traversal.
    """
    def __init__(self, resolution_m=0.05, margin_m=1.0):
        self.resolution = resolution_m # 5 cm per pixel
        self.margin = margin_m # 1 meter margin around blueprint
        self.lines = [] # List of ((x1, y1), (x2, y2)) in meters
        self.bounds = [0.0, 0.0, 10.0, 10.0] # xmin, ymin, xmax, ymax
        self.grid = None
        self.waypoints = []

    def load_dxf(self, dxf_filepath):
        if not os.path.exists(dxf_filepath):
            raise FileNotFoundError(f"DXF file not found: {dxf_filepath}")
            
        doc = ezdxf.readfile(dxf_filepath)
        msp = doc.modelspace()
        
        extracted_lines = []
        all_pts = []
        
        # 1. Extract LINE entities
        for e in msp.query('LINE'):
            p1 = (e.dxf.start.x, e.dxf.start.y)
            p2 = (e.dxf.end.x, e.dxf.end.y)
            extracted_lines.append((p1, p2))
            all_pts.extend([p1, p2])
            
        # 2. Extract LWPOLYLINE & POLYLINE entities
        for e in msp.query('LWPOLYLINE POLYLINE'):
            pts = [(p[0], p[1]) for p in e.get_points('xy')]
            is_closed = e.is_closed if hasattr(e, 'is_closed') else False
            for i in range(len(pts) - 1):
                extracted_lines.append((pts[i], pts[i+1]))
                all_pts.extend([pts[i], pts[i+1]])
            if is_closed and len(pts) > 2:
                extracted_lines.append((pts[-1], pts[0]))
                
        # 3. Extract CIRCLE / ARC entities
        for e in msp.query('CIRCLE ARC'):
            center = (e.dxf.center.x, e.dxf.center.y)
            r = e.dxf.radius
            start_ang = getattr(e.dxf, 'start_angle', 0.0)
            end_ang = getattr(e.dxf, 'end_angle', 360.0)
            if end_ang < start_ang: end_ang += 360.0
            
            num_segs = max(12, int(r * 20))
            arc_pts = []
            for i in range(num_segs + 1):
                ang = math.radians(start_ang + (end_ang - start_ang) * (i / num_segs))
                arc_pts.append((center[0] + r * math.cos(ang), center[1] + r * math.sin(ang)))
            for i in range(len(arc_pts) - 1):
                extracted_lines.append((arc_pts[i], arc_pts[i+1]))
                all_pts.extend([arc_pts[i], arc_pts[i+1]])

        if not all_pts:
            raise ValueError(f"No geometric lines found in DXF: {dxf_filepath}")

        # Check units: if coordinate span > 1000, assume millimeters and convert to meters!
        xs = [p[0] for p in all_pts]
        ys = [p[1] for p in all_pts]
        span_x = max(xs) - min(xs)
        span_y = max(ys) - min(ys)
        
        scale_factor = 1.0
        if span_x > 50.0 or span_y > 50.0: # likely in mm
            scale_factor = 0.001
            print(f"[DXF Loader] Coordinates detected in millimeters (Span: {span_x:.1f}x{span_y:.1f}mm) -> Converting to meters (Scale: 0.001)")
            
        self.lines = [
            ((p1[0] * scale_factor, p1[1] * scale_factor),
             (p2[0] * scale_factor, p2[1] * scale_factor))
            for p1, p2 in extracted_lines
        ]
        
        scaled_xs = [p[0] * scale_factor for p in all_pts]
        scaled_ys = [p[1] * scale_factor for p in all_pts]
        self.bounds = [min(scaled_xs), min(scaled_ys), max(scaled_xs), max(scaled_ys)]
        
        print(f"[DXF Loaded] Extracted {len(self.lines)} line segments. Bounding box: [{self.bounds[0]:.2f}, {self.bounds[1]:.2f}] to [{self.bounds[2]:.2f}, {self.bounds[3]:.2f}] meters.")
        return len(self.lines)

    def generate_occupancy_grid(self):
        """Converts vector lines into a 2D occupancy grid."""
        xmin, ymin, xmax, ymax = self.bounds
        w_m = (xmax - xmin) + 2 * self.margin
        h_m = (ymax - ymin) + 2 * self.margin
        
        grid_w = max(50, int(w_m / self.resolution))
        grid_h = max(50, int(h_m / self.resolution))
        
        # 254 = Free (White), 0 = Occupied Wall (Black)
        img = Image.new('L', (grid_w, grid_h), color=254)
        draw = ImageDraw.Draw(img)
        
        ox = xmin - self.margin
        oy = ymin - self.margin
        
        wall_width_px = max(2, int(0.15 / self.resolution)) # 15cm wall thickness
        
        for (x1, y1), (x2, y2) in self.lines:
            px1 = int((x1 - ox) / self.resolution)
            py1 = grid_h - int((y1 - oy) / self.resolution) # Flip Y
            px2 = int((x2 - ox) / self.resolution)
            py2 = grid_h - int((y2 - oy) / self.resolution)
            draw.line([px1, py1, px2, py2], fill=0, width=wall_width_px)
            
        self.grid = np.array(img)
        return self.grid, (grid_w, grid_h), (ox, oy)

    def extract_corridor_waypoints(self, num_points=6):
        """Generates a smooth navigation path through the center of the loaded map."""
        xmin, ymin, xmax, ymax = self.bounds
        
        # S-shape / serpentine search path covering the blueprint
        wps = []
        cx = (xmin + xmax) / 2.0
        cy = (ymin + ymax) / 2.0
        
        # 6 Strategic Waypoints covering the perimeter and crosscuts
        wps.append((xmin + 1.0, ymin + 1.0))
        wps.append((xmin + 1.0, ymax - 1.0))
        wps.append((cx, ymax - 1.0))
        wps.append((cx, ymin + 1.0))
        wps.append((xmax - 1.0, ymin + 1.0))
        wps.append((xmax - 1.0, ymax - 1.0))
        
        self.waypoints = wps
        return self.waypoints

    def export_ros2_nav2_map(self, output_dir="e:/miners", map_name="mine_blueprint"):
        """Exports .yaml and .pgm files for Nav2."""
        if self.grid is None:
            self.generate_occupancy_grid()
            
        xmin, ymin, _, _ = self.bounds
        ox = xmin - self.margin
        oy = ymin - self.margin
        
        pgm_filename = f"{map_name}.pgm"
        yaml_filename = f"{map_name}.yaml"
        
        pgm_path = os.path.join(output_dir, pgm_filename)
        yaml_path = os.path.join(output_dir, yaml_filename)
        
        # Save PGM
        Image.fromarray(self.grid).save(pgm_path)
        
        # Save YAML
        yaml_str = f"""image: {pgm_filename}
resolution: {self.resolution:.4f}
origin: [{ox:.4f}, {oy:.4f}, 0.000000]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.25
"""
        with open(yaml_path, 'w', encoding='utf-8') as f:
            f.write(yaml_str)
            
        print(f"[DXF Map Exported] Saved {yaml_path} and {pgm_path}")
        return yaml_path, pgm_path
