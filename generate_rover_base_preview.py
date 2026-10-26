import os
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def generate_base_preview():
    # Dimensions in mm
    total_length = 400.0  # 40 cm
    total_width = 350.0   # 35 cm
    side_flat_len = 120.0 # 12 cm (matches wheel bracket top length)
    
    half_L = total_length / 2.0
    half_W = total_width / 2.0
    half_flat = side_flat_len / 2.0
    
    # 6 Hexagon Vertices
    # P1: Left-Bottom (-175, -60)
    # P2: Left-Top (-175, +60)
    # P3: Front Apex (0, +200)
    # P4: Right-Top (+175, +60)
    # P5: Right-Bottom (+175, -60)
    # P6: Back Apex (0, -200)
    
    p1 = np.array([-half_W, -half_flat])
    p2 = np.array([-half_W, +half_flat])
    p3 = np.array([0.0, +half_L])
    p4 = np.array([+half_W, +half_flat])
    p5 = np.array([+half_W, -half_flat])
    p6 = np.array([0.0, -half_L])
    
    hex_verts = [p1, p2, p3, p4, p5, p6, p1]
    hx = [p[0] for p in hex_verts]
    hy = [p[1] for p in hex_verts]
    
    # Setup Figure with 2 subplots: 
    # Subplot 1: Chassis Base Plate Dimensions & L-Clamp Mounting Holes
    # Subplot 2: Full Rover Assembly Top-Down Layout (Base + 4 Wheel Brackets + Motors & Wheels)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 9), dpi=300)
    fig.patch.set_facecolor('#0f172a') # Dark slate background
    
    # -----------------------------------------------------------------
    # SUBPLOT 1: Base Plate Design & Key Dimensions
    # -----------------------------------------------------------------
    ax1.set_facecolor('#1e293b')
    ax1.plot(hx, hy, color='#38bdf8', linewidth=3.0, label='Hexagonal Base Cutout')
    ax1.fill(hx, hy, color='#0284c7', alpha=0.15)
    
    # Highlight Left and Right Flat Sides (120 mm)
    ax1.plot([-half_W, -half_W], [-half_flat, half_flat], color='#f43f5e', linewidth=4.0, label='Flat Edge (120mm - Matches Wheel Bracket)')
    ax1.plot([half_W, half_W], [-half_flat, half_flat], color='#f43f5e', linewidth=4.0)
    
    # L-Clamp Mounting Holes on Base (Offset 15mm inward from flat edge, 60mm pitch)
    l_hole_offset = 15.0
    l_hole_pitch = 60.0
    
    # Left L-clamp holes
    l_holes_left = [
        np.array([-half_W + l_hole_offset, -l_hole_pitch/2.0]),
        np.array([-half_W + l_hole_offset, +l_hole_pitch/2.0])
    ]
    # Right L-clamp holes
    l_holes_right = [
        np.array([+half_W - l_hole_offset, -l_hole_pitch/2.0]),
        np.array([+half_W - l_hole_offset, +l_hole_pitch/2.0])
    ]
    
    first_h = True
    for h in l_holes_left + l_holes_right:
        circle = plt.Circle((h[0], h[1]), 2.1, color='#10b981', fill=True, 
                            label='L-Clamp M4 Mounting Holes' if first_h else "")
        ax1.add_patch(circle)
        first_h = False
        
    # Dimension Callouts for Subplot 1
    # Total Length (Y)
    ax1.annotate('', xy=(0, -half_L), xytext=(0, half_L),
                 arrowprops=dict(arrowstyle='<->', color='#fbbf24', lw=1.8))
    ax1.text(10, 0, f'Total Length: 40 cm (400 mm)', color='#fbbf24', fontsize=11, weight='bold', rotation=90, va='center')
    
    # Total Width (X)
    ax1.annotate('', xy=(-half_W, -half_L-20), xytext=(half_W, -half_L-20),
                 arrowprops=dict(arrowstyle='<->', color='#fbbf24', lw=1.8))
    ax1.text(0, -half_L-35, f'Total Width: 35 cm (350 mm)', color='#fbbf24', fontsize=11, weight='bold', ha='center')
    
    # Flat Edge Length (120mm)
    ax1.annotate(f'Flat Side: 12 cm (120 mm)', xy=(-half_W, 0), xytext=(-half_W-70, 0),
                 color='#f43f5e', fontsize=10, weight='bold', va='center', ha='right',
                 arrowprops=dict(arrowstyle='->', color='#f43f5e', lw=1.5))
                 
    ax1.annotate(f'Front Pointy Apex', xy=(0, half_L), xytext=(0, half_L+25),
                 color='#38bdf8', fontsize=10, weight='bold', ha='center',
                 arrowprops=dict(arrowstyle='->', color='#38bdf8', lw=1.5))
                 
    ax1.set_aspect('equal', 'box')
    ax1.grid(True, linestyle='--', alpha=0.3, color='#475569')
    ax1.set_title('1. Base Plate CAD Geometry (Top View)', color='#f8fafc', fontsize=13, pad=12, weight='bold')
    ax1.set_xlabel('X Dimension (mm)', color='#94a3b8', fontsize=10)
    ax1.set_ylabel('Y Dimension (mm)', color='#94a3b8', fontsize=10)
    ax1.tick_params(colors='#94a3b8')
    ax1.legend(facecolor='#1e293b', edgecolor='#475569', labelcolor='#f8fafc', loc='upper right', fontsize=9)

    # -----------------------------------------------------------------
    # SUBPLOT 2: Rover Assembly Schematic (Base + Brackets + Wheels)
    # -----------------------------------------------------------------
    ax2.set_facecolor('#1e293b')
    ax2.plot(hx, hy, color='#38bdf8', linewidth=2.0, linestyle='--', label='Hexagonal Base Plate')
    ax2.fill(hx, hy, color='#0284c7', alpha=0.10)
    
    # Draw Wheel Attachment Brackets attached on Left & Right
    # Left Outer & Inner Brackets
    # Bracket top span is 120mm, sitting along X = -175mm
    # Legs angle outward down-left and up-left
    # Bracket length of legs = 110mm @ 45deg => delta_X = 110*cos(45) = 77.78mm, delta_Y = 77.78mm
    
    # Left Brackets representation
    ax2.plot([-half_W, -half_W], [-60, 60], color='#f43f5e', linewidth=5.0, label='Wheel Attachment Brackets (4 Pcs)')
    # Left Front Arm
    ax2.plot([-half_W, -half_W - 77.8], [60, 60 + 77.8], color='#f43f5e', linewidth=3.5)
    # Left Back Arm
    ax2.plot([-half_W, -half_W - 77.8], [-60, -60 - 77.8], color='#f43f5e', linewidth=3.5)
    
    # Right Brackets representation
    ax2.plot([half_W, half_W], [-60, 60], color='#f43f5e', linewidth=5.0)
    # Right Front Arm
    ax2.plot([half_W, half_W + 77.8], [60, 60 + 77.8], color='#f43f5e', linewidth=3.5)
    # Right Back Arm
    ax2.plot([half_W, half_W + 77.8], [-60, -60 - 77.8], color='#f43f5e', linewidth=3.5)
    
    # Wheels (4 Wheels on the 4 leg ends)
    wheel_w = 40.0 # wheel width
    wheel_d = 85.0 # wheel diameter
    
    wheel_centers = [
        (-half_W - 77.8, 60 + 77.8),   # Front-Left
        (-half_W - 77.8, -60 - 77.8),  # Back-Left
        (half_W + 77.8, 60 + 77.8),    # Front-Right
        (half_W + 77.8, -60 - 77.8),   # Back-Right
    ]
    
    first_w = True
    for (cx, cy) in wheel_centers:
        rect = patches.Rectangle((cx - wheel_w/2.0, cy - wheel_d/2.0), wheel_w, wheel_d,
                                 linewidth=1.5, edgecolor='#eab308', facecolor='#ca8a04', alpha=0.8,
                                 label='Rover Wheels (4WD)' if first_w else "")
        ax2.add_patch(rect)
        first_w = False
        
    # Draw L-Clamps schematic (connecting base to brackets)
    ax2.plot([-half_W, -half_W+15], [30, 30], color='#10b981', linewidth=4.0, label='L-Clamps')
    ax2.plot([-half_W, -half_W+15], [-30, -30], color='#10b981', linewidth=4.0)
    ax2.plot([half_W-15, half_W], [30, 30], color='#10b981', linewidth=4.0)
    ax2.plot([half_W-15, half_W], [-30, -30], color='#10b981', linewidth=4.0)
    
    ax2.annotate('L-Clamp Base Attachment', xy=(-half_W+7.5, 30), xytext=(-half_W+50, 80),
                 color='#10b981', fontsize=9, weight='bold',
                 arrowprops=dict(arrowstyle='->', color='#10b981', lw=1.2))
                 
    ax2.set_aspect('equal', 'box')
    ax2.grid(True, linestyle='--', alpha=0.3, color='#475569')
    ax2.set_title('2. Full Rover Assembly Concept (Top View)', color='#f8fafc', fontsize=13, pad=12, weight='bold')
    ax2.set_xlabel('X Dimension (mm)', color='#94a3b8', fontsize=10)
    ax2.set_ylabel('Y Dimension (mm)', color='#94a3b8', fontsize=10)
    ax2.tick_params(colors='#94a3b8')
    ax2.legend(facecolor='#1e293b', edgecolor='#475569', labelcolor='#f8fafc', loc='upper right', fontsize=9)
    
    plt.suptitle('M.I.N.E.R.S. Rover Hexagonal Base Plate & Wheel Assembly Concept', color='#f8fafc', fontsize=15, weight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    png_filename = 'rover_base_preview.png'
    plt.savefig(png_filename, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"Saved base preview image: {png_filename}")

if __name__ == '__main__':
    generate_base_preview()
