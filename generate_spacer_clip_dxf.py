import os
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import ezdxf
from ezdxf import units

def generate_spacer_clip(
    w_center=20.0,    # Center block thickness (mm)
    w_slot=1.6,       # Slot gap width (1.6mm as requested - locks 1.6mm board)
    d_slot=50.0,      # Depth of slot (50mm)
    w_leg=6.0,        # Outer leg wall width (mm)
    h_top=8.0         # Top spine height (mm)
):
    w_total = 2 * w_leg + 2 * w_slot + w_center
    h_total = d_slot + h_top
    
    # 12-point closed polygon contour
    polygon = [
        (0.0, 0.0),                                       # 1. Left leg bottom-left
        (w_leg, 0.0),                                     # 2. Left leg bottom-right
        (w_leg, d_slot),                                  # 3. Left slot top-left
        (w_leg + w_slot, d_slot),                         # 4. Left slot top-right
        (w_leg + w_slot, 0.0),                            # 5. Center block bottom-left
        (w_leg + w_slot + w_center, 0.0),                 # 6. Center block bottom-right
        (w_leg + w_slot + w_center, d_slot),              # 7. Right slot top-left
        (w_leg + 2 * w_slot + w_center, d_slot),          # 8. Right slot top-right
        (w_leg + 2 * w_slot + w_center, 0.0),             # 9. Right leg bottom-left
        (w_total, 0.0),                                   # 10. Right leg bottom-right
        (w_total, h_total),                               # 11. Top spine top-right
        (0.0, h_total),                                   # 12. Top spine top-left
    ]
    
    # -------------------------------------------------------------
    # 1. CREATE DXF FILE
    # -------------------------------------------------------------
    doc = ezdxf.new('R2000')
    doc.units = units.MM
    msp = doc.modelspace()
    doc.layers.add('OUTER_CUT', color=1) # RED = Laser Cut
    
    msp.add_lwpolyline(polygon, close=True, dxfattribs={'layer': 'OUTER_CUT'})
    
    dxf_filename = 'wheel_bracket_spacer_clip.dxf'
    doc.saveas(dxf_filename)
    print(f"Saved DXF: {dxf_filename} (1.6mm Slot Width, 50mm Depth)")
    
    # -------------------------------------------------------------
    # 2. CREATE SVG FILE
    # -------------------------------------------------------------
    svg_filename = 'wheel_bracket_spacer_clip.svg'
    margin = 5.0
    width_svg = w_total + 2 * margin
    height_svg = h_total + 2 * margin
    
    def poly_to_svg_pts(poly):
        return " ".join([f"{p[0] + margin:.3f},{height_svg - (p[1] + margin):.3f}" for p in poly])
        
    svg_content = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="{width_svg}mm" height="{height_svg}mm" viewBox="0 0 {width_svg} {height_svg}" xmlns="http://www.w3.org/2000/svg">
    <g id="OUTER_CUT" stroke="#FF0000" stroke-width="0.3" fill="none">
        <polygon points="{poly_to_svg_pts(polygon)}" />
    </g>
</svg>'''
    with open(svg_filename, 'w') as f:
        f.write(svg_content)
    print(f"Saved SVG: {svg_filename}")

    # -------------------------------------------------------------
    # 3. CREATE PNG VISUAL PREVIEW DIAGRAM
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 9), dpi=300)
    fig.patch.set_facecolor('#0f172a') # Dark slate background
    ax.set_facecolor('#1e293b')
    
    poly_x = [p[0] for p in polygon] + [polygon[0][0]]
    poly_y = [p[1] for p in polygon] + [polygon[0][1]]
    
    ax.plot(poly_x, poly_y, color='#38bdf8', linewidth=3.0, label='Laser Cut Contour')
    ax.fill(poly_x, poly_y, color='#0284c7', alpha=0.25)
    
    # Highlight 1.6mm slots (Red) and 20mm center block (Green/Yellow)
    ax.fill_between([w_leg, w_leg + w_slot], [0, 0], [d_slot, d_slot], color='#f43f5e', alpha=0.3, label='1.6mm Board Slot Gap')
    ax.fill_between([w_leg + w_slot + w_center, w_leg + 2*w_slot + w_center], [0, 0], [d_slot, d_slot], color='#f43f5e', alpha=0.3)
    
    # Annotations & Dimensions
    # 20mm Center Thickness
    ax.annotate('', xy=(w_leg + w_slot, -2), xytext=(w_leg + w_slot + w_center, -2),
                arrowprops=dict(arrowstyle='<->', color='#fbbf24', lw=2.0))
    ax.text(w_leg + w_slot + w_center/2.0, -5, f'Inner Thickness: {w_center:.1f} mm', 
            color='#fbbf24', fontsize=11, weight='bold', ha='center', va='top')
            
    # Left 1.6mm Slot
    ax.annotate(f'Slot Gap: {w_slot:.1f} mm', xy=(w_leg + w_slot/2.0, d_slot/2.0),
                xytext=(w_leg - 15, d_slot/2.0),
                color='#f43f5e', fontsize=10, weight='bold', va='center', ha='right',
                arrowprops=dict(arrowstyle='->', color='#f43f5e', lw=1.5))

    # Right 1.6mm Slot
    ax.annotate(f'Slot Gap: {w_slot:.1f} mm', xy=(w_leg + w_slot + w_center + w_slot/2.0, d_slot/2.0),
                xytext=(w_leg + w_slot + w_center + w_slot + 15, d_slot/2.0),
                color='#f43f5e', fontsize=10, weight='bold', va='center', ha='left',
                arrowprops=dict(arrowstyle='->', color='#f43f5e', lw=1.5))
                
    # Slot Depth (50mm)
    ax.annotate('', xy=(-3, 0), xytext=(-3, d_slot),
                arrowprops=dict(arrowstyle='<->', color='#34d399', lw=2.0))
    ax.text(-6, d_slot/2.0, f'Slot Insertion Depth: {d_slot:.0f} mm', 
            color='#34d399', fontsize=11, weight='bold', va='center', ha='right', rotation=90)
            
    # Total Width
    ax.annotate('', xy=(0, h_total + 3), xytext=(w_total, h_total + 3),
                arrowprops=dict(arrowstyle='<->', color='#38bdf8', lw=1.8))
    ax.text(w_total/2.0, h_total + 5, f'Total Width: {w_total:.1f} mm', 
            color='#38bdf8', fontsize=11, weight='bold', ha='center', va='bottom')

    ax.set_aspect('equal', 'box')
    ax.grid(True, linestyle='--', alpha=0.3, color='#475569')
    ax.set_title('Dual Wheel Board Spacer Clip - 1.6 mm Slot Width (1:1 CAD Model)', color='#f8fafc', fontsize=13, pad=25, weight='bold')
    ax.set_xlabel('X Dimension (mm)', color='#94a3b8', fontsize=10)
    ax.set_ylabel('Y Dimension (mm)', color='#94a3b8', fontsize=10)
    ax.tick_params(colors='#94a3b8')
    ax.legend(facecolor='#1e293b', edgecolor='#475569', labelcolor='#f8fafc', loc='upper right')
    
    plt.tight_layout()
    png_filename = 'wheel_bracket_spacer_clip_preview.png'
    plt.savefig(png_filename, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"Saved PNG preview: {png_filename}")

if __name__ == '__main__':
    generate_spacer_clip()
