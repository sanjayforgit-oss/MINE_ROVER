import math
import numpy as np
import time
from PIL import Image

class LiveSonarSLAM:
    """
    Log-Odds 2D Occupancy Grid SLAM & Gas Heatmap Mapper
    Designed for 4-direction dual ultrasonic sensors & dead reckoning wheel odometry.
    """
    def __init__(self, map_width_m=20.0, map_height_m=20.0, resolution_m=0.05):
        self.resolution = resolution_m # 5 cm per cell
        self.width_m = map_width_m
        self.height_m = map_height_m
        self.grid_w = int(map_width_m / resolution_m) # 400 cells
        self.grid_h = int(map_height_m / resolution_m) # 400 cells
        
        # Origin at center of map (meters)
        self.origin_x = map_width_m / 2.0
        self.origin_y = map_height_m / 2.0
        
        # Log-odds occupancy grid: 0 = Unknown (p=0.5), <0 = Free space, >0 = Occupied
        self.log_odds = np.zeros((self.grid_h, self.grid_w), dtype=np.float32)
        
        # Gas Heatmap Grids: stores peak ADC readings (0-1023)
        self.gas_ch4 = np.zeros((self.grid_h, self.grid_w), dtype=np.float32)
        self.gas_co  = np.zeros((self.grid_h, self.grid_w), dtype=np.float32)
        self.gas_mq2 = np.zeros((self.grid_h, self.grid_w), dtype=np.float32)
        
        # Log-odds update constants
        self.L_OCC = 0.85   # Probability when beam hits wall
        self.L_FREE = -0.40 # Probability for empty space along beam
        self.L_MAX = 3.5    # Clamping limits
        self.L_MIN = -3.5
        
        # Rover Pose: (x, y) in meters, theta in radians (0 = Facing North/Up)
        self.x = 0.0
        self.y = 0.0
        self.theta = math.pi / 2.0 # Facing Up
        self.trajectory = [] # List of (x, y) history
        self.last_update_time = time.time()
        
        # Estimated speed & turn rates for kinematic dead-reckoning
        self.linear_speed = 0.35 # m/s at 255 PWM
        self.angular_speed = 1.60 # rad/s (~90 deg/sec)
        
    def reset(self):
        self.log_odds.fill(0.0)
        self.gas_ch4.fill(0.0)
        self.gas_co.fill(0.0)
        self.gas_mq2.fill(0.0)
        self.x = 0.0
        self.y = 0.0
        self.theta = math.pi / 2.0
        self.trajectory = [(0.0, 0.0)]
        self.last_update_time = time.time()

    def update_odometry(self, motion_char, dt=None):
        now = time.time()
        if dt is None:
            dt = now - self.last_update_time
            self.last_update_time = now
        dt = min(max(dt, 0.01), 0.5) # clamp delta time
        
        if motion_char == 'F':
            self.x += self.linear_speed * dt * math.cos(self.theta)
            self.y += self.linear_speed * dt * math.sin(self.theta)
        elif motion_char == 'B':
            self.x -= self.linear_speed * dt * math.cos(self.theta)
            self.y -= self.linear_speed * dt * math.sin(self.theta)
        elif motion_char == 'L':
            self.theta += self.angular_speed * dt
        elif motion_char == 'R':
            self.theta -= self.angular_speed * dt
            
        # Normalize theta to [-pi, pi]
        self.theta = (self.theta + math.pi) % (2 * math.pi) - math.pi
        
        # Record trajectory (sample every 10cm or turn)
        if not self.trajectory or math.hypot(self.x - self.trajectory[-1][0], self.y - self.trajectory[-1][1]) > 0.08:
            self.trajectory.append((self.x, self.y))
            if len(self.trajectory) > 1000:
                self.trajectory.pop(0)

    def world_to_grid(self, wx, wy):
        gx = int((wx + self.origin_x) / self.resolution)
        gy = int((wy + self.origin_y) / self.resolution)
        return gx, gy

    def grid_to_world(self, gx, gy):
        wx = (gx * self.resolution) - self.origin_x
        wy = (gy * self.resolution) - self.origin_y
        return wx, wy

    def bresenham_line(self, x0, y0, x1, y1):
        """Bresenham's line algorithm for raycasting free space."""
        points = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        curr_x, curr_y = x0, y0
        while True:
            points.append((curr_x, curr_y))
            if curr_x == x1 and curr_y == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                curr_x += sx
            if e2 < dx:
                err += dx
                curr_y += sy
        return points

    def update_sensors(self, sonar_dict, gas_dict, motion_char='S'):
        self.update_odometry(motion_char)
        
        # 1. Update Sonar Beams
        # Directions and their relative angles from rover heading (theta)
        # Front = 0, Right = -pi/2, Rear = pi, Left = +pi/2
        beam_definitions = [
            ("FRONT", sonar_dict.get("F", 100), 0.0),
            ("RIGHT", sonar_dict.get("R", 100), -math.pi / 2.0),
            ("REAR",  sonar_dict.get("B", 100), math.pi),
            ("LEFT",  sonar_dict.get("L", 100), math.pi / 2.0),
        ]
        
        # If individual dual beams exist, process them with realistic slight angular offset
        if "F1" in sonar_dict and "F2" in sonar_dict:
            beam_definitions = [
                ("F1", sonar_dict.get("F1", 100), math.radians(12)),
                ("F2", sonar_dict.get("F2", 100), -math.radians(12)),
                ("R1", sonar_dict.get("R1", 100), -math.pi / 2.0 + math.radians(12)),
                ("R2", sonar_dict.get("R2", 100), -math.pi / 2.0 - math.radians(12)),
                ("B1", sonar_dict.get("B1", 100), math.pi - math.radians(12)),
                ("B2", sonar_dict.get("B2", 100), math.pi + math.radians(12)),
                ("L1", sonar_dict.get("L1", 100), math.pi / 2.0 + math.radians(12)),
                ("L2", sonar_dict.get("L2", 100), math.pi / 2.0 - math.radians(12)),
            ]

        rx_grid, ry_grid = self.world_to_grid(self.x, self.y)
        
        for name, dist_cm, rel_angle in beam_definitions:
            dist_m = dist_cm / 100.0
            if dist_m < 0.04: continue # Ignore noise
            
            # Max valid range 2.5m
            is_obstacle = (dist_m <= 2.2)
            scan_dist = min(dist_m, 2.2)
            
            beam_angle = self.theta + rel_angle
            end_wx = self.x + scan_dist * math.cos(beam_angle)
            end_wy = self.y + scan_dist * math.sin(beam_angle)
            end_gx, end_gy = self.world_to_grid(end_wx, end_wy)
            
            # Raycast free cells along line
            line_cells = self.bresenham_line(rx_grid, ry_grid, end_gx, end_gy)
            
            for cx, cy in line_cells[:-1]:
                if 0 <= cx < self.grid_w and 0 <= cy < self.grid_h:
                    self.log_odds[cy, cx] = max(self.log_odds[cy, cx] + self.L_FREE, self.L_MIN)
                    
            # Mark obstacle cell if within range
            if is_obstacle and len(line_cells) > 0:
                ox, oy = line_cells[-1]
                if 0 <= ox < self.grid_w and 0 <= oy < self.grid_h:
                    self.log_odds[oy, ox] = min(self.log_odds[oy, ox] + self.L_OCC, self.L_MAX)
                    
        # 2. Update Gas Heatmap at current position
        if 0 <= rx_grid < self.grid_w and 0 <= ry_grid < self.grid_h:
            mq4 = gas_dict.get("mq4", 0)
            mq7 = gas_dict.get("mq7", 0)
            mq2 = gas_dict.get("mq2", 0)
            
            # Gas dispersion radius ~3 cells (15 cm)
            r = 3
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    gx, gy = rx_grid + dx, ry_grid + dy
                    if 0 <= gx < self.grid_w and 0 <= gy < self.grid_h:
                        dist_sq = dx*dx + dy*dy
                        if dist_sq <= r*r:
                            weight = 1.0 - (math.sqrt(dist_sq) / (r + 1))
                            self.gas_ch4[gy, gx] = max(self.gas_ch4[gy, gx], mq4 * weight)
                            self.gas_co[gy, gx]  = max(self.gas_co[gy, gx], mq7 * weight)
                            self.gas_mq2[gy, gx] = max(self.gas_mq2[gy, gx], mq2 * weight)

    def get_probability_map(self):
        """Converts log-odds to standard probability [0.0 (free) to 1.0 (occupied)]."""
        # p = 1 - 1 / (1 + exp(L))
        prob = 1.0 - 1.0 / (1.0 + np.exp(self.log_odds))
        return prob

    def render_map_image(self, target_w=500, target_h=500, show_gas_layer=True):
        """Renders an RGB NumPy image of the map for GUI display."""
        # 1. Base Map: Unknown = #1e293b (Dark Slate), Free = #f8fafc (White), Wall = #0f172a (Black)
        prob = self.get_probability_map()
        
        # Color initialization: Dark Slate for Unknown
        img_rgb = np.zeros((self.grid_h, self.grid_w, 3), dtype=np.uint8)
        img_rgb[:, :] = [30, 41, 59] # #1e293b Unknown
        
        # Free space: prob < 0.40 -> Light / Clean Floor (#334155 / #475569)
        free_mask = prob < 0.40
        img_rgb[free_mask] = [71, 85, 105] # Clear tunnel floor
        
        # High confidence free floor
        high_free = prob < 0.20
        img_rgb[high_free] = [100, 116, 139]
        
        # Occupied / Wall: prob > 0.65 -> Bright Cyan / Rock Contour (#38bdf8 / #0284c7)
        wall_mask = prob > 0.65
        img_rgb[wall_mask] = [56, 189, 248] # Cyan rock boundary
        
        # Solid Rock Core: prob > 0.85 -> Bright Amber / Red
        solid_wall = prob > 0.85
        img_rgb[solid_wall] = [239, 68, 68] # Red obstacle
        
        # 2. Gas Plume Layer Overlay (if enabled)
        if show_gas_layer:
            # Highlight Methane (MQ-4) in Green/Yellow and CO in Red
            ch4_mask = self.gas_ch4 > 350
            img_rgb[ch4_mask] = [16, 185, 129] # Green Methane cloud
            
            co_mask = self.gas_co > 300
            img_rgb[co_mask] = [245, 158, 11] # Amber CO plume
            
        # 3. Draw Rover Trajectory (Green Trail)
        for tx, ty in self.trajectory:
            gx, gy = self.world_to_grid(tx, ty)
            if 0 <= gx < self.grid_w and 0 <= gy < self.grid_h:
                img_rgb[gy, gx] = [52, 211, 153] # Emerald Green
                
        # 4. Draw Rover Body & Heading Vector at (x, y)
        rx, ry = self.world_to_grid(self.x, self.y)
        if 0 <= rx < self.grid_w and 0 <= ry < self.grid_h:
            # Rover footprint box (radius 3 cells = 15cm)
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    gx, gy = rx + dx, ry + dy
                    if 0 <= gx < self.grid_w and 0 <= gy < self.grid_h:
                        img_rgb[gy, gx] = [2, 132, 199] # Blue Rover Core
                        
            # Heading Indicator Line (length 7 cells)
            for k in range(1, 8):
                hx = int(rx + k * math.cos(self.theta))
                hy = int(ry + k * math.sin(self.theta))
                if 0 <= hx < self.grid_w and 0 <= hy < self.grid_h:
                    img_rgb[hy, hx] = [255, 255, 255] # White Heading Pointer
                    
        # Invert Y for standard top-left image coordinates
        img_rgb = np.flipud(img_rgb)
        
        # Resize to target display dimensions
        pil_img = Image.fromarray(img_rgb)
        pil_img = pil_img.resize((target_w, target_h), Image.NEAREST)
        return pil_img

    def export_ros2_map(self, base_filepath="e:/miners/mine_slam_map"):
        """Exports the generated map to standard ROS2/Nav2 .yaml + .pgm files."""
        prob = self.get_probability_map()
        # ROS standard: 0 = Free, 100 = Occupied, 255 = Unknown
        ros_grid = np.full(prob.shape, 255, dtype=np.uint8)
        ros_grid[prob < 0.40] = 0   # Free
        ros_grid[prob > 0.65] = 100 # Occupied
        
        # PGM image: 254 (white) = Free, 0 (black) = Occupied, 205 (gray) = Unknown
        pgm_img = np.full(prob.shape, 205, dtype=np.uint8)
        pgm_img[prob < 0.40] = 254
        pgm_img[prob > 0.65] = 0
        pgm_img = np.flipud(pgm_img)
        
        pgm_path = f"{base_filepath}.pgm"
        yaml_path = f"{base_filepath}.yaml"
        
        # Save PGM
        Image.fromarray(pgm_img).save(pgm_path)
        
        # Save YAML descriptor
        yaml_content = f"""image: {os.path.basename(pgm_path)}
resolution: {self.resolution:.4f}
origin: [{-self.origin_x:.4f}, {-self.origin_y:.4f}, 0.000000]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.25
"""
        with open(yaml_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
            
        print(f"[ROS2 Map Exported] {yaml_path} & {pgm_path}")
        return yaml_path, pgm_path
