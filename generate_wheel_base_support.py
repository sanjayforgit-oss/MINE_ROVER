import os
import ezdxf
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def generate_wheel_base_support(w_outer_tab=6.0, w_slot=1.7, w_mid_part=20.0, l_middle_path=250.0, h_total=65.0, h_slot=50.0):
    w_total = (w_outer_tab * 2) + (w_slot * 4) + (w_mid_part * 2) + l_middle_path
    h_spine = h_total - h_slot
    
    # 20 Vertices defining the perimeter counter-clockwise
    pts = []
    x = 0.0
    pts.append((0.0, 0.0))
    
    # Left outer tab
    x += w_outer_tab
    pts.append((x, 0.0))
    pts.append((x, h_slot))
    x += w_slot
    pts.append((x, h_slot))
    pts.append((x, 0.0))
    
    # Left middle part
    x += w_mid_part
    pts.append((x, 0.0))
    pts.append((x, h_slot))
    x += w_slot
    pts.append((x, h_slot))
    pts.append((x, 0.0))
    
    # Central middle path
    x += l_middle_path
    pts.append((x, 0.0))
    pts.append((x, h_slot))
    x += w_slot
    pts.append((x, h_slot))
    pts.append((x, 0.0))
    
    # Right middle part
    x += w_mid_part
    pts.append((x, 0.0))
    pts.append((x, h_slot))
    x += w_slot
    pts.append((x, h_slot))
    pts.append((x, 0.0))
    
    # Right outer tab
    x += w_outer_tab
    pts.append((x, 0.0))
    
    # Right edge & Top spine
    pts.append((x, h_total))
    pts.append((0.0, h_total))
    
    return pts, w_total, h_total

def save_dxf(pts, filepath):
    doc = ezdxf.new('R2000')
    doc.units = ezdxf.units.MM
    msp = doc.modelspace()
    
    # Add Layer for Laser Cutting
    doc.layers.add('CUT_OUTER', color=1) # Red
    
    # Add closed LWPOLYLINE
    msp.add_lwpolyline(pts, close=True, dxfattribs={'layer': 'CUT_OUTER'})
    
    doc.saveas(filepath)
    print(f"[DXF Saved] {filepath}")

def save_svg(pts, w_total, h_total, filepath, margin=5.0):
    svg_w = w_total + 2 * margin
    svg_h = h_total + 2 * margin
    
    # SVG coordinates have Y pointing down, so flip Y
    svg_pts = []
    for px, py in pts:
        sx = margin + px
        sy = margin + (h_total - py)
        svg_pts.append(f"{sx:.3f},{sy:.3f}")
    
    points_str = " ".join(svg_pts)
    
    svg_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="{svg_w:.2f}mm" height="{svg_h:.2f}mm" viewBox="0 0 {svg_w:.2f} {svg_h:.2f}" xmlns="http://www.w3.org/2000/svg">
    <title>M.I.N.E.R.S. Rover - Wheel Base Support Crossbar (1:1 Scale)</title>
    <desc>Total Height: {h_total}mm, Slot Height: 50mm, Middle Path: 250mm, Left/Right Middle Parts: 20mm, Slots: 1.7mm</desc>
    <g id="CUT_OUTER" stroke="#FF0000" stroke-width="0.3" fill="none">
        <polygon points="{points_str}" />
    </g>
</svg>
"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print(f"[SVG Saved] {filepath}")

def generate_preview_image(pts, w_total, h_total, filepath):
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(15, 5.5), dpi=200)
    fig.patch.set_facecolor('#0b0f19')
    ax.set_facecolor('#0b0f19')
    
    # Draw filled polygon
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    poly = patches.Polygon(pts, closed=True, facecolor='#1e293b', edgecolor='#38bdf8', linewidth=2.0)
    ax.add_patch(poly)
    
    # Highlight the 4 slots in bright yellow/amber
    w_outer = 6.0
    w_slot = 1.7
    w_mid = 20.0
    l_mid = 250.0
    h_slot = 50.0
    
    slot_starts = [
        w_outer,
        w_outer + w_slot + w_mid,
        w_outer + w_slot + w_mid + w_slot + l_mid,
        w_outer + w_slot + w_mid + w_slot + l_mid + w_slot + w_mid
    ]
    
    for idx, sx in enumerate(slot_starts):
        s_rect = patches.Rectangle((sx, 0), w_slot, h_slot, facecolor='#f59e0b', edgecolor='#fbbf24', alpha=0.35, linewidth=1.2)
        ax.add_patch(s_rect)
        ax.text(sx + w_slot/2, h_slot/2, f"Slot {idx+1}\n1.7mm", color='#fef08a', fontsize=7, ha='center', va='center', rotation=90, fontweight='bold')
    
    # Dimensions & Annotations
    # 1. Middle Path 250mm arrow
    x_mid_start = w_outer + w_slot + w_mid + w_slot
    x_mid_end = x_mid_start + l_mid
    y_dim = -8
    ax.annotate('', xy=(x_mid_start, y_dim), xytext=(x_mid_end, y_dim),
                arrowprops=dict(arrowstyle='<|-|>', color='#38bdf8', lw=2.0, mutation_scale=15))
    ax.text((x_mid_start + x_mid_end)/2, y_dim - 4, "MIDDLE PATH LENGTH: 250.0 mm", color='#38bdf8', fontsize=11, fontweight='bold', ha='center', va='top')
    
    # 2. Left Middle Part 20mm arrow
    x_lmid_start = w_outer + w_slot
    x_lmid_end = x_lmid_start + w_mid
    ax.annotate('', xy=(x_lmid_start, y_dim), xytext=(x_lmid_end, y_dim),
                arrowprops=dict(arrowstyle='<|-|>', color='#10b981', lw=1.8, mutation_scale=12))
    ax.text((x_lmid_start + x_lmid_end)/2, y_dim - 4, "20.0 mm", color='#10b981', fontsize=9, fontweight='bold', ha='center', va='top')
    
    # 3. Right Middle Part 20mm arrow
    x_rmid_start = x_mid_end + w_slot
    x_rmid_end = x_rmid_start + w_mid
    ax.annotate('', xy=(x_rmid_start, y_dim), xytext=(x_rmid_end, y_dim),
                arrowprops=dict(arrowstyle='<|-|>', color='#10b981', lw=1.8, mutation_scale=12))
    ax.text((x_rmid_start + x_rmid_end)/2, y_dim - 4, "20.0 mm", color='#10b981', fontsize=9, fontweight='bold', ha='center', va='top')
    
    # 4. Total Height 65mm arrow on left
    x_h_dim = -12
    ax.annotate('', xy=(x_h_dim, 0), xytext=(x_h_dim, h_total),
                arrowprops=dict(arrowstyle='<|-|>', color='#f43f5e', lw=2.0, mutation_scale=15))
    ax.text(x_h_dim - 4, h_total/2, "TOTAL HEIGHT: 65.0 mm", color='#f43f5e', fontsize=10, fontweight='bold', ha='right', va='center', rotation=90)
    
    # 5. Slot Height 50mm arrow on right
    x_sd_dim = w_total + 10
    ax.annotate('', xy=(x_sd_dim, 0), xytext=(x_sd_dim, h_slot),
                arrowprops=dict(arrowstyle='<|-|>', color='#fbbf24', lw=1.6, mutation_scale=12))
    ax.text(x_sd_dim + 4, h_slot/2, "SLOT HEIGHT: 50.0 mm", color='#fbbf24', fontsize=9, fontweight='bold', ha='left', va='center', rotation=90)
    
    # Top Spine 15mm note
    ax.annotate('Top Solid Spine: 15.0 mm', xy=(w_total/2, 57.5), xytext=(w_total/2, 73),
                color='#94a3b8', fontsize=9, ha='center',
                arrowprops=dict(arrowstyle='->', color='#94a3b8', lw=1.2))
    
    # Total Overall Span
    ax.annotate(f"TOTAL SPAN: {w_total:.1f} mm", xy=(0, h_total + 12), xytext=(w_total, h_total + 12),
                arrowprops=dict(arrowstyle='<|-|>', color='#e2e8f0', lw=1.5, mutation_scale=12))
    ax.text(w_total/2, h_total + 16, f"TOTAL OVERALL SPAN = {w_total:.1f} mm", color='#e2e8f0', fontsize=10, fontweight='bold', ha='center')
    
    # Title & Subtitle
    plt.title("M.I.N.E.R.S. ROVER — WHEEL BASE SUPPORT CROSSBAR BRACKET\n1:1 Laser Cutting Spec | Dual Locking Slots for 1.6mm Brackets",
              color='#f8fafc', fontsize=12, fontweight='bold', pad=25)
    
    # Limits & aspect
    ax.set_xlim(-25, w_total + 30)
    ax.set_ylim(-20, h_total + 25)
    ax.set_aspect('equal')
    ax.axis('off')
    
    plt.tight_layout()
    plt.savefig(filepath, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[Preview Image Saved] {filepath}")

if __name__ == '__main__':
    pts, w_tot, h_tot = generate_wheel_base_support()
    
    # Output paths
    workspace_dir = "e:/miners"
    artifact_dir = "C:/Users/sanja/.gemini/antigravity-ide/brain/4fb4b155-d4bd-49ab-b212-b5b5c38b8f10"
    
    # 1. Save in Workspace
    save_dxf(pts, os.path.join(workspace_dir, "wheel_base_support_crossbar.dxf"))
    save_svg(pts, w_tot, h_tot, os.path.join(workspace_dir, "wheel_base_support_crossbar.svg"))
    generate_preview_image(pts, w_tot, h_tot, os.path.join(workspace_dir, "wheel_base_support_crossbar_preview.png"))
    
    # 2. Save in Artifact directory for embedding
    save_dxf(pts, os.path.join(artifact_dir, "wheel_base_support_crossbar.dxf"))
    save_svg(pts, w_tot, h_tot, os.path.join(artifact_dir, "wheel_base_support_crossbar.svg"))
    generate_preview_image(pts, w_tot, h_tot, os.path.join(artifact_dir, "wheel_base_support_crossbar_preview.png"))
    
    print("\n[SUCCESS] All DXF, SVG, and Preview files successfully generated!")
