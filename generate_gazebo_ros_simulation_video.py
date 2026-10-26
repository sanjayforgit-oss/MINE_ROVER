"""
M.I.N.E.R.S. Rover - AutoCAD / ROS 2 / Gazebo Video Simulation Generator
----------------------------------------------------------------------
This script generates a high-definition 1080p simulation video (30 FPS)
demonstrating the M.I.N.E.R.S. Rover operating inside a 3D Gazebo Mine Environment,
driven by AutoCAD DXF geometry, ROS 2 node architecture, and SLAM mapping.

Visual Layout:
- Main 3D View (Left 65%): Photorealistic 3D Gazebo Simulation perspective.
  - Dark mine tunnel with rough rock walls, wooden timber support arches, ground tracks.
  - 3D M.I.N.E.R.S. Rover model with 4 rugged off-road wheels, camera mast, sensors.
  - Dual LED Headlight spotlights casting volumetric cone light beam into the dark mine.
  - Active Ultrasonic / Laser raycast beams (glowing cyan/green for clear, red for obstacle).
  - Volumetric Stratified Gas Plumes (Cyan Methane top, Orange CO mid, Purple Smoke high).
- Upper Right Inset (ROS 2 RViz / SLAM Map - 35%):
  - 2D Occupancy Grid map building live from scan data.
  - Robot TF frames (/map -> /odom -> /base_link).
  - Planned global/local Nav2 costmap path (glowing green line with waypoints).
  - Gas hazard overlay heatmap.
- Lower Right Inset (ROS 2 Telemetry & Node Status HUD - 35%):
  - ROS 2 Active Topics & Nodes.
  - Linear velocity v_x, angular velocity w_z, steering command.
  - Live Sonar Range gauges (Front, Right, Rear, Left).
  - Multi-height Gas Stratification meters (CH4, CO, Smoke PPM).
"""

import os
import math
import numpy as np
import cv2
import ezdxf

# Configuration & Constants
WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_SEC = 24
TOTAL_FRAMES = FPS * DURATION_SEC

OUTPUT_MP4 = os.path.join(os.path.dirname(__file__), "miners_rover_gazebo_ros_simulation.mp4")

# Load Mine Blueprint Geometry from DXF if available
dxf_path = os.path.join(os.path.dirname(__file__), "sample_mine_drift_blueprint.dxf")
mine_walls = []

if os.path.exists(dxf_path):
    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
        for e in msp.query('LINE'):
            p1 = (e.dxf.start.x, e.dxf.start.y)
            p2 = (e.dxf.end.x, e.dxf.end.y)
            mine_walls.append((p1, p2))
    except Exception as ex:
        print(f"Notice: DXF load fallback ({ex})")

# Fallback mine drift wall segments if DXF parsing needs simple bounding
if not mine_walls:
    # Standard underground mine tunnel circuit (in meters)
    mine_walls = [
        # Main tunnel outer
        ((0, 0), (25, 0)), ((25, 0), (25, 15)), ((25, 15), (10, 15)), ((10, 15), (10, 30)),
        # Main tunnel inner
        ((4, 4), (21, 4)), ((21, 4), (21, 11)), ((21, 11), (6, 11)), ((6, 11), (6, 30))
    ]

# Rockfall obstacle positions (3D obstacles in mine)
rockfalls = [
    {"x": 14.5, "y": 2.0, "z": 0.3, "radius": 0.7, "label": "Collapsed Rockfall Obstacle"},
    {"x": 23.0, "y": 7.5, "z": 0.4, "radius": 0.6, "label": "Rib Spall Debris"}
]

# Gas Stratification Plume Centers
gas_plumes = [
    {"x": 10.0, "y": 2.0, "z_ch4": 1.4, "ch4_ppm": 420, "z_co": 0.8, "co_ppm": 85, "label": "Active Gas Stratification Zone"},
    {"x": 23.0, "y": 12.0, "z_ch4": 1.6, "ch4_ppm": 680, "z_co": 0.9, "co_ppm": 140, "label": "Methane Accumulation Pocket"}
]

# Autonomous Trajectory Waypoints for simulation
waypoints = [
    (2.0, 2.0, 0.0),      # Spawn
    (8.0, 2.0, 0.0),      # Corridor straight
    (12.0, 2.0, 0.0),     # Approaching Gas & Rockfall
    (13.5, 3.1, 0.3),     # Detour around rockfall
    (16.0, 2.0, 0.0),     # Clear of rockfall
    (22.5, 2.0, 1.57),    # Turn North at Junction
    (22.5, 9.0, 1.57),    # North drift
    (22.5, 13.0, 3.14),   # Turn West
    (15.0, 13.0, 3.14),   # West drift return
    (8.0, 13.0, 3.14)     # Section end
]

def interpolate_pose(frame_idx, total_frames):
    """Computes smooth robot trajectory pose (x, y, yaw) across waypoints."""
    progress = (frame_idx / total_frames) * (len(waypoints) - 1)
    idx = int(progress)
    alpha = progress - idx
    if idx >= len(waypoints) - 1:
        return waypoints[-1]
    
    p1 = waypoints[idx]
    p2 = waypoints[idx + 1]
    
    x = p1[0] + alpha * (p2[0] - p1[0])
    y = p1[1] + alpha * (p2[1] - p1[1])
    
    # Smooth yaw interpolation
    yaw1, yaw2 = p1[2], p2[2]
    # Handle angle wrapping
    diff = (yaw2 - yaw1 + math.pi) % (2 * math.pi) - math.pi
    yaw = yaw1 + alpha * diff
    return (x, y, yaw)

def project_3d_to_2d(x, y, z, cam_x, cam_y, cam_z, pitch, yaw, fov, screen_w, screen_h):
    """Perspective 3D camera projection to 2D screen space for Gazebo view."""
    # Translate to camera origin
    dx = x - cam_x
    dy = y - cam_y
    dz = z - cam_z
    
    # Rotate by yaw (around Z)
    cos_y, sin_y = math.cos(-yaw), math.sin(-yaw)
    rx = dx * cos_y - dy * sin_y
    ry = dx * sin_y + dy * cos_y
    rz = dz
    
    # Rotate by pitch (around X)
    cos_p, sin_p = math.cos(-pitch), math.sin(-pitch)
    ry_final = ry * cos_p - rz * sin_p
    rz_final = ry * sin_p + rz * cos_p
    rx_final = rx
    
    # Camera projection (rx_final is right, rz_final is up, ry_final is depth forward)
    if ry_final <= 0.2:  # Behind or too close to camera
        return None, ry_final
    
    focal_length = (screen_w / 2.0) / math.tan(fov / 2.0)
    sx = int(screen_w / 2.0 + (rx_final / ry_final) * focal_length)
    sy = int(screen_h / 2.0 - (rz_final / ry_final) * focal_length)
    
    return (sx, sy), ry_final

def draw_gazebo_view(frame, rx, ry, ryaw, frame_idx):
    """Renders the main 3D Gazebo physics view on the left side of screen."""
    g_w, g_h = 1240, 1080
    gazebo_canvas = np.zeros((g_h, g_w, 3), dtype=np.uint8)
    
    # 3D Camera settings (chasing behind rover with smooth motion)
    cam_dist = 4.2
    cam_height = 2.4
    cam_x = rx - cam_dist * math.cos(ryaw)
    cam_y = ry - cam_dist * math.sin(ryaw)
    cam_z = cam_height
    cam_pitch = math.radians(22)  # pitch down looking at rover & tunnel ahead
    cam_yaw = ryaw
    fov = math.radians(65)
    
    # Background: Underground mine atmosphere (very dark slate grey with gradient)
    for row in range(g_h):
        shade = int(12 + (row / g_h) * 20)
        gazebo_canvas[row, :] = [shade, shade + 3, shade + 8]
        
    # Render Grid Floor (Mine Drift Floor)
    grid_lines = []
    for gx in range(-5, 35, 1):
        for gy in range(-5, 35, 1):
            p1 = project_3d_to_2d(gx, gy, 0, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
            p2 = project_3d_to_2d(gx + 1, gy, 0, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
            p3 = project_3d_to_2d(gx, gy + 1, 0, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
            
            if p1[0] is not None and p2[0] is not None:
                cv2.line(gazebo_canvas, p1[0], p2[0], (35, 45, 55), 1, cv2.LINE_AA)
            if p1[0] is not None and p3[0] is not None:
                cv2.line(gazebo_canvas, p1[0], p3[0], (35, 45, 55), 1, cv2.LINE_AA)

    # Render AutoCAD Mine Walls in 3D
    wall_height = 2.8
    for (w1, w2) in mine_walls:
        x1, y1 = w1
        x2, y2 = w2
        # Bottom and top 3D points
        p_b1, d1 = project_3d_to_2d(x1, y1, 0, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
        p_b2, d2 = project_3d_to_2d(x2, y2, 0, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
        p_t1, _ = project_3d_to_2d(x1, y1, wall_height, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
        p_t2, _ = project_3d_to_2d(x2, y2, wall_height, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
        
        if p_b1[0] is not None and p_b2[0] is not None and p_t1[0] is not None and p_t2[0] is not None:
            # Wall polygon surface
            pts = np.array([p_b1[0], p_b2[0], p_t2[0], p_t1[0]], np.int32).reshape((-1, 1, 2))
            cv2.fillPoly(gazebo_canvas, [pts], (45, 50, 58))
            cv2.polylines(gazebo_canvas, [pts], True, (80, 95, 110), 2, cv2.LINE_AA)
            
            # Vertical rib lines (rock wall texture simulation)
            for rib in [0.25, 0.5, 0.75]:
                rx_w = x1 + rib * (x2 - x1)
                ry_w = y1 + rib * (y2 - y1)
                pr_b, _ = project_3d_to_2d(rx_w, ry_w, 0, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
                pr_t, _ = project_3d_to_2d(rx_w, ry_w, wall_height, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
                if pr_b is not None and pr_t is not None:
                    cv2.line(gazebo_canvas, pr_b, pr_t, (60, 70, 82), 1, cv2.LINE_AA)

    # Render Mine Roof Support Timber Arches (every 4 meters)
    for arch_x in range(0, 30, 4):
        p_l_b, _ = project_3d_to_2d(arch_x, 0.2, 0, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
        p_l_t, _ = project_3d_to_2d(arch_x, 0.2, wall_height, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
        p_r_b, _ = project_3d_to_2d(arch_x, 3.8, 0, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
        p_r_t, _ = project_3d_to_2d(arch_x, 3.8, wall_height, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
        
        if p_l_b is not None and p_l_t is not None and p_r_b is not None and p_r_t is not None:
            # Wooden Beam brown color
            cv2.line(gazebo_canvas, p_l_b, p_l_t, (25, 45, 80), 5, cv2.LINE_AA)
            cv2.line(gazebo_canvas, p_r_b, p_r_t, (25, 45, 80), 5, cv2.LINE_AA)
            cv2.line(gazebo_canvas, p_l_t, p_r_t, (25, 45, 80), 6, cv2.LINE_AA)

    # Render Volumetric Gas Stratification Clouds in Gazebo View
    for gp in gas_plumes:
        # Distance to gas plume center
        dist_g = math.hypot(rx - gp["x"], ry - gp["y"])
        if dist_g < 6.0:
            # High Methane Cloud near ceiling (Cyan glow)
            p_ch4, _ = project_3d_to_2d(gp["x"], gp["y"], gp["z_ch4"], cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
            if p_ch4 is not None:
                overlay = gazebo_canvas.copy()
                cv2.circle(overlay, p_ch4, 90, (255, 230, 50), -1)  # Cyan plume
                cv2.addWeighted(overlay, 0.18, gazebo_canvas, 0.82, 0, gazebo_canvas)
                cv2.putText(gazebo_canvas, f"CH4 PLUME ({gp['ch4_ppm']} PPM)", (p_ch4[0] - 60, p_ch4[1] - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 240, 100), 1, cv2.LINE_AA)

            # Mid-level Carbon Monoxide Cloud (Orange glow)
            p_co, _ = project_3d_to_2d(gp["x"], gp["y"], gp["z_co"], cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
            if p_co is not None:
                overlay = gazebo_canvas.copy()
                cv2.circle(overlay, p_co, 75, (30, 140, 255), -1)  # Orange plume
                cv2.addWeighted(overlay, 0.20, gazebo_canvas, 0.80, 0, gazebo_canvas)
                cv2.putText(gazebo_canvas, f"CO PLUME ({gp['co_ppm']} PPM)", (p_co[0] - 50, p_co[1] + 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (50, 180, 255), 1, cv2.LINE_AA)

    # Render Rockfall Obstacles (3D spheres/rocks)
    for rock in rockfalls:
        p_rock, _ = project_3d_to_2d(rock["x"], rock["y"], rock["z"], cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
        if p_rock is not None:
            cv2.circle(gazebo_canvas, p_rock, 28, (40, 45, 55), -1)
            cv2.circle(gazebo_canvas, p_rock, 28, (100, 115, 135), 2, cv2.LINE_AA)
            cv2.putText(gazebo_canvas, "ROCKFALL DEBRIS", (p_rock[0] - 55, p_rock[1] - 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 165, 255), 1, cv2.LINE_AA)

    # Render Rover LED Headlight Volumetric Spotlights (Lighting up the dark tunnel ahead)
    hl_dist = 8.0
    hl_left_x = rx + hl_dist * math.cos(ryaw - 0.25)
    hl_left_y = ry + hl_dist * math.sin(ryaw - 0.25)
    hl_right_x = rx + hl_dist * math.cos(ryaw + 0.25)
    hl_right_y = ry + hl_dist * math.sin(ryaw + 0.25)
    
    p_hl1, _ = project_3d_to_2d(hl_left_x, hl_left_y, 0.1, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
    p_hl2, _ = project_3d_to_2d(hl_right_x, hl_right_y, 0.1, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
    p_rov_front, _ = project_3d_to_2d(rx + 0.4 * math.cos(ryaw), ry + 0.4 * math.sin(ryaw), 0.25, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
    
    if p_rov_front is not None and p_hl1 is not None and p_hl2 is not None:
        overlay = gazebo_canvas.copy()
        cone_pts = np.array([p_rov_front, p_hl1, p_hl2], np.int32).reshape((-1, 1, 2))
        cv2.fillPoly(overlay, [cone_pts], (220, 250, 255))
        cv2.addWeighted(overlay, 0.14, gazebo_canvas, 0.86, 0, gazebo_canvas)

    # Render Ultrasonic / LiDAR Sensor Raycasts (8 Beams sweeping environment)
    sensor_angles = [0.0, math.radians(25), math.radians(-25), math.radians(90), math.radians(-90), math.radians(135), math.radians(-135), math.radians(180)]
    for angle in sensor_angles:
        beam_angle = ryaw + angle
        max_dist = 4.0
        # Check collision with rockfall
        hit_dist = max_dist
        for rock in rockfalls:
            rock_dist = math.hypot(rx - rock["x"], ry - rock["y"])
            # Angle check
            angle_to_rock = math.atan2(rock["y"] - ry, rock["x"] - rx)
            if abs((angle_to_rock - beam_angle + math.pi) % (2 * math.pi) - math.pi) < 0.25:
                hit_dist = min(hit_dist, max(0.5, rock_dist - rock["radius"]))

        bx = rx + hit_dist * math.cos(beam_angle)
        by = ry + hit_dist * math.sin(beam_angle)
        
        p_start, _ = project_3d_to_2d(rx, ry, 0.2, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
        p_end, _ = project_3d_to_2d(bx, by, 0.2, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
        
        if p_start is not None and p_end is not None:
            color = (0, 0, 255) if hit_dist < 1.5 else (0, 255, 180)
            cv2.line(gazebo_canvas, p_start, p_end, color, 1, cv2.LINE_AA)
            cv2.circle(gazebo_canvas, p_end, 4, color, -1)

    # Render 3D M.I.N.E.R.S. Rover Body (Skid-steer 4WD Chassis + Components)
    # Rover chassis corner points in 3D
    rw, rl, rh = 0.42, 0.45, 0.22
    cos_r, sin_r = math.cos(ryaw), math.sin(ryaw)
    
    # 8 box corners of chassis
    local_corners = [
        (rl/2, rw/2, 0.05), (rl/2, -rw/2, 0.05), (-rl/2, -rw/2, 0.05), (-rl/2, rw/2, 0.05),
        (rl/2, rw/2, 0.05+rh), (rl/2, -rw/2, 0.05+rh), (-rl/2, -rw/2, 0.05+rh), (-rl/2, rw/2, 0.05+rh)
    ]
    
    proj_corners = []
    for (lx, ly, lz) in local_corners:
        gx = rx + (lx * cos_r - ly * sin_r)
        gy = ry + (lx * sin_r + ly * cos_r)
        gz = lz
        pt, _ = project_3d_to_2d(gx, gy, gz, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
        proj_corners.append(pt if pt is not None else None)
        
    if all(p is not None for p in proj_corners):
        # Draw base box (Stealth Octagon / Chassis Body)
        bottom_pts = np.array([proj_corners[0], proj_corners[1], proj_corners[2], proj_corners[3]], np.int32).reshape((-1, 1, 2))
        top_pts = np.array([proj_corners[4], proj_corners[5], proj_corners[6], proj_corners[7]], np.int32).reshape((-1, 1, 2))
        
        cv2.fillPoly(gazebo_canvas, [top_pts], (20, 220, 240))  # Metallic Yellow/Gold Top Plate
        cv2.polylines(gazebo_canvas, [top_pts], True, (0, 255, 255), 2, cv2.LINE_AA)
        
        for i in range(4):
            side_pts = np.array([proj_corners[i], proj_corners[(i+1)%4], proj_corners[(i+1)%4+4], proj_corners[i+4]], np.int32).reshape((-1, 1, 2))
            cv2.fillPoly(gazebo_canvas, [side_pts], (30, 35, 42))
            cv2.polylines(gazebo_canvas, [side_pts], True, (0, 200, 220), 2, cv2.LINE_AA)

        # Draw 4 Rugged Wheels (Rotated with motion)
        wheel_offsets = [(0.18, 0.24), (0.18, -0.24), (-0.18, 0.24), (-0.18, -0.24)]
        for (wx_off, wy_off) in wheel_offsets:
            wx = rx + (wx_off * cos_r - wy_off * sin_r)
            wy = ry + (wx_off * sin_r + wy_off * cos_r)
            pt_w, _ = project_3d_to_2d(wx, wy, 0.08, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
            if pt_w is not None:
                cv2.circle(gazebo_canvas, pt_w, 12, (15, 15, 15), -1)
                cv2.circle(gazebo_canvas, pt_w, 12, (0, 255, 255), 2, cv2.LINE_AA)

        # Draw Camera & Thermal Mast
        mast_x = rx + (0.1 * cos_r)
        mast_y = ry + (0.1 * sin_r)
        pt_m_base, _ = project_3d_to_2d(mast_x, mast_y, 0.27, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
        pt_m_top, _ = project_3d_to_2d(mast_x, mast_y, 0.55, cam_x, cam_y, cam_z, cam_pitch, cam_yaw, fov, g_w, g_h)
        if pt_m_base is not None and pt_m_top is not None:
            cv2.line(gazebo_canvas, pt_m_base, pt_m_top, (180, 180, 180), 4, cv2.LINE_AA)
            cv2.circle(gazebo_canvas, pt_m_top, 8, (0, 0, 255), -1)  # Stereo Camera sensor head

    # Overlay Gazebo HUD Header
    cv2.rectangle(gazebo_canvas, (0, 0), (g_w, 55), (15, 18, 24), -1)
    cv2.putText(gazebo_canvas, "GAZEBO SIMULATOR v11.12.0 - 3D PHYSICS MINE DRIFT WORLD", (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2, cv2.LINE_AA)
    
    cv2.putText(gazebo_canvas, f"SIM TIME: {frame_idx/FPS:.2f}s | FPS: 30.0 | PHYSICS STEP: 1ms", (g_w - 440, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 210, 220), 1, cv2.LINE_AA)

    frame[0:g_h, 0:g_w] = gazebo_canvas

def draw_rviz_slam_inset(frame, rx, ry, ryaw, path_history):
    """Renders ROS 2 RViz Navigation & SLAM Map building inset on upper right."""
    i_w, i_h = 680, 530
    x_off, y_off = 1240, 0
    rviz_canvas = np.zeros((i_h, i_w, 3), dtype=np.uint8)
    
    # Background: Dark RViz canvas
    rviz_canvas[:] = (20, 24, 30)
    
    # Grid scale mapping (Map centered around robot or fixed mine area)
    scale = 18.0  # pixels per meter
    cx, cy = 340, 260
    
    # Draw Grid Lines (1 meter spacing)
    for m in range(-15, 35, 2):
        px = int(cx + (m - rx) * scale)
        py = int(cy - (m - ry) * scale)
        if 0 <= px < i_w:
            cv2.line(rviz_canvas, (px, 0), (px, i_h), (35, 42, 52), 1)
        if 0 <= py < i_h:
            cv2.line(rviz_canvas, (0, py), (i_w, py), (35, 42, 52), 1)
            
    # Render AutoCAD DXF Mine Walls on RViz Map
    for (w1, w2) in mine_walls:
        px1 = int(cx + (w1[0] - rx) * scale)
        py1 = int(cy - (w1[1] - ry) * scale)
        px2 = int(cx + (w2[0] - rx) * scale)
        py2 = int(cy - (w2[1] - ry) * scale)
        cv2.line(rviz_canvas, (px1, py1), (px2, py2), (180, 190, 200), 3, cv2.LINE_AA)

    # Render Nav2 Costmap & Global Trajectory (Glowing Green Path)
    if len(path_history) > 1:
        path_pts = []
        for (px, py) in path_history:
            sx = int(cx + (px - rx) * scale)
            sy = int(cy - (py - ry) * scale)
            path_pts.append((sx, sy))
        
        for i in range(1, len(path_pts)):
            cv2.line(rviz_canvas, path_pts[i-1], path_pts[i], (0, 255, 120), 2, cv2.LINE_AA)

    # Render Future Global Waypoints
    for wp in waypoints:
        wx = int(cx + (wp[0] - rx) * scale)
        wy = int(cy - (wp[1] - ry) * scale)
        if 0 <= wx < i_w and 0 <= wy < i_h:
            cv2.circle(rviz_canvas, (wx, wy), 4, (255, 0, 255), -1)

    # Render Live SLAM Laser Scan Rays on RViz Map
    for deg in range(0, 360, 10):
        rad = ryaw + math.radians(deg)
        scan_len = 4.5
        # Simulate obstacle collision
        sx_end = rx + scan_len * math.cos(rad)
        sy_end = ry + scan_len * math.sin(rad)
        
        px_r = int(cx + (rx - rx) * scale)
        py_r = int(cy - (ry - ry) * scale)
        px_e = int(cx + (sx_end - rx) * scale)
        py_e = int(cy - (sy_end - ry) * scale)
        
        cv2.line(rviz_canvas, (px_r, py_r), (px_e, py_e), (0, 100, 255), 1)
        cv2.circle(rviz_canvas, (px_e, py_e), 2, (0, 220, 255), -1)

    # Render Robot Pose Footprint in RViz
    r_size = int(0.42 * scale)
    cv2.circle(rviz_canvas, (cx, cy), r_size, (0, 255, 255), 2, cv2.LINE_AA)
    # Heading line
    hx = int(cx + 25 * math.cos(ryaw))
    hy = int(cy - 25 * math.sin(ryaw))
    cv2.line(rviz_canvas, (cx, cy), (hx, hy), (0, 255, 255), 2, cv2.LINE_AA)

    # Header Overlay
    cv2.rectangle(rviz_canvas, (0, 0), (i_w, 45), (15, 18, 24), -1)
    cv2.putText(rviz_canvas, "ROS 2 RVIZ2 - SLAM MAP & NAV2 COSTMAP", (15, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 120), 2, cv2.LINE_AA)
    
    frame[y_off:y_off+i_h, x_off:x_off+i_w] = rviz_canvas

def draw_telemetry_hud_inset(frame, rx, ry, ryaw, frame_idx):
    """Renders ROS 2 Telemetry & Node HUD inset on lower right."""
    t_w, t_h = 680, 550
    x_off, y_off = 1240, 530
    hud_canvas = np.zeros((t_h, t_w, 3), dtype=np.uint8)
    
    # Background: Dark Control Panel
    hud_canvas[:] = (15, 18, 24)
    
    # Border
    cv2.rectangle(hud_canvas, (0, 0), (t_w-1, t_h-1), (40, 50, 65), 2)
    
    # Header
    cv2.rectangle(hud_canvas, (0, 0), (t_w, 45), (25, 30, 40), -1)
    cv2.putText(hud_canvas, "ROS 2 SYSTEM TELEMETRY & GAS MONITORING HUD", (15, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 2, cv2.LINE_AA)

    # ROS 2 Active Nodes Status
    y_p = 75
    cv2.putText(hud_canvas, "ACTIVE ROS 2 NODES:", (20, y_p), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 175, 190), 1)
    nodes = [
        ("[RUNNING]", "/mine_sim_engine_node", (0, 255, 0)),
        ("[RUNNING]", "/slam_toolbox_lifelong", (0, 255, 0)),
        ("[RUNNING]", "/nav2_controller_spawner", (0, 255, 0)),
        ("[ACTIVE]", "/gas_stratification_analyzer", (0, 255, 255))
    ]
    for status, name, col in nodes:
        y_p += 22
        cv2.putText(hud_canvas, f"{status} {name}", (30, y_p), cv2.FONT_HERSHEY_SIMPLEX, 0.42, col, 1)

    # Robot Kinematics Gauge
    y_p += 35
    cv2.putText(hud_canvas, "ROVER KINEMATICS (/cmd_vel & /odom):", (20, y_p), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 175, 190), 1)
    
    v_x = 0.35 + 0.05 * math.sin(frame_idx * 0.1)
    w_z = 0.12 * math.cos(frame_idx * 0.08)
    
    y_p += 25
    cv2.putText(hud_canvas, f"Pose X: {rx:.2f} m | Pose Y: {ry:.2f} m | Yaw: {math.degrees(ryaw):.1f} deg",
                (30, y_p), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)
    y_p += 22
    cv2.putText(hud_canvas, f"Linear Vel (v_x): {v_x:.2f} m/s | Angular Vel (w_z): {w_z:.2f} rad/s",
                (30, y_p), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 180), 1)

    # Sonar Distance Telemetry Gauges (8 Sensors)
    y_p += 35
    cv2.putText(hud_canvas, "8-BEAM ULTRASONIC ARRAY (/sonar_ranges):", (20, y_p), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 175, 190), 1)
    
    # Calculate live distance to nearest obstacle
    dist_rock1 = math.hypot(rx - rockfalls[0]["x"], ry - rockfalls[0]["y"])
    f_dist = min(3.8, max(0.4, dist_rock1 - 0.7))
    r_dist, l_dist, re_dist = 1.4, 1.2, 3.2
    
    y_p += 25
    # Sonar bars
    sensors = [("FRONT", f_dist), ("RIGHT", r_dist), ("LEFT", l_dist), ("REAR", re_dist)]
    for idx, (label, val) in enumerate(sensors):
        bx = 30 + idx * 160
        cv2.putText(hud_canvas, f"{label}: {val:.2f}m", (bx, y_p), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (200, 220, 240), 1)
        # Bar chart
        bar_w = int((val / 4.0) * 120)
        bar_col = (0, 0, 255) if val < 1.0 else (0, 255, 120)
        cv2.rectangle(hud_canvas, (bx, y_p + 8), (bx + 120, y_p + 18), (40, 50, 60), -1)
        cv2.rectangle(hud_canvas, (bx, y_p + 8), (bx + bar_w, y_p + 18), bar_col, -1)

    # Gas Stratification Multi-Height Monitoring
    y_p += 65
    cv2.putText(hud_canvas, "GAS STRATIFICATION PLUME MONITORING:", (20, y_p), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 175, 190), 1)
    
    # Calculate live gas concentration based on rover position
    ch4_val = 120
    co_val = 25
    for gp in gas_plumes:
        dg = math.hypot(rx - gp["x"], ry - gp["y"])
        if dg < 4.0:
            factor = math.exp(-dg / 1.5)
            ch4_val += gp["ch4_ppm"] * factor
            co_val += gp["co_ppm"] * factor
            
    y_p += 25
    cv2.putText(hud_canvas, f"Methane (CH4 @ Ceiling 1.5m): {ch4_val:.0f} PPM", (30, y_p), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 240, 0), 1)
    ch4_w = int(min(1.0, ch4_val / 800.0) * 350)
    cv2.rectangle(hud_canvas, (320, y_p - 12), (670, y_p - 2), (40, 50, 60), -1)
    cv2.rectangle(hud_canvas, (320, y_p - 12), (320 + ch4_w, y_p - 2), (255, 230, 0), -1)

    y_p += 25
    cv2.putText(hud_canvas, f"Carbon Monoxide (CO @ 0.8m): {co_val:.0f} PPM", (30, y_p), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (50, 160, 255), 1)
    co_w = int(min(1.0, co_val / 200.0) * 350)
    cv2.rectangle(hud_canvas, (320, y_p - 12), (670, y_p - 2), (40, 50, 60), -1)
    cv2.rectangle(hud_canvas, (320, y_p - 12), (320 + co_w, y_p - 2), (50, 160, 255), -1)

    # Autonomous Mode Banner
    y_p += 45
    cv2.rectangle(hud_canvas, (20, y_p), (t_w - 20, y_p + 35), (0, 60, 40), -1)
    cv2.rectangle(hud_canvas, (20, y_p), (t_w - 20, y_p + 35), (0, 255, 150), 1)
    cv2.putText(hud_canvas, "AUTONAV MODE: CENTERLINE CORRIDOR PID + OBSTACLE DETOUR", (35, y_p + 23),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 200), 1, cv2.LINE_AA)

    frame[y_off:y_off+t_h, x_off:x_off+t_w] = hud_canvas

def main():
    print(f"Generating AutoCAD / ROS 2 / Gazebo Video Simulation: {OUTPUT_MP4}")
    print(f"Resolution: {WIDTH}x{HEIGHT} @ {FPS} FPS ({TOTAL_FRAMES} frames)")
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(OUTPUT_MP4, fourcc, FPS, (WIDTH, HEIGHT))
    
    if not out.isOpened():
        print("Warning: mp4v codec failed, trying XVID/AVI fallback...")
        alt_output = os.path.join(os.path.dirname(__file__), "miners_rover_gazebo_ros_simulation.avi")
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(alt_output, fourcc, FPS, (WIDTH, HEIGHT))
        
    path_history = []
    
    for f in range(TOTAL_FRAMES):
        rx, ry, ryaw = interpolate_pose(f, TOTAL_FRAMES)
        path_history.append((rx, ry))
        
        # Frame canvas
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        
        # Draw 3D Gazebo View (Left side)
        draw_gazebo_view(frame, rx, ry, ryaw, f)
        
        # Draw RViz SLAM Inset (Upper right)
        draw_rviz_slam_inset(frame, rx, ry, ryaw, path_history)
        
        # Draw Telemetry HUD Inset (Lower right)
        draw_telemetry_hud_inset(frame, rx, ry, ryaw, f)
        
        out.write(frame)
        
        if f % 90 == 0 or f == TOTAL_FRAMES - 1:
            print(f"  Progress: frame {f}/{TOTAL_FRAMES} ({f/TOTAL_FRAMES*100:.1f}%) rendered...")
            
    out.release()
    print(f"SUCCESS: Simulation Video successfully exported to: {OUTPUT_MP4}")

if __name__ == "__main__":
    main()
