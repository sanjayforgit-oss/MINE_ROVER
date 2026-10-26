import os
import math
import numpy as np
import ezdxf
from ezdxf import units

def generate_base_dxf(
    total_length=400.0,      # 40 cm (Y axis, Front to Back)
    total_width=350.0,       # 35 cm (X axis, Left to Right)
    side_flat_len=120.0,     # 12 cm (Left & Right flat edge length, matching wheel bracket top)
    l_hole_offset=15.0,      # Inward offset for L-clamp mounting holes (mm)
    l_hole_pitch=60.0,       # Distance between L-clamp holes (mm)
    hole_dia=4.2             # M4 clearance hole diameter (mm)
):
    half_L = total_length / 2.0
    half_W = total_width / 2.0
    half_flat = side_flat_len / 2.0
    
    # 6 Hexagon Vertices
    p1 = (-half_W, -half_flat)  # Left-Bottom
    p2 = (-half_W, +half_flat)  # Left-Top
    p3 = (0.0, +half_L)         # Front Apex
    p4 = (+half_W, +half_flat)  # Right-Top
    p5 = (+half_W, -half_flat)  # Right-Bottom
    p6 = (0.0, -half_L)         # Back Apex
    
    hexagon_polygon = [p1, p2, p3, p4, p5, p6]
    
    # L-clamp mounting holes
    # Left side holes
    hole_L1 = (-half_W + l_hole_offset, -l_hole_pitch / 2.0)
    hole_L2 = (-half_W + l_hole_offset, +l_hole_pitch / 2.0)
    
    # Right side holes
    hole_R1 = (+half_W - l_hole_offset, -l_hole_pitch / 2.0)
    hole_R2 = (+half_W - l_hole_offset, +l_hole_pitch / 2.0)
    
    holes = [hole_L1, hole_L2, hole_R1, hole_R2]
    
    # -------------------------------------------------------------
    # 1. CREATE DXF FILE
    # -------------------------------------------------------------
    doc = ezdxf.new('R2000')
    doc.units = units.MM
    msp = doc.modelspace()
    
    doc.layers.add('OUTER_CUT', color=1)       # RED = Outer boundary
    doc.layers.add('MOUNTING_HOLES', color=3)  # GREEN = Drill holes
    
    # Add hexagon boundary
    msp.add_lwpolyline(hexagon_polygon, close=True, dxfattribs={'layer': 'OUTER_CUT'})
    
    # Add mounting holes
    for h in holes:
        msp.add_circle(h, radius=hole_dia / 2.0, dxfattribs={'layer': 'MOUNTING_HOLES'})
        
    dxf_filename = 'rover_base_hexagon.dxf'
    doc.saveas(dxf_filename)
    print(f"Saved DXF: {dxf_filename}")
    
    # -------------------------------------------------------------
    # 2. CREATE SVG FILE
    # -------------------------------------------------------------
    svg_filename = 'rover_base_hexagon.svg'
    min_x, max_x = -half_W - 10, half_W + 10
    min_y, max_y = -half_L - 10, half_L + 10
    width_svg = max_x - min_x
    height_svg = max_y - min_y
    
    def poly_to_svg_pts(poly):
        return " ".join([f"{p[0] - min_x:.3f},{max_y - p[1]:.3f}" for p in poly])
        
    svg_content = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="{width_svg}mm" height="{height_svg}mm" viewBox="0 0 {width_svg} {height_svg}" xmlns="http://www.w3.org/2000/svg">
    <g id="OUTER_CUT" stroke="#FF0000" stroke-width="0.5" fill="none">
        <polygon points="{poly_to_svg_pts(hexagon_polygon)}" />
    </g>
    <g id="MOUNTING_HOLES" stroke="#00AA00" stroke-width="0.5" fill="none">
'''
    for h in holes:
        cx_svg = h[0] - min_x
        cy_svg = max_y - h[1]
        r_svg = hole_dia / 2.0
        svg_content += f'        <circle cx="{cx_svg:.3f}" cy="{cy_svg:.3f}" r="{r_svg:.3f}" />\n'
    svg_content += '''    </g>
</svg>'''
    
    with open(svg_filename, 'w') as f:
        f.write(svg_content)
    print(f"Saved SVG: {svg_filename}")

if __name__ == '__main__':
    generate_base_dxf()
