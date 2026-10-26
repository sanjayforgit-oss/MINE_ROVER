import os
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import ezdxf
from ezdxf import units

def update_wheel_attachment_42cm():
    # Original tip-to-tip span was 120 + 2*(110*cos(45)) = 275.5635 mm
    orig_span = 120.0 + 2.0 * (110.0 * math.cos(math.radians(45)))
    target_span = 420.0 # 42 cm
    scale = target_span / orig_span
    
    top_length = 120.0 * scale       # ~182.9 mm
    leg_length = 110.0 * scale       # ~167.7 mm
    leg_angle_deg = 45.0
    arm_width = 35.0 * scale         # ~53.3 mm
    slot_length = 50.0 * scale       # ~76.2 mm
    slot_width = 16.0 * scale        # ~24.4 mm
    l_clamp_hole_dia = 4.2           # Keep M4 bolt size standard
    l_clamp_hole_spacing = 60.0 * scale # ~91.5 mm
    
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
    
    # Export DXF
    doc = ezdxf.new('R2000')
    doc.units = units.MM
    msp = doc.modelspace()
    doc.layers.add('OUTER_CUT', color=1)
    doc.layers.add('SLOT_CUTS', color=5)
    doc.layers.add('MOUNTING_HOLES', color=3)
    
    msp.add_lwpolyline([(p[0], p[1]) for p in outer_polygon], close=True, dxfattribs={'layer': 'OUTER_CUT'})
    msp.add_lwpolyline([(p[0], p[1]) for p in left_slot], close=True, dxfattribs={'layer': 'SLOT_CUTS'})
    msp.add_lwpolyline([(p[0], p[1]) for p in right_slot], close=True, dxfattribs={'layer': 'SLOT_CUTS'})
    for h in holes:
        msp.add_circle((h[0], h[1]), radius=l_clamp_hole_dia / 2.0, dxfattribs={'layer': 'MOUNTING_HOLES'})
        
    doc.saveas('wheel_attachment_bracket.dxf')
    print("Updated wheel_attachment_bracket.dxf to 42 cm total span.")

    # Export SVG
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
    with open('wheel_attachment_bracket.svg', 'w') as f:
        f.write(svg_content)

    # Plot PNG Preview
    fig, ax = plt.subplots(figsize=(12, 7), dpi=300)
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#1e293b')
    
    op_x = [p[0] for p in outer_polygon] + [outer_polygon[0][0]]
    op_y = [p[1] for p in outer_polygon] + [outer_polygon[0][1]]
    ax.plot(op_x, op_y, color='#38bdf8', linewidth=2.5, label='Outer Laser Cut Contour')
    ax.fill(op_x, op_y, color='#0284c7', alpha=0.15)
    
    ls_x = [p[0] for p in left_slot] + [left_slot[0][0]]
    ls_y = [p[1] for p in left_slot] + [left_slot[0][1]]
    ax.plot(ls_x, ls_y, color='#f43f5e', linewidth=2.0, label='Leg Cutout Slots')
    ax.fill(ls_x, ls_y, color='#1e293b')
    
    rs_x = [p[0] for p in right_slot] + [right_slot[0][0]]
    rs_y = [p[1] for p in right_slot] + [right_slot[0][1]]
    ax.plot(rs_x, rs_y, color='#f43f5e', linewidth=2.0)
    ax.fill(rs_x, rs_y, color='#1e293b')
    
    first_h = True
    for h in holes:
        circle = plt.Circle((h[0], h[1]), l_clamp_hole_dia / 2.0, color='#10b981', fill=True, 
                            label='L-Clamp M4 Mounting Holes' if first_h else "")
        ax.add_patch(circle)
        first_h = False
        
    ax.annotate(f'Total Span: {target_span/10.0:.1f} cm ({target_span:.1f} mm)', xy=(0, Y_top), xytext=(0, 25),
                ha='center', color='#fbbf24', fontsize=12, weight='bold',
                arrowprops=dict(arrowstyle='->', color='#fbbf24', lw=1.8))

    ax.annotate(f'Top Span: {top_length/10.0:.1f} cm ({top_length:.1f} mm)', xy=(0, Y_top-10), xytext=(0, -arm_width/2.0),
                ha='center', color='#38bdf8', fontsize=11, weight='bold')

    ax.set_aspect('equal', 'box')
    ax.grid(True, linestyle='--', alpha=0.3, color='#475569')
    ax.set_title(f'Wheel Attachment Bracket - Scaled to 42 cm Total Length (1:1 CAD Model)', color='#f8fafc', fontsize=13, pad=15, weight='bold')
    ax.set_xlabel('X Dimension (mm)', color='#94a3b8', fontsize=11)
    ax.set_ylabel('Y Dimension (mm)', color='#94a3b8', fontsize=11)
    ax.tick_params(colors='#94a3b8')
    ax.legend(facecolor='#1e293b', edgecolor='#475569', labelcolor='#f8fafc', loc='upper right')
    
    plt.tight_layout()
    plt.savefig('wheel_attachment_bracket_preview.png', dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()

    return top_length, leg_length, arm_width, l_clamp_hole_spacing

def update_rover_base_42cm(top_length_wheel):
    # Total length of base = 60 cm (600 mm) or scaled proportionally to accommodate 42cm wheel span cleanly
    # Width of base = 53.3 cm (533 mm) or 400 mm
    total_length_base = 600.0 # 60 cm long front-to-back
    total_width_base = 450.0  # 45 cm total width
    side_flat_len = top_length_wheel # Exactly matches wheel bracket top span (182.9 mm = 18.3 cm)
    
    half_L = total_length_base / 2.0
    half_W = total_width_base / 2.0
    half_flat = side_flat_len / 2.0
    
    p1 = (-half_W, -half_flat)
    p2 = (-half_W, +half_flat)
    p3 = (0.0, +half_L)
    p4 = (+half_W, +half_flat)
    p5 = (+half_W, -half_flat)
    p6 = (0.0, -half_L)
    
    hexagon_polygon = [p1, p2, p3, p4, p5, p6]
    
    l_hole_offset = 20.0
    l_hole_pitch = 91.5 # Matches scaled wheel bracket hole spacing
    hole_dia = 4.2
    
    hole_L1 = (-half_W + l_hole_offset, -l_hole_pitch / 2.0)
    hole_L2 = (-half_W + l_hole_offset, +l_hole_pitch / 2.0)
    hole_R1 = (+half_W - l_hole_offset, -l_hole_pitch / 2.0)
    hole_R2 = (+half_W - l_hole_offset, +l_hole_pitch / 2.0)
    holes = [hole_L1, hole_L2, hole_R1, hole_R2]
    
    # Export DXF
    doc = ezdxf.new('R2000')
    doc.units = units.MM
    msp = doc.modelspace()
    doc.layers.add('OUTER_CUT', color=1)
    doc.layers.add('MOUNTING_HOLES', color=3)
    msp.add_lwpolyline(hexagon_polygon, close=True, dxfattribs={'layer': 'OUTER_CUT'})
    for h in holes:
        msp.add_circle(h, radius=hole_dia / 2.0, dxfattribs={'layer': 'MOUNTING_HOLES'})
    doc.saveas('rover_base_hexagon.dxf')
    print("Updated rover_base_hexagon.dxf to 42 cm wheel match.")

    # Export SVG
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
    with open('rover_base_hexagon.svg', 'w') as f:
        f.write(svg_content)

    # Plot Preview
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 9), dpi=300)
    fig.patch.set_facecolor('#0f172a')
    
    # Subplot 1
    ax1.set_facecolor('#1e293b')
    hx = [p[0] for p in hexagon_polygon] + [hexagon_polygon[0][0]]
    hy = [p[1] for p in hexagon_polygon] + [hexagon_polygon[0][1]]
    ax1.plot(hx, hy, color='#38bdf8', linewidth=3.0, label='Hexagonal Base Cutout')
    ax1.fill(hx, hy, color='#0284c7', alpha=0.15)
    
    ax1.plot([-half_W, -half_W], [-half_flat, half_flat], color='#f43f5e', linewidth=4.0, label=f'Flat Side ({side_flat_len/10:.1f}cm - Wheel Match)')
    ax1.plot([half_W, half_W], [-half_flat, half_flat], color='#f43f5e', linewidth=4.0)
    
    for h in holes:
        circle = plt.Circle((h[0], h[1]), 2.1, color='#10b981', fill=True)
        ax1.add_patch(circle)
        
    ax1.annotate('', xy=(0, -half_L), xytext=(0, half_L),
                 arrowprops=dict(arrowstyle='<->', color='#fbbf24', lw=1.8))
    ax1.text(10, 0, f'Total Length: {total_length_base/10:.0f} cm ({total_length_base:.0f} mm)', color='#fbbf24', fontsize=11, weight='bold', rotation=90, va='center')
    
    ax1.set_aspect('equal', 'box')
    ax1.grid(True, linestyle='--', alpha=0.3, color='#475569')
    ax1.set_title('1. Hexagonal Base DXF Geometry', color='#f8fafc', fontsize=13, pad=12, weight='bold')
    ax1.set_xlabel('X Dimension (mm)', color='#94a3b8', fontsize=10)
    ax1.set_ylabel('Y Dimension (mm)', color='#94a3b8', fontsize=10)
    ax1.tick_params(colors='#94a3b8')
    ax1.legend(facecolor='#1e293b', edgecolor='#475569', labelcolor='#f8fafc', loc='upper right', fontsize=9)

    # Subplot 2
    ax2.set_facecolor('#1e293b')
    ax2.plot(hx, hy, color='#38bdf8', linewidth=2.0, linestyle='--', label='Hexagonal Base Plate')
    ax2.fill(hx, hy, color='#0284c7', alpha=0.10)
    
    # 42cm Wheel Brackets on Left & Right
    leg_dx = 167.7 * math.cos(math.radians(45))
    ax2.plot([-half_W, -half_W], [-half_flat, half_flat], color='#f43f5e', linewidth=5.0, label='Scaled Wheel Brackets (42 cm Span)')
    ax2.plot([-half_W, -half_W - leg_dx], [half_flat, half_flat + leg_dx], color='#f43f5e', linewidth=3.5)
    ax2.plot([-half_W, -half_W - leg_dx], [-half_flat, -half_flat - leg_dx], color='#f43f5e', linewidth=3.5)
    
    ax2.plot([half_W, half_W], [-half_flat, half_flat], color='#f43f5e', linewidth=5.0)
    ax2.plot([half_W, half_W + leg_dx], [half_flat, half_flat + leg_dx], color='#f43f5e', linewidth=3.5)
    ax2.plot([half_W, half_W + leg_dx], [-half_flat, -half_flat - leg_dx], color='#f43f5e', linewidth=3.5)
    
    wheel_w = 45.0
    wheel_d = 100.0
    wheel_centers = [
        (-half_W - leg_dx, half_flat + leg_dx),
        (-half_W - leg_dx, -half_flat - leg_dx),
        (half_W + leg_dx, half_flat + leg_dx),
        (half_W + leg_dx, -half_flat - leg_dx),
    ]
    
    for (cx, cy) in wheel_centers:
        rect = patches.Rectangle((cx - wheel_w/2.0, cy - wheel_d/2.0), wheel_w, wheel_d,
                                 linewidth=1.5, edgecolor='#eab308', facecolor='#ca8a04', alpha=0.8)
        ax2.add_patch(rect)
        
    ax2.set_aspect('equal', 'box')
    ax2.grid(True, linestyle='--', alpha=0.3, color='#475569')
    ax2.set_title('2. Rover Assembly with 42 cm Wheel Attachment', color='#f8fafc', fontsize=13, pad=12, weight='bold')
    ax2.set_xlabel('X Dimension (mm)', color='#94a3b8', fontsize=10)
    ax2.set_ylabel('Y Dimension (mm)', color='#94a3b8', fontsize=10)
    ax2.tick_params(colors='#94a3b8')
    ax2.legend(facecolor='#1e293b', edgecolor='#475569', labelcolor='#f8fafc', loc='upper right', fontsize=9)
    
    plt.suptitle('M.I.N.E.R.S. Rover Design - Scaled to 42 cm Wheel Length', color='#f8fafc', fontsize=15, weight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig('rover_base_preview.png', dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()

if __name__ == '__main__':
    top_len, leg_len, arm_w, pitch = update_wheel_attachment_42cm()
    update_rover_base_42cm(top_len)
