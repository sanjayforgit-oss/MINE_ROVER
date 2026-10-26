import os
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def generate_alternative_designs():
    wheel_mount_len = 182.9
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 7), dpi=300)
    fig.patch.set_facecolor('#0f172a') # Slate dark background
    
    # -------------------------------------------------------------------------
    # OPTION A: TACTICAL STEALTH OCTAGON (Chamfered Corners & Sensor Notch)
    # -------------------------------------------------------------------------
    ax = axes[0]
    ax.set_facecolor('#1e293b')
    
    L_a, W_a = 550.0, 400.0
    hL, hW = L_a / 2.0, W_a / 2.0
    half_side = wheel_mount_len / 2.0
    chamfer = 70.0
    
    v_a = [
        (-hW, -half_side),
        (-hW, +half_side),
        (-hW + chamfer, +hL - 40),
        (-40.0, +hL),           # Front camera notch left
        (+40.0, +hL),           # Front camera notch right
        (+hW - chamfer, +hL - 40),
        (+hW, +half_side),
        (+hW, -half_side),
        (+hW - chamfer, -hL + 40),
        (+40.0, -hL),           # Rear bumper right
        (-40.0, -hL),           # Rear bumper left
        (-hW + chamfer, -hL + 40),
    ]
    va_x = [p[0] for p in v_a] + [v_a[0][0]]
    va_y = [p[1] for p in v_a] + [v_a[0][1]]
    
    ax.plot(va_x, va_y, color='#38bdf8', linewidth=2.5, label='Octagon Outer Cut')
    ax.fill(va_x, va_y, color='#0284c7', alpha=0.15)
    
    ax.plot([-hW, -hW], [-half_side, half_side], color='#f43f5e', linewidth=4.0, label='Wheel Bracket Mount (18.3 cm)')
    ax.plot([hW, hW], [-half_side, half_side], color='#f43f5e', linewidth=4.0)
    
    ax.scatter([-hW+15, -hW+15, hW-15, hW-15], [-45.7, 45.7, -45.7, 45.7], color='#10b981', s=30, zorder=5, label='L-Clamp Holes')
    
    rect_battery = patches.Rectangle((-70, -120), 140, 240, linewidth=1.5, edgecolor='#34d399', facecolor='#059669', alpha=0.2, linestyle='--')
    ax.add_patch(rect_battery)
    ax.text(0, 0, 'Battery & Electronics\nInternal Bay', color='#34d399', fontsize=9, ha='center', va='center', weight='bold')
    
    ax.set_aspect('equal', 'box')
    ax.grid(True, linestyle='--', alpha=0.3, color='#475569')
    ax.set_title('OPTION A: Tactical Stealth Octagon\n(Sleek Chamfered Corners + Front Sensor Bay)', color='#f8fafc', fontsize=12, pad=10, weight='bold')
    ax.set_xlabel('X (mm)', color='#94a3b8', fontsize=9)
    ax.set_ylabel('Y (mm)', color='#94a3b8', fontsize=9)
    ax.tick_params(colors='#94a3b8')
    ax.legend(facecolor='#1e293b', edgecolor='#475569', labelcolor='#f8fafc', loc='upper right', fontsize=8)

    # -------------------------------------------------------------------------
    # OPTION B: AGGRESSIVE AERO-ARROWHEAD / WEDGE
    # -------------------------------------------------------------------------
    ax = axes[1]
    ax.set_facecolor('#1e293b')
    
    L_b, W_b = 560.0, 420.0
    hL_b, hW_b = L_b / 2.0, W_b / 2.0
    
    v_b = [
        (-hW_b + 20, -half_side),
        (-hW_b + 20, +half_side),
        (-hW_b + 80, +hL_b - 80),
        (0.0, +hL_b),             # Front Arrow Point
        (+hW_b - 80, +hL_b - 80),
        (+hW_b - 20, +half_side),
        (+hW_b - 20, -half_side),
        (+hW_b, -hL_b + 60),      # Wide rear wing
        (+60.0, -hL_b),
        (-60.0, -hL_b),
        (-hW_b, -hL_b + 60),
    ]
    vb_x = [p[0] for p in v_b] + [v_b[0][0]]
    vb_y = [p[1] for p in v_b] + [v_b[0][1]]
    
    ax.plot(vb_x, vb_y, color='#f59e0b', linewidth=2.5, label='Arrowhead Outer Cut')
    ax.fill(vb_x, vb_y, color='#d97706', alpha=0.15)
    
    ax.plot([-hW_b + 20, -hW_b + 20], [-half_side, half_side], color='#f43f5e', linewidth=4.0, label='Recessed Wheel Mount')
    ax.plot([hW_b - 20, hW_b - 20], [-half_side, half_side], color='#f43f5e', linewidth=4.0)
    
    ax.set_aspect('equal', 'box')
    ax.grid(True, linestyle='--', alpha=0.3, color='#475569')
    ax.set_title('OPTION B: Aggressive Aero Arrowhead\n(Tapered Nose Wedge + Recessed Side Mounts)', color='#f8fafc', fontsize=12, pad=10, weight='bold')
    ax.set_xlabel('X (mm)', color='#94a3b8', fontsize=9)
    ax.set_ylabel('Y (mm)', color='#94a3b8', fontsize=9)
    ax.tick_params(colors='#94a3b8')
    ax.legend(facecolor='#1e293b', edgecolor='#475569', labelcolor='#f8fafc', loc='upper right', fontsize=8)

    # -------------------------------------------------------------------------
    # OPTION C: HEAVY-DUTY INDUSTRIAL (Rounded Curves + Carrying Handles)
    # -------------------------------------------------------------------------
    ax = axes[2]
    ax.set_facecolor('#1e293b')
    
    L_c, W_c = 540.0, 380.0
    hL_c, hW_c = L_c / 2.0, W_c / 2.0
    r_corner = 40.0
    
    theta = np.linspace(0, np.pi/2, 10)
    
    tr_x = (hW_c - r_corner) + r_corner * np.cos(theta)
    tr_y = (hL_c - r_corner) + r_corner * np.sin(theta)
    
    tl_x = (-hW_c + r_corner) - r_corner * np.cos(theta[::-1])
    tl_y = (hL_c - r_corner) + r_corner * np.sin(theta[::-1])
    
    bl_x = (-hW_c + r_corner) - r_corner * np.cos(theta)
    bl_y = (-hL_c + r_corner) - r_corner * np.sin(theta)
    
    br_x = (hW_c - r_corner) + r_corner * np.cos(theta[::-1])
    br_y = (-hL_c + r_corner) - r_corner * np.sin(theta[::-1])
    
    vc_x = np.concatenate([tr_x, tl_x, bl_x, br_x, [tr_x[0]]])
    vc_y = np.concatenate([tr_y, tl_y, bl_y, br_y, [tr_y[0]]])
    
    ax.plot(vc_x, vc_y, color='#a855f7', linewidth=2.5, label='Industrial Rounded Outer Cut')
    ax.fill(vc_x, vc_y, color='#9333ea', alpha=0.15)
    
    ax.plot([-hW_c, -hW_c], [-half_side, half_side], color='#f43f5e', linewidth=4.0, label='Wheel Bracket Mount')
    ax.plot([hW_c, hW_c], [-half_side, half_side], color='#f43f5e', linewidth=4.0)
    
    handle_f = patches.FancyBboxPatch((-50, hL_c - 45), 100, 20, boxstyle="round,pad=2", linewidth=1.5, edgecolor='#c084fc', facecolor='#1e293b')
    handle_r = patches.FancyBboxPatch((-50, -hL_c + 25), 100, 20, boxstyle="round,pad=2", linewidth=1.5, edgecolor='#c084fc', facecolor='#1e293b')
    ax.add_patch(handle_f)
    ax.add_patch(handle_r)
    ax.text(0, hL_c - 35, 'Carry Handle', color='#c084fc', fontsize=8, ha='center', va='center', weight='bold')
    ax.text(0, -hL_c + 35, 'Carry Handle', color='#c084fc', fontsize=8, ha='center', va='center', weight='bold')

    ax.set_aspect('equal', 'box')
    ax.grid(True, linestyle='--', alpha=0.3, color='#475569')
    ax.set_title('OPTION C: Heavy-Duty Industrial\n(Filleted Curves + Dual Carrying Handles)', color='#f8fafc', fontsize=12, pad=10, weight='bold')
    ax.set_xlabel('X (mm)', color='#94a3b8', fontsize=9)
    ax.set_ylabel('Y (mm)', color='#94a3b8', fontsize=9)
    ax.tick_params(colors='#94a3b8')
    ax.legend(facecolor='#1e293b', edgecolor='#475569', labelcolor='#f8fafc', loc='upper right', fontsize=8)

    plt.suptitle('M.I.N.E.R.S. Rover Base Plate - Top View Alternative Design Concepts', color='#f8fafc', fontsize=15, weight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    
    png_filename = 'rover_base_alternative_designs.png'
    plt.savefig(png_filename, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"Saved alternative designs preview: {png_filename}")

if __name__ == '__main__':
    generate_alternative_designs()
