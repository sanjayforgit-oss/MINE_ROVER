import os
import math
import numpy as np
import matplotlib.pyplot as plt
import ezdxf
from ezdxf import units

def generate_bracket_files(
    top_length=120.0,       # Length of top flat section (mm)
    leg_length=110.0,       # Length of angled legs (mm)
    leg_angle_deg=45.0,     # Angle of legs sloped down from horizontal (deg)
    arm_width=35.0,         # Width of the plate arms (mm)
    slot_length=50.0,       # Length of the slot inside legs (mm)
    slot_width=16.0,        # Width of the slot inside legs (mm)
    l_clamp_hole_dia=4.2,   # Diameter of L-clamp mounting holes (M4 clearance = 4.2mm)
    l_clamp_hole_spacing=60.0 # Spacing between L-clamp holes on top bar (mm)
):
    rad = math.radians(leg_angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    
    Y_top = 0.0
    pt_top_L = np.array([-top_length/2.0, Y_top])
    pt_top_R = np.array([top_length/2.0, Y_top])
    
    pt_leg_R_outer = pt_top_R + leg_length * np.array([cos_a, -sin_a])
    pt_leg_R_inner = pt_leg_R_outer + arm_width * np.array([-sin_a, -cos_a])
    
    Y_inner_top = Y_top - arm_width
    t_R = (Y_inner_top - pt_leg_R_inner[1]) / sin_a
    pt_knee_R = pt_leg_R_inner + t_R * np.array([-cos_a, sin_a])
    
    pt_leg_L_outer = pt_top_L + leg_length * np.array([-cos_a, -sin_a])
    pt_leg_L_inner = pt_leg_L_outer + arm_width * np.array([sin_a, -cos_a])
    
    t_L = (Y_inner_top - pt_leg_L_inner[1]) / sin_a
    pt_knee_L = pt_leg_L_inner + t_L * np.array([cos_a, sin_a])
    
    outer_polygon = [
        pt_top_L,
        pt_top_R,
        pt_leg_R_outer,
        pt_leg_R_inner,
        pt_knee_R,
        pt_knee_L,
        pt_leg_L_inner,
        pt_leg_L_outer
    ]
    
    dist_slot_center = leg_length * 0.5
    c_R = pt_top_R + dist_slot_center * np.array([cos_a, -sin_a]) + (arm_width / 2.0) * np.array([-sin_a, -cos_a])
    c_L = pt_top_L + dist_slot_center * np.array([-cos_a, -sin_a]) + (arm_width / 2.0) * np.array([sin_a, -cos_a])
    
    def get_slot_corners(center, u_arm, n_perp, l_s, w_s):
        half_l = l_s / 2.0
        half_w = w_s / 2.0
        c1 = center - half_l * u_arm - half_w * n_perp
        c2 = center + half_l * u_arm - half_w * n_perp
        c3 = center + half_l * u_arm + half_w * n_perp
        c4 = center - half_l * u_arm + half_w * n_perp
        return [c1, c2, c3, c4]
        
    u_arm_R = np.array([cos_a, -sin_a])
    n_perp_R = np.array([-sin_a, -cos_a])
    right_slot = get_slot_corners(c_R, u_arm_R, n_perp_R, slot_length, slot_width)
    
    u_arm_L = np.array([-cos_a, -sin_a])
    n_perp_L = np.array([sin_a, -cos_a])
    left_slot = get_slot_corners(c_L, u_arm_L, n_perp_L, slot_length, slot_width)
    
    y_holes = Y_top - arm_width / 2.0
    hole_L = np.array([-l_clamp_hole_spacing / 2.0, y_holes])
    hole_R = np.array([l_clamp_hole_spacing / 2.0, y_holes])
    holes = [hole_L, hole_R]
    
    # -------------------------------------------------------------
    # 1. CREATE DXF FILE
    # -------------------------------------------------------------
    doc = ezdxf.new('R2000') # Standard R2000 DXF format
    doc.units = units.MM
    msp = doc.modelspace()
    
    # Add layers with distinct colors for Laser Cutters (RED = outer cut, BLUE = slot cut, GREEN = drill holes)
    doc.layers.add('OUTER_CUT', color=1)       # Color 1 = Red
    doc.layers.add('SLOT_CUTS', color=5)       # Color 5 = Blue
    doc.layers.add('MOUNTING_HOLES', color=3)  # Color 3 = Green
    
    # Add outer contour
    pts_outer_2d = [(p[0], p[1]) for p in outer_polygon]
    msp.add_lwpolyline(pts_outer_2d, close=True, dxfattribs={'layer': 'OUTER_CUT'})
    
    # Add left slot
    pts_left_slot_2d = [(p[0], p[1]) for p in left_slot]
    msp.add_lwpolyline(pts_left_slot_2d, close=True, dxfattribs={'layer': 'SLOT_CUTS'})
    
    # Add right slot
    pts_right_slot_2d = [(p[0], p[1]) for p in right_slot]
    msp.add_lwpolyline(pts_right_slot_2d, close=True, dxfattribs={'layer': 'SLOT_CUTS'})
    
    # Add L-clamp holes
    for h in holes:
        msp.add_circle((h[0], h[1]), radius=l_clamp_hole_dia / 2.0, dxfattribs={'layer': 'MOUNTING_HOLES'})
        
    dxf_filename = 'wheel_attachment_bracket.dxf'
    doc.saveas(dxf_filename)
    print(f"Saved DXF: {dxf_filename}")
    
    # -------------------------------------------------------------
    # 2. CREATE SVG FILE
    # -------------------------------------------------------------
    svg_filename = 'wheel_attachment_bracket.svg'
    
    # Compute bounding box
    all_x = [p[0] for p in outer_polygon]
    all_y = [p[1] for p in outer_polygon]
    min_x, max_x = min(all_x) - 10, max(all_x) + 10
    min_y, max_y = min(all_y) - 10, max(all_y) + 10
    width_svg = max_x - min_x
    height_svg = max_y - min_y
    
    def poly_to_svg_pts(poly):
        return " ".join([f"{p[0] - min_x:.3f},{max_y - p[1]:.3f}" for p in poly])
        
    svg_content = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="{width_svg}mm" height="{height_svg}mm" viewBox="0 0 {width_svg} {height_svg}" xmlns="http://www.w3.org/2000/svg">
    <g id="OUTER_CUT" stroke="#FF0000" stroke-width="0.5" fill="none">
        <polygon points="{poly_to_svg_pts(outer_polygon)}" />
    </g>
    <g id="SLOT_CUTS" stroke="#0000FF" stroke-width="0.5" fill="none">
        <polygon points="{poly_to_svg_pts(left_slot)}" />
        <polygon points="{poly_to_svg_pts(right_slot)}" />
    </g>
    <g id="MOUNTING_HOLES" stroke="#00AA00" stroke-width="0.5" fill="none">
'''
    for h in holes:
        cx_svg = h[0] - min_x
        cy_svg = max_y - h[1]
        r_svg = l_clamp_hole_dia / 2.0
        svg_content += f'        <circle cx="{cx_svg:.3f}" cy="{cy_svg:.3f}" r="{r_svg:.3f}" />\n'
    svg_content += '''    </g>
</svg>'''
    
    with open(svg_filename, 'w') as f:
        f.write(svg_content)
    print(f"Saved SVG: {svg_filename}")

    # -------------------------------------------------------------
    # 3. CREATE PNG VISUAL PREVIEW & SCHEMATIC
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(12, 7), dpi=300)
    fig.patch.set_facecolor('#0f172a') # Dark modern engineering background
    ax.set_facecolor('#1e293b')
    
    # Plot outer contour
    op_x = [p[0] for p in outer_polygon] + [outer_polygon[0][0]]
    op_y = [p[1] for p in outer_polygon] + [outer_polygon[0][1]]
    ax.plot(op_x, op_y, color='#38bdf8', linewidth=2.5, label='Outer Laser Cut Contour')
    ax.fill(op_x, op_y, color='#0284c7', alpha=0.15)
    
    # Plot left slot
    ls_x = [p[0] for p in left_slot] + [left_slot[0][0]]
    ls_y = [p[1] for p in left_slot] + [left_slot[0][1]]
    ax.plot(ls_x, ls_y, color='#f43f5e', linewidth=2.0, label='Leg Cutout Slots (Motor/Shaft Gap)')
    ax.fill(ls_x, ls_y, color='#1e293b')
    
    # Plot right slot
    rs_x = [p[0] for p in right_slot] + [right_slot[0][0]]
    rs_y = [p[1] for p in right_slot] + [right_slot[0][1]]
    ax.plot(rs_x, rs_y, color='#f43f5e', linewidth=2.0)
    ax.fill(rs_x, rs_y, color='#1e293b')
    
    # Plot holes
    first_h = True
    for h in holes:
        circle = plt.Circle((h[0], h[1]), l_clamp_hole_dia / 2.0, color='#10b981', fill=True, 
                            label='L-Clamp M4 Mounting Holes' if first_h else "")
        ax.add_patch(circle)
        first_h = False
        
    # Annotations & Dimension Callouts
    ax.annotate(f'Top Span: {top_length:.1f} mm', xy=(0, 5), xytext=(0, 15),
                ha='center', color='#f8fafc', fontsize=11, weight='bold',
                arrowprops=dict(arrowstyle='->', color='#38bdf8', lw=1.5))
                
    ax.annotate(f'Angled Leg: {leg_length:.1f} mm @ {leg_angle_deg:.0f}°', xy=(pt_leg_R_outer[0], pt_leg_R_outer[1]),
                xytext=(pt_leg_R_outer[0]+15, pt_leg_R_outer[1]+15),
                ha='left', color='#f8fafc', fontsize=10,
                arrowprops=dict(arrowstyle='->', color='#38bdf8', lw=1.5))
                
    ax.annotate(f'Slot: {slot_length:.0f} x {slot_width:.0f} mm', xy=(c_R[0], c_R[1]),
                xytext=(c_R[0]+20, c_R[1]-15),
                ha='left', color='#fb7185', fontsize=10, weight='bold',
                arrowprops=dict(arrowstyle='->', color='#f43f5e', lw=1.5))
                
    ax.annotate(f'L-Clamp Holes (M4, {l_clamp_hole_spacing:.0f}mm Pitch)', xy=(hole_L[0], hole_L[1]),
                xytext=(hole_L[0]-40, hole_L[1]+25),
                ha='right', color='#6ee7b7', fontsize=10, weight='bold',
                arrowprops=dict(arrowstyle='->', color='#10b981', lw=1.5))
                
    ax.annotate(f'Plate Width: {arm_width:.1f} mm', xy=((pt_top_L[0]+pt_knee_L[0])/2, Y_inner_top),
                xytext=(0, Y_inner_top - 20),
                ha='center', color='#cbd5e1', fontsize=10,
                arrowprops=dict(arrowstyle='->', color='#cbd5e1', lw=1.2))

    ax.set_aspect('equal', 'box')
    ax.grid(True, linestyle='--', alpha=0.3, color='#475569')
    ax.set_title('Wheel Attachment Side Bracket - Laser Cut Profile (1:1 Scale CAD Model)', color='#f8fafc', fontsize=14, pad=15, weight='bold')
    ax.set_xlabel('X Dimension (mm)', color='#94a3b8', fontsize=11)
    ax.set_ylabel('Y Dimension (mm)', color='#94a3b8', fontsize=11)
    ax.tick_params(colors='#94a3b8')
    ax.legend(facecolor='#1e293b', edgecolor='#475569', labelcolor='#f8fafc', loc='upper right')
    
    png_filename = 'wheel_attachment_bracket_preview.png'
    plt.tight_layout()
    plt.savefig(png_filename, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"Saved PNG Preview: {png_filename}")

if __name__ == '__main__':
    generate_bracket_files()
