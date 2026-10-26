import math
import random
import time
import numpy as np
from PIL import Image, ImageDraw

class MineSimulatorEngine:
    """
    2D Subterranean Mine Simulation & Sensory Raycasting Engine
    Simulates:
    - Branching mine tunnels, pillars, crosscuts, and rockfall dead-ends
    - 4WD skid-steer kinematics with wall collision physics
    - Dual-beam 4-direction ultrasonic raycasting (8 sensors)
    - 3D stratified gas dispersion plumes (CH4 Methane, CO, Smoke)
    - Thermal survivor hotspot locations
    """
    def __init__(self, width_m=16.0, height_m=16.0):
        self.width_m = width_m
        self.height_m = height_m
        
        # Rover State
        self.x = 2.5 # Start in Main South Tunnel
        self.y = 2.0
        self.theta = math.pi / 2.0 # Facing North (Up)
        self.linear_velocity = 0.0
        self.angular_velocity = 0.0
        self.total_dist_traveled = 0.0
        self.current_motion = 'S'
        
        # Physics Parameters
        self.MAX_LINEAR_SPEED = 0.40 # m/s at 255 PWM
        self.MAX_ANGULAR_SPEED = 1.80 # rad/s (~100 deg/s)
        self.ROVER_RADIUS = 0.22 # 22 cm collision radius
        
        # Define Mine Tunnel Walls (List of line segments: [(x1, y1, x2, y2), ...])
        self.walls = self._generate_mine_layout()
        
        # Gas Plume Source Emitters: [(x, y, type, peak_adc, radius_m), ...]
        self.gas_sources = [
            (2.5, 13.5, "CH4", 780, 3.2), # High Methane pool at North Dead-End Ceiling
            (13.5, 8.5, "CO",  650, 2.8), # Carbon Monoxide plume near East Smoldering Zone
            (8.0, 8.0,  "MQ2", 520, 2.2), # Smoke at Central Crosscut
        ]
        
        # Simulated Survivors: [(x, y, label, temp_c), ...]
        self.survivors = [
            (2.5, 13.2, "Trapped Miner #1 (Injured)", 37.8),
            (13.2, 8.5, "Trapped Miner #2 (Unconscious)", 36.9)
        ]
        
        self.last_sim_time = time.time()
        
    def _generate_mine_layout(self):
        """Generates a realistic underground coal/metal mine drift network."""
        w, h = self.width_m, self.height_m
        walls = []
        
        # 1. Outer Perimeter Walls
        walls.append((0.5, 0.5, w - 0.5, 0.5))
        walls.append((w - 0.5, 0.5, w - 0.5, h - 0.5))
        walls.append((w - 0.5, h - 0.5, 0.5, h - 0.5))
        walls.append((0.5, h - 0.5, 0.5, 0.5))
        
        # 2. Left Pillar (Pillar 1)
        walls.append((4.0, 3.5, 6.5, 3.5))
        walls.append((6.5, 3.5, 6.5, 12.0))
        walls.append((6.5, 12.0, 4.0, 12.0))
        walls.append((4.0, 12.0, 4.0, 3.5))
        
        # 3. Right Pillar (Pillar 2)
        walls.append((9.5, 3.5, 12.0, 3.5))
        walls.append((12.0, 3.5, 12.0, 6.5))
        walls.append((12.0, 6.5, 9.5, 6.5))
        walls.append((9.5, 6.5, 9.5, 3.5))
        
        # 4. East Chamber Pillar (Pillar 3)
        walls.append((9.5, 10.0, 12.0, 10.0))
        walls.append((12.0, 10.0, 12.0, 13.0))
        walls.append((12.0, 13.0, 9.5, 13.0))
        walls.append((9.5, 13.0, 9.5, 10.0))
        
        # 5. Rockfall Collapse in North-East Dead-End
        walls.append((13.5, 11.5, 15.0, 11.5))
        
        return walls

    def reset_rover(self, x=2.5, y=2.0, theta=math.pi/2.0):
        self.x = x
        self.y = y
        self.theta = theta
        self.total_dist_traveled = 0.0
        self.current_motion = 'S'
        self.last_sim_time = time.time()

    def update_physics(self, motion_char, speed_val=255, dt=None):
        now = time.time()
        if dt is None:
            dt = now - self.last_sim_time
            self.last_sim_time = now
        dt = min(max(dt, 0.005), 0.2)
        
        self.current_motion = motion_char
        speed_ratio = max(0.0, min(speed_val / 255.0, 1.0))
        
        target_lin = 0.0
        target_ang = 0.0
        
        if motion_char == 'F':
            target_lin = self.MAX_LINEAR_SPEED * speed_ratio
        elif motion_char == 'B':
            target_lin = -self.MAX_LINEAR_SPEED * speed_ratio
        elif motion_char == 'L':
            target_ang = self.MAX_ANGULAR_SPEED * speed_ratio
        elif motion_char == 'R':
            target_ang = -self.MAX_ANGULAR_SPEED * speed_ratio
            
        # Kinematic integration
        self.theta += target_ang * dt
        self.theta = (self.theta + math.pi) % (2 * math.pi) - math.pi
        
        dx = target_lin * dt * math.cos(self.theta)
        dy = target_lin * dt * math.sin(self.theta)
        
        # Collision check with all walls
        new_x = self.x + dx
        new_y = self.y + dy
        
        if not self._check_collision(new_x, new_y):
            self.x = new_x
            self.y = new_y
            self.total_dist_traveled += abs(target_lin * dt)
        else:
            # Hit rock wall -> slide or stop
            pass

    def _check_collision(self, px, py):
        for x1, y1, x2, y2 in self.walls:
            dist = self._point_to_line_dist(px, py, x1, y1, x2, y2)
            if dist < self.ROVER_RADIUS:
                return True
        return False

    def _point_to_line_dist(self, px, py, x1, y1, x2, y2):
        line_len_sq = (x2 - x1)**2 + (y2 - y1)**2
        if line_len_sq == 0: return math.hypot(px - x1, py - y1)
        t = max(0, min(1, ((px - x1)*(x2 - x1) + (py - y1)*(y2 - y1)) / line_len_sq))
        proj_x = x1 + t * (x2 - x1)
        proj_y = y1 + t * (y2 - y1)
        return math.hypot(px - proj_x, py - proj_y)

    def _ray_intersect_segment(self, rx, ry, r_angle, x1, y1, x2, y2):
        """Finds intersection distance of a ray from (rx, ry) at r_angle with line segment (x1, y1)-(x2, y2)."""
        dx = math.cos(r_angle)
        dy = math.sin(r_angle)
        
        # Segment vector
        sx = x2 - x1
        sy = y2 - y1
        
        denom = dx * sy - dy * sx
        if abs(denom) < 1e-6:
            return None # Parallel
            
        t = ((x1 - rx) * sy - (y1 - ry) * sx) / denom
        u = ((x1 - rx) * dy - (y1 - ry) * dx) / denom
        
        if t > 0 and 0.0 <= u <= 1.0:
            return t
        return None

    def raycast_beam(self, rel_angle_rad, max_range=2.5):
        beam_angle = self.theta + rel_angle_rad
        min_dist = max_range
        
        for x1, y1, x2, y2 in self.walls:
            hit_dist = self._ray_intersect_segment(self.x, self.y, beam_angle, x1, y1, x2, y2)
            if hit_dist is not None and hit_dist < min_dist:
                min_dist = hit_dist
                
        # Add realistic sensor noise (+/- 1.5 cm)
        noise = random.gaunormvariate(0.0, 0.012) if hasattr(random, 'gaunormvariate') else random.gauss(0.0, 0.012)
        measured_m = max(0.04, min_dist + noise)
        return int(measured_m * 100) # cm

    def get_simulated_telemetry(self):
        """Outputs exact dictionary matching the physical Arduino Mega packet."""
        # 8 Ultrasonic beams
        f1 = self.raycast_beam(math.radians(12))
        f2 = self.raycast_beam(-math.radians(12))
        r1 = self.raycast_beam(-math.pi / 2.0 + math.radians(12))
        r2 = self.raycast_beam(-math.pi / 2.0 - math.radians(12))
        b1 = self.raycast_beam(math.pi - math.radians(12))
        b2 = self.raycast_beam(math.pi + math.radians(12))
        l1 = self.raycast_beam(math.pi / 2.0 + math.radians(12))
        l2 = self.raycast_beam(math.pi / 2.0 - math.radians(12))
        
        f_min = min(f1, f2)
        r_min = min(r1, r2)
        b_min = min(b1, b2)
        l_min = min(l1, l2)
        
        # Gas Sensor calculations based on proximity to sources
        mq4 = 110 + random.randint(0, 10) # Methane baseline
        mq7 = 90  + random.randint(0, 8)  # CO baseline
        mq2 = 105 + random.randint(0, 8)  # Smoke baseline
        
        for gx, gy, gtype, peak_val, radius in self.gas_sources:
            dist = math.hypot(self.x - gx, self.y - gy)
            if dist < radius:
                # Gaussian plume concentration curve
                conc = (peak_val - 120) * math.exp(-(dist**2) / (2 * (radius/2.2)**2))
                if gtype == "CH4": mq4 = max(mq4, int(110 + conc))
                elif gtype == "CO": mq7 = max(mq7, int(90 + conc))
                elif gtype == "MQ2": mq2 = max(mq2, int(105 + conc))
                
        telemetry = {
            "sector": 1,
            "motion": self.current_motion,
            "sonar": {
                "F": f_min, "F1": f1, "F2": f2,
                "R": r_min, "R1": r1, "R2": r2,
                "B": b_min, "B1": b1, "B2": b2,
                "L": l_min, "L1": l1, "L2": l2
            },
            "gas": {
                "mq4": mq4,
                "mq7": mq7,
                "mq2": mq2
            },
            "dist_m": self.total_dist_traveled,
            "gov": 0,
            "segment": 0,
            "total_seg": 2,
            "sim_pose": {"x": self.x, "y": self.y, "theta": self.theta}
        }
        return telemetry

    def render_sim_view(self, target_w=500, target_h=500):
        """Renders an interactive top-down visual map of the virtual mine & rover."""
        scale_x = target_w / self.width_m
        scale_y = target_h / self.height_m
        
        img = Image.new('RGB', (target_w, target_h), color='#0f172a') # Deep Slate background
        draw = ImageDraw.Draw(img)
        
        # 1. Draw Gas Hazard Plume Circles
        for gx, gy, gtype, peak_val, radius in self.gas_sources:
            px = gx * scale_x
            py = target_h - (gy * scale_y)
            pr = radius * scale_x
            color = (16, 185, 129, 60) if gtype == "CH4" else (245, 158, 11, 60)
            draw.ellipse([px - pr, py - pr, px + pr, py + pr], outline='#10b981' if gtype=="CH4" else '#f59e0b', width=1)
            draw.text((px, py), f"{gtype}\nPlume", fill='#10b981' if gtype=="CH4" else '#fbbf24')
            
        # 2. Draw Survivors / Hotspots
        for sx, sy, label, temp_c in self.survivors:
            px = sx * scale_x
            py = target_h - (sy * scale_y)
            draw.rectangle([px - 6, py - 6, px + 6, py + 6], fill='#ef4444', outline='white')
            draw.text((px + 8, py - 8), f"♨ {temp_c}°C\n{label}", fill='#fca5a5')

        # 3. Draw Solid Rock Walls
        for x1, y1, x2, y2 in self.walls:
            px1 = x1 * scale_x
            py1 = target_h - (y1 * scale_y)
            px2 = x2 * scale_x
            py2 = target_h - (y2 * scale_y)
            draw.line([px1, py1, px2, py2], fill='#38bdf8', width=3) # Bright Cyan Rock Faces

        # 4. Draw Rover Body & Sonar Beams
        rx = self.x * scale_x
        ry = target_h - (self.y * scale_y)
        rr = self.ROVER_RADIUS * scale_x
        
        # Draw 4 primary Sonar Raycast Beams (yellow lines)
        for angle_offset, col in [(0.0, '#38bdf8'), (math.pi/2, '#10b981'), (-math.pi/2, '#10b981'), (math.pi, '#f43f5e')]:
            beam_rad = self.theta + angle_offset
            dist_cm = self.raycast_beam(angle_offset)
            dist_px = (dist_cm / 100.0) * scale_x
            bx = rx + dist_px * math.cos(beam_rad)
            by = ry - dist_px * math.sin(beam_rad)
            draw.line([rx, ry, bx, by], fill='#f59e0b', width=1)
            draw.ellipse([bx - 2, by - 2, bx + 2, by + 2], fill='#fbbf24')

        # Rover Chassis Box
        draw.ellipse([rx - rr, ry - rr, rx + rr, ry + rr], fill='#0284c7', outline='white', width=2)
        
        # Rover Heading Arrow
        hx = rx + (rr + 10) * math.cos(self.theta)
        hy = ry - (rr + 10) * math.sin(self.theta)
        draw.line([rx, ry, hx, hy], fill='white', width=3)
        
        return img
