import os
import math
import numpy as np
import ezdxf
from ezdxf import units

def generate_stealth_octagon_dxf():
    wheel_mount_len = 182.9 # Matches 42cm wheel bracket top span
    
    L_a, W_a = 550.0, 400.0 # 55 cm length x 40 cm width
    hL, hW = L_a / 2.0, W_a / 2.0
    half_side = wheel_mount_len / 2.0
    chamfer = 70.0
    
    # Vertices of Tactical Stealth Octagon
    v_a = [
        (-hW, -half_side),
        (-hW, +half_side),
        (-hW + chamfer, +hL - 40.0),
        (-40.0, +hL),           # Front notch left
        (+40.0, +hL),           # Front notch right
        (+hW - chamfer, +hL - 40.0),
        (+hW, +half_side),
        (+hW, -half_side),
        (+hW - chamfer, -hL + 40.0),
        (+40.0, -hL),           # Rear bumper right
        (-40.0, -hL),           # Rear bumper left
        (-hW + chamfer, -hL + 40.0),
    ]
    
    # L-Clamp Mounting Holes
    l_hole_offset = 15.0
    l_hole_pitch = 91.5 # Matches scaled wheel bracket hole spacing
    hole_dia = 4.2
    
    hole_L1 = (-hW + l_hole_offset, -l_hole_pitch / 2.0)
    hole_L2 = (-hW + l_hole_offset, +l_hole_pitch / 2.0)
    hole_R1 = (+hW - l_hole_offset, -l_hole_pitch / 2.0)
    hole_R2 = (+hW - l_hole_offset, +l_hole_pitch / 2.0)
    holes = [hole_L1, hole_L2, hole_R1, hole_R2]
    
    # Export DXF
    doc = ezdxf.new('R2000')
    doc.units = units.MM
    msp = doc.modelspace()
    doc.layers.add('OUTER_CUT', color=1)
    doc.layers.add('MOUNTING_HOLES', color=3)
    
    msp.add_lwpolyline(v_a, close=True, dxfattribs={'layer': 'OUTER_CUT'})
    for h in holes:
        msp.add_circle(h, radius=hole_dia / 2.0, dxfattribs={'layer': 'MOUNTING_HOLES'})
        
    dxf_filename = 'rover_base_stealth_octagon.dxf'
    doc.saveas(dxf_filename)
    print(f"Saved DXF: {dxf_filename}")
    
    # Export SVG
    svg_filename = 'rover_base_stealth_octagon.svg'
    min_x, max_x = -hW - 10, hW + 10
    min_y, max_y = -hL - 10, hL + 10
    width_svg = max_x - min_x
    height_svg = max_y - min_y
    def poly_to_svg_pts(poly):
        return " ".join([f"{p[0] - min_x:.3f},{max_y - p[1]:.3f}" for p in poly])
        
    svg_content = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="{width_svg}mm" height="{height_svg}mm" viewBox="0 0 {width_svg} {height_svg}" xmlns="http://www.w3.org/2000/svg">
    <g id="OUTER_CUT" stroke="#FF0000" stroke-width="0.5" fill="none">
        <polygon points="{poly_to_svg_pts(v_a)}" />
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
    generate_stealth_octagon_dxf()
