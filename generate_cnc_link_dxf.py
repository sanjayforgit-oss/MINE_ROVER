import os
import math
import shutil
import ezdxf
from ezdxf import units
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def create_dxf_r2000(filename, length=120.0, width=8.0, hole_dia=3.0, inner_dist=105.0):
    """
    AutoCAD 2000 (AC1015) DXF with closed LWPOLYLINE (with arc bulges) and CIRCLEs.
    Separated into layers for RDWorks / CNC CAM:
      - DRILL_HOLES: Color 5 (Blue) - 3.0mm holes to drill/bore first
      - CUT_OUTER:   Color 1 (Red)  - 120x8mm outer perimeter cut second
    """
    doc = ezdxf.new('R2000')
    doc.units = units.MM
    msp = doc.modelspace()
    
    doc.layers.add('CUT_OUTER', color=1)
    doc.layers.add('DRILL_HOLES', color=5)
    
    r_end = width / 2.0      # 4.0 mm
    r_hole = hole_dia / 2.0  # 1.5 mm
    
    # Calculate hole centers from inner distance (105.0 mm)
    # pitch = inner_dist + hole_dia = 105.0 + 3.0 = 108.0 mm
    pitch = inner_dist + hole_dia
    hole_offset = (length - pitch) / 2.0  # (120 - 108) / 2 = 6.0 mm
    left_hole_x = hole_offset             # 6.0 mm
    right_hole_x = length - hole_offset   # 114.0 mm
    center_y = width / 2.0                # 4.0 mm
    
    # Circles
    msp.add_circle((left_hole_x, center_y), radius=r_hole, dxfattribs={'layer': 'DRILL_HOLES'})
    msp.add_circle((right_hole_x, center_y), radius=r_hole, dxfattribs={'layer': 'DRILL_HOLES'})
    
    # Outer profile: Obround
    poly_points = [
        (r_end, 0.0, 0, 0, 0),
        (length - r_end, 0.0, 0, 0, 1.0),
        (length - r_end, width, 0, 0, 0),
        (r_end, width, 0, 0, 1.0)
    ]
    msp.add_lwpolyline(poly_points, format='xyseb', close=True, dxfattribs={'layer': 'CUT_OUTER'})
    
    doc.saveas(filename)
    print(f"Saved R2000 DXF: {filename}")

def create_dxf_r12(filename, length=120.0, width=8.0, hole_dia=3.0, inner_dist=105.0):
    """
    AutoCAD R12 (AC1009) DXF with discrete LINEs, ARCs, and CIRCLEs.
    Universally accepted by RDWorks, Mach3, GRBL, ArtCAM, Aspire, Vectric.
    """
    doc = ezdxf.new('R12')
    doc.units = units.MM
    msp = doc.modelspace()
    
    doc.layers.add('CUT_OUTER', color=1)
    doc.layers.add('DRILL_HOLES', color=5)
    
    r_end = width / 2.0      # 4.0 mm
    r_hole = hole_dia / 2.0  # 1.5 mm
    center_y = width / 2.0  # 4.0 mm
    
    pitch = inner_dist + hole_dia
    hole_offset = (length - pitch) / 2.0  # 6.0 mm
    left_hole_x = hole_offset             # 6.0 mm
    right_hole_x = length - hole_offset   # 114.0 mm
    
    # Circles
    msp.add_circle((left_hole_x, center_y), radius=r_hole, dxfattribs={'layer': 'DRILL_HOLES'})
    msp.add_circle((right_hole_x, center_y), radius=r_hole, dxfattribs={'layer': 'DRILL_HOLES'})
    
    # Straight lines
    msp.add_line((r_end, 0.0), (length - r_end, 0.0), dxfattribs={'layer': 'CUT_OUTER'})
    msp.add_line((length - r_end, width), (r_end, width), dxfattribs={'layer': 'CUT_OUTER'})
    
    # Right Arc: Center=(length - r_end, center_y), radius=r_end, from 270° to 90° (CCW)
    msp.add_arc(
        center=(length - r_end, center_y),
        radius=r_end,
        start_angle=270.0,
        end_angle=90.0,
        dxfattribs={'layer': 'CUT_OUTER'}
    )
    
    # Left Arc: Center=(r_end, center_y), radius=r_end, from 90° to 270° (CCW)
    msp.add_arc(
        center=(r_end, center_y),
        radius=r_end,
        start_angle=90.0,
        end_angle=270.0,
        dxfattribs={'layer': 'CUT_OUTER'}
    )
    
    doc.saveas(filename)
    print(f"Saved R12 DXF: {filename}")

def create_svg(filename, length=120.0, width=8.0, hole_dia=3.0, inner_dist=105.0):
    """
    Vector SVG file for RDWorks direct import or web preview.
    """
    margin = 10.0
    view_w = length + 2 * margin
    view_h = width + 2 * margin
    r_end = width / 2.0
    r_hole = hole_dia / 2.0
    center_y = margin + width / 2.0
    
    pitch = inner_dist + hole_dia
    hole_offset = (length - pitch) / 2.0
    left_hole_x = margin + hole_offset
    right_hole_x = margin + length - hole_offset
    
    x_l_center = margin + r_end
    x_r_center = margin + length - r_end
    
    y_top = margin
    y_bot = margin + width
    
    svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="{view_w}mm" height="{view_h}mm" viewBox="0 0 {view_w} {view_h}" xmlns="http://www.w3.org/2000/svg">
    <title>M.I.N.E.R.S. Rover - CNC Link Plate 120x8mm (Inner Hole Distance 105mm)</title>
    <rect width="{view_w}" height="{view_h}" fill="#0f172a" />
    
    <!-- Outer Contour (Red Cut Layer) -->
    <path d="M {x_l_center},{y_bot} 
             L {x_r_center},{y_bot} 
             A {r_end},{r_end} 0 0,0 {x_r_center},{y_top} 
             L {x_l_center},{y_top} 
             A {r_end},{r_end} 0 0,0 {x_l_center},{y_bot} Z" 
          stroke="#ef4444" stroke-width="0.3" fill="#1e293b" fill-opacity="0.8" id="CUT_OUTER" />
          
    <!-- 3mm Holes (Blue Drill Layer) -->
    <circle cx="{left_hole_x}" cy="{center_y}" r="{r_hole}" 
            stroke="#38bdf8" stroke-width="0.3" fill="#0f172a" id="DRILL_HOLE_LEFT" />
    <circle cx="{right_hole_x}" cy="{center_y}" r="{r_hole}" 
            stroke="#38bdf8" stroke-width="0.3" fill="#0f172a" id="DRILL_HOLE_RIGHT" />
            
    <!-- Dimension text -->
    <text x="{view_w / 2}" y="{y_bot + 6}" font-family="Arial, sans-serif" font-size="2.5" fill="#94a3b8" text-anchor="middle">
        Total Length: {length:.1f} mm | Width: {width:.1f} mm | Inner Hole Span: {inner_dist:.1f} mm | Hole: Ø{hole_dia:.1f} mm
    </text>
</svg>'''
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(svg)
    print(f"Saved SVG: {filename}")

def create_preview_png(filename, length=120.0, width=8.0, hole_dia=3.0, inner_dist=105.0):
    """
    Detailed 300 DPI technical drawing showing inner distance, center pitch, and all clearances.
    """
    fig, ax = plt.subplots(figsize=(15, 6.5), dpi=300)
    fig.patch.set_facecolor('#0b0f19')
    ax.set_facecolor('#111827')
    
    r_end = width / 2.0
    r_hole = hole_dia / 2.0
    center_y = width / 2.0
    
    pitch = inner_dist + hole_dia
    hole_offset = (length - pitch) / 2.0  # 6.0 mm
    left_hole_x = hole_offset             # 6.0 mm
    right_hole_x = length - hole_offset   # 114.0 mm
    
    inner_l_edge = left_hole_x + r_hole   # 7.5 mm
    inner_r_edge = right_hole_x - r_hole  # 112.5 mm
    
    # Outer profile
    angles_r = [math.radians(a) for a in range(-90, 91, 5)]
    arc_r_x = [length - r_end + r_end * math.cos(a) for a in angles_r]
    arc_r_y = [center_y + r_end * math.sin(a) for a in angles_r]
    
    angles_l = [math.radians(a) for a in range(90, 271, 5)]
    arc_l_x = [r_end + r_end * math.cos(a) for a in angles_l]
    arc_l_y = [center_y + r_end * math.sin(a) for a in angles_l]
    
    peri_x = [r_end] + arc_r_x + [length - r_end] + arc_l_x + [r_end]
    peri_y = [0.0] + arc_r_y + [width] + arc_l_y + [0.0]
    
    ax.plot(peri_x, peri_y, color='#ef4444', linewidth=2.8, label='Outer CNC Cut Contour (Red: CUT_OUTER)')
    ax.fill(peri_x, peri_y, color='#3b82f6', alpha=0.15)
    
    # Plot Holes
    circle_l = patches.Circle((left_hole_x, center_y), r_hole, edgecolor='#38bdf8', facecolor='#0b0f19', linewidth=2.2, label='Ø3.0 mm Drill Hole (Blue: DRILL_HOLES)')
    circle_r = patches.Circle((right_hole_x, center_y), r_hole, edgecolor='#38bdf8', facecolor='#0b0f19', linewidth=2.2)
    ax.add_patch(circle_l)
    ax.add_patch(circle_r)
    
    # Centerlines
    ax.plot([0, length], [center_y, center_y], color='#94a3b8', linestyle='-.', linewidth=1.0, alpha=0.6)
    ax.plot([left_hole_x, left_hole_x], [-2, width + 2], color='#94a3b8', linestyle='-.', linewidth=1.0, alpha=0.6)
    ax.plot([right_hole_x, right_hole_x], [-2, width + 2], color='#94a3b8', linestyle='-.', linewidth=1.0, alpha=0.6)
    
    # DIMENSION 1: INNER DISTANCE (10.5 cm = 105.0 mm) - Highlighted in Cyan
    y_dim_inner = width + 5.0
    ax.annotate('', xy=(inner_l_edge, y_dim_inner), xytext=(inner_r_edge, y_dim_inner),
                arrowprops=dict(arrowstyle='<->', color='#06b6d4', lw=2.2))
    ax.plot([inner_l_edge, inner_l_edge], [center_y + r_hole, y_dim_inner + 1], color='#06b6d4', linestyle=':', lw=1.2)
    ax.plot([inner_r_edge, inner_r_edge], [center_y + r_hole, y_dim_inner + 1], color='#06b6d4', linestyle=':', lw=1.2)
    ax.text(length / 2.0, y_dim_inner + 1.6, f'Inner Distance (Circle Start to Start): {inner_dist:.1f} mm ({inner_dist/10.0:.1f} cm)',
            color='#06b6d4', fontsize=11, weight='bold', ha='center', va='bottom')
            
    # DIMENSION 2: CENTER-TO-CENTER PITCH (108.0 mm)
    y_dim_pitch = width + 13.0
    ax.annotate('', xy=(left_hole_x, y_dim_pitch), xytext=(right_hole_x, y_dim_pitch),
                arrowprops=dict(arrowstyle='<->', color='#38bdf8', lw=1.6))
    ax.plot([left_hole_x, left_hole_x], [width, y_dim_pitch + 1], color='#38bdf8', linestyle=':', lw=1.0)
    ax.plot([right_hole_x, right_hole_x], [width, y_dim_pitch + 1], color='#38bdf8', linestyle=':', lw=1.0)
    ax.text(length / 2.0, y_dim_pitch + 1.4, f'Center-to-Center Pitch: {pitch:.1f} mm (10.8 cm)',
            color='#38bdf8', fontsize=10, weight='bold', ha='center', va='bottom')

    # DIMENSION 3: TOTAL LENGTH (120.0 mm = 12.0 cm)
    y_dim_total = -6.0
    ax.annotate('', xy=(0, y_dim_total), xytext=(length, y_dim_total),
                arrowprops=dict(arrowstyle='<->', color='#fbbf24', lw=2.0))
    ax.plot([0, 0], [0, y_dim_total - 1], color='#fbbf24', linestyle=':', lw=1.0)
    ax.plot([length, length], [0, y_dim_total - 1], color='#fbbf24', linestyle=':', lw=1.0)
    ax.text(length / 2.0, y_dim_total - 2.5, f'Total Length: {length:.1f} mm (12.0 cm)',
            color='#fbbf24', fontsize=11, weight='bold', ha='center', va='top')
            
    # DIMENSION 4: HOLE OFFSET FROM END (6.0 mm) & WALL MARGIN (4.5 mm)
    y_dim_off = -14.0
    ax.annotate('', xy=(0, y_dim_off), xytext=(left_hole_x, y_dim_off),
                arrowprops=dict(arrowstyle='<->', color='#a855f7', lw=1.6))
    ax.plot([left_hole_x, left_hole_x], [y_dim_total - 1, y_dim_off - 1], color='#a855f7', linestyle=':', lw=1.0)
    ax.text(left_hole_x / 2.0, y_dim_off - 2.0, f'Center: {hole_offset:.1f} mm\nTip Wall: 4.5 mm',
            color='#a855f7', fontsize=8.5, weight='bold', ha='center', va='top')

    # DIMENSION 5: TOTAL WIDTH (8.0 mm)
    x_dim_w = -7.0
    ax.annotate('', xy=(x_dim_w, 0), xytext=(x_dim_w, width),
                arrowprops=dict(arrowstyle='<->', color='#4ade80', lw=1.8))
    ax.plot([0, x_dim_w - 1], [0, 0], color='#4ade80', linestyle=':', lw=1.0)
    ax.plot([0, x_dim_w - 1], [width, width], color='#4ade80', linestyle=':', lw=1.0)
    ax.text(x_dim_w - 2.0, width / 2.0, f'Width: {width:.1f} mm',
            color='#4ade80', fontsize=10, weight='bold', ha='right', va='center', rotation=90)
            
    # Hole diameter callout
    ax.annotate(f'Drill Hole: Ø{hole_dia:.1f} mm\n(2.5 mm top/bottom margin)',
                xy=(left_hole_x, center_y + r_hole),
                xytext=(left_hole_x + 8, width + 21),
                color='#38bdf8', fontsize=9.5, weight='bold',
                arrowprops=dict(arrowstyle='->', color='#38bdf8', lw=1.5, connectionstyle="arc3,rad=-0.15"))
                
    # End radius callout
    ax.annotate(f'Full Round: R{r_end:.1f} mm',
                xy=(length, center_y),
                xytext=(length + 5, center_y + 4),
                color='#f87171', fontsize=9.5, weight='bold',
                arrowprops=dict(arrowstyle='->', color='#f87171', lw=1.5))
                
    # Plate specification badge
    badge_text = "3-AXIS CNC ROUTER PROGRAM:\n• Stock Thickness: 2.0 mm\n• Inner Hole Clearance: 105.0 mm (10.5 cm)\n• Tool: 2.0 mm Flat Endmill\n• Passes: 2 passes @ 1.1 mm depth\n• Total Depth: Z -2.2 mm (through cut)\n• G-Code File: link_plate_120x8mm_cnc_cut.nc"
    ax.text(0.98, 0.05, badge_text, transform=ax.transAxes,
            color='#e2e8f0', fontsize=8.5, fontfamily='monospace',
            bbox=dict(boxstyle='round,pad=0.6', facecolor='#1e293b', edgecolor='#475569', alpha=0.9),
            ha='right', va='bottom')

    ax.set_aspect('equal')
    ax.set_xlim(-22, length + 25)
    ax.set_ylim(-22, width + 30)
    ax.grid(True, linestyle='--', alpha=0.2, color='#64748b')
    ax.set_title('CNC Link Plate - 120 mm × 8 mm × 2 mm (Inner Hole Span = 105.0 mm)',
                 color='#f8fafc', fontsize=13, weight='bold', pad=15)
    ax.set_xlabel('X Dimension (mm)', color='#94a3b8', fontsize=9)
    ax.set_ylabel('Y Dimension (mm)', color='#94a3b8', fontsize=9)
    ax.tick_params(colors='#94a3b8')
    ax.legend(facecolor='#1e293b', edgecolor='#475569', labelcolor='#f8fafc', loc='upper left', fontsize=8.5)
    
    plt.tight_layout()
    plt.savefig(filename, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"Saved PNG Preview: {filename}")

def generate_gcode(filename, length=120.0, width=8.0, hole_dia=3.0, inner_dist=105.0, plate_thick=2.0, tool_dia=2.0):
    """
    Standard G-code for a 3-axis CNC router:
    - 2.0 mm flat endmill
    - Inner distance = 105.0 mm
    - Hole 1: X = 6.0 mm, Y = 4.0 mm
    - Hole 2: X = 114.0 mm, Y = 4.0 mm
    - 2 passes at 1.1 mm depth each = Z -2.2 mm total depth (breakthrough into spoilboard)
    """
    r_tool = tool_dia / 2.0
    feed_cut = 600.0     # mm/min
    feed_plunge = 150.0  # mm/min
    safe_z = 5.0         # mm above material
    cut_depth = plate_thick + 0.2  # 2.2 mm total
    pass_depth = 1.1     # 2 passes
    center_y = width / 2.0
    
    pitch = inner_dist + hole_dia
    hole_offset = (length - pitch) / 2.0  # 6.0 mm
    left_x = hole_offset                  # 6.0 mm
    right_x = length - hole_offset        # 114.0 mm
    
    hole_orbit_r = (hole_dia - tool_dia) / 2.0 # 0.5 mm
    
    gcode = []
    gcode.append("( ========================================================== )")
    gcode.append(f"( M.I.N.E.R.S. ROVER - CNC LINK PLATE 120x8x{plate_thick}mm )")
    gcode.append(f"( INNER HOLE CLEARANCE: {inner_dist}mm | PITCH: {pitch}mm )")
    gcode.append(f"( TOOL: {tool_dia}mm Flat Endmill | UNITS: MM )")
    gcode.append(f"( STOCK THICKNESS: {plate_thick}mm | TOTAL CUT DEPTH: -{cut_depth}mm )")
    gcode.append("( ========================================================== )")
    gcode.append("G21          (Units in Millimeters)")
    gcode.append("G90          (Absolute Positioning)")
    gcode.append("G17          (XY Plane Selection)")
    gcode.append("G94          (Feed per minute)")
    gcode.append("M03 S12000   (Spindle On 12000 RPM)")
    gcode.append(f"G00 Z{safe_z:.2f}    (Safe Clearance Height)")
    gcode.append("")
    
    # 1. BORE 3.0MM HOLES FIRST
    gcode.append("( --- OPERATION 1: BORE 3.0MM HOLES --- )")
    for hole_idx, hx in enumerate([left_x, right_x], start=1):
        gcode.append(f"( Hole {hole_idx} at X={hx:.3f}, Y={center_y:.3f} )")
        gcode.append(f"G00 X{hx:.3f} Y{center_y:.3f}")
        gcode.append("G00 Z1.000")
        
        curr_z = 0.0
        while curr_z < cut_depth:
            curr_z = min(curr_z + pass_depth, cut_depth)
            gcode.append(f"G01 Z-{curr_z:.3f} F{feed_plunge:.0f}")
            if hole_orbit_r > 0.01:
                gcode.append(f"G01 X{hx + hole_orbit_r:.3f} Y{center_y:.3f} F{feed_cut:.0f}")
                gcode.append(f"G02 X{hx + hole_orbit_r:.3f} Y{center_y:.3f} I-{hole_orbit_r:.3f} J0.000")
                gcode.append(f"G01 X{hx:.3f} Y{center_y:.3f}")
        gcode.append(f"G00 Z{safe_z:.2f}")
        gcode.append("")
        
    # 2. PROFILE CUT OUTER CONTOUR
    r_ext = (width / 2.0) + r_tool  # 5.0 mm
    y_bot_cut = -r_tool             # -1.0 mm
    y_top_cut = width + r_tool      # 9.0 mm
    x_l_start = width / 2.0         # 4.0 mm
    x_r_end = length - (width / 2.0)# 116.0 mm
    
    gcode.append("( --- OPERATION 2: PROFILE CUT OUTER CONTOUR --- )")
    gcode.append(f"G00 X{x_l_start:.3f} Y{y_bot_cut:.3f}")
    gcode.append("G00 Z1.000")
    
    curr_z = 0.0
    while curr_z < cut_depth:
        curr_z = min(curr_z + pass_depth, cut_depth)
        gcode.append(f"( Pass at Z = -{curr_z:.3f} mm )")
        gcode.append(f"G01 Z-{curr_z:.3f} F{feed_plunge:.0f}")
        gcode.append(f"G01 X{x_r_end:.3f} Y{y_bot_cut:.3f} F{feed_cut:.0f}")
        gcode.append(f"G03 X{x_r_end:.3f} Y{y_top_cut:.3f} I0.000 J{r_ext:.3f}")
        gcode.append(f"G01 X{x_l_start:.3f} Y{y_top_cut:.3f}")
        gcode.append(f"G03 X{x_l_start:.3f} Y{y_bot_cut:.3f} I0.000 J-{r_ext:.3f}")
        
    gcode.append(f"G00 Z{safe_z:.2f}")
    gcode.append("M05          (Spindle Stop)")
    gcode.append("G00 X0 Y0    (Return to Origin Home)")
    gcode.append("M30          (End of Program)")
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n".join(gcode))
    print(f"Saved CNC G-code: {filename}")

if __name__ == '__main__':
    art_dir = r'C:\Users\sanja\.gemini\antigravity-ide\brain\4fb4b155-d4bd-49ab-b212-b5b5c38b8f10'
    
    # 1. Update Primary DXFs with Inner Distance = 105.0 mm (Pitch = 108.0 mm)
    create_dxf_r2000(r'e:\miners\link_plate_120x8mm.dxf', length=120.0, width=8.0, hole_dia=3.0, inner_dist=105.0)
    create_dxf_r12(r'e:\miners\link_plate_120x8mm_R12.dxf', length=120.0, width=8.0, hole_dia=3.0, inner_dist=105.0)
    
    # 2. Update SVG
    create_svg(r'e:\miners\link_plate_120x8mm.svg', length=120.0, width=8.0, hole_dia=3.0, inner_dist=105.0)
    
    # 3. Update PNG Preview
    create_preview_png(r'e:\miners\link_plate_120x8mm_preview.png', length=120.0, width=8.0, hole_dia=3.0, inner_dist=105.0)
    create_preview_png(os.path.join(art_dir, 'link_plate_120x8mm_preview.png'), length=120.0, width=8.0, hole_dia=3.0, inner_dist=105.0)
    
    # 4. Update CNC Router G-code
    generate_gcode(r'e:\miners\link_plate_120x8mm_cnc_cut.nc', length=120.0, width=8.0, hole_dia=3.0, inner_dist=105.0, plate_thick=2.0, tool_dia=2.0)
    
    # Copy all to artifact directory
    for fname in ['link_plate_120x8mm.dxf', 'link_plate_120x8mm_R12.dxf', 'link_plate_120x8mm.svg', 'link_plate_120x8mm_cnc_cut.nc']:
        shutil.copy2(os.path.join(r'e:\miners', fname), os.path.join(art_dir, fname))
        print(f"Synced {fname} to artifacts.")
        
    print("\nALL FILES UPDATED WITH INNER DISTANCE = 105.0 MM (10.5 CM)!")
