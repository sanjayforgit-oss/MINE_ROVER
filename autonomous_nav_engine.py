import math
import time

class AutonomousNavEngine:
    """
    Subterranean Mine Autonomous Navigation & Exploration Engine
    Supports:
    1. Reactive Centerline Tunnel Following & Obstacle Reflexes
    2. Junction & Dead-End Decision Logic
    3. Prior-Map & DXF Waypoint Navigation with Real-Time Avoidance
    """
    def __init__(self, slam_mapper=None):
        self.slam = slam_mapper
        self.enabled = False
        self.mode = "CORRIDOR_EXPLORE" # "CORRIDOR_EXPLORE" or "WAYPOINT_FOLLOW"
        
        # PID Constants for Tunnel Centerline Guidance
        self.kp = 0.8
        self.kd = 0.3
        self.last_lateral_error = 0.0
        
        # State Machine for Multi-Step Maneuvers
        self.state = "IDLE" # "DRIVE_FORWARD", "TURNING_LEFT", "TURNING_RIGHT", "UTURN_REVERSING"
        self.state_start_time = 0.0
        self.target_heading = 0.0
        
        # Waypoints for DXF/Prior-Map Navigation
        self.waypoints = [] # List of (x, y) in meters
        self.current_waypoint_idx = 0
        self.waypoint_reach_threshold = 0.30 # 30 cm
        
        # Safety Thresholds (cm)
        self.FRONT_CRITICAL_CM = 38
        self.FRONT_CLEAR_CM = 65
        self.SIDE_CLEAR_MIN = 25
        
        # Default Speeds (PWM)
        self.SPEED_CRUISE = 240
        self.SPEED_TURN = 200
        self.SPEED_CREEP = 180
        
    def set_mode(self, mode_str):
        self.mode = mode_str
        self.state = "IDLE"
        self.current_waypoint_idx = 0

    def load_waypoints(self, wp_list):
        self.waypoints = wp_list
        self.current_waypoint_idx = 0
        print(f"[Autonav] Loaded {len(wp_list)} navigation waypoints.")

    def compute_next_action(self, telemetry):
        """
        Main decision loop. Takes real-time telemetry dictionary and returns (dir_char, speed_val, log_msg).
        """
        if not self.enabled:
            return 'S', 0, "Autonomous Navigation Inactive (Manual Mode)"
            
        sonar = telemetry.get("sonar", {})
        f_dist = sonar.get("F", 100)
        r_dist = sonar.get("R", 100)
        l_dist = sonar.get("L", 100)
        b_dist = sonar.get("B", 100)
        
        # Route to active controller
        if self.mode == "WAYPOINT_FOLLOW" and len(self.waypoints) > 0 and self.current_waypoint_idx < len(self.waypoints):
            return self._execute_waypoint_navigation(f_dist, r_dist, l_dist, b_dist)
        else:
            return self._execute_corridor_exploration(f_dist, r_dist, l_dist, b_dist)

    def _execute_corridor_exploration(self, f_dist, r_dist, l_dist, b_dist):
        now = time.time()
        
        # 1. State Machine Handling (Active Turning Maneuvers)
        if self.state == "TURNING_LEFT":
            if f_dist > self.FRONT_CLEAR_CM or (now - self.state_start_time > 2.5):
                self.state = "IDLE"
                return 'F', self.SPEED_CRUISE, "Turn complete -> Resuming Forward Exploration"
            return 'L', self.SPEED_TURN, f"Pivoting LEFT into open drift (Front clearance: {f_dist}cm)"
            
        elif self.state == "TURNING_RIGHT":
            if f_dist > self.FRONT_CLEAR_CM or (now - self.state_start_time > 2.5):
                self.state = "IDLE"
                return 'F', self.SPEED_CRUISE, "Turn complete -> Resuming Forward Exploration"
            return 'R', self.SPEED_TURN, f"Pivoting RIGHT into open drift (Front clearance: {f_dist}cm)"
            
        elif self.state == "UTURN_REVERSING":
            if now - self.state_start_time > 1.8:
                # After reversing out of dead-end, pivot 180
                self.state = "TURNING_LEFT"
                self.state_start_time = now
                return 'L', self.SPEED_TURN, "Dead-end escape -> Executing 180° Spin"
            return 'B', self.SPEED_CREEP, "Dead-end encountered -> Backing up"

        # 2. Obstacle / Wall Collision Reflex
        if f_dist < self.FRONT_CRITICAL_CM:
            # Dead-end check: both left and right blocked
            if l_dist < self.SIDE_CLEAR_MIN and r_dist < self.SIDE_CLEAR_MIN:
                self.state = "UTURN_REVERSING"
                self.state_start_time = now
                return 'B', self.SPEED_CREEP, f"DEAD-END (F:{f_dist}cm, L:{l_dist}cm, R:{r_dist}cm) -> Backtracking"
                
            # Crosscut / T-Junction: Pick side with maximum open space
            if l_dist >= r_dist:
                self.state = "TURNING_LEFT"
                self.state_start_time = now
                return 'L', self.SPEED_TURN, f"Rock obstacle ahead (F:{f_dist}cm) -> Initiating LEFT turn (L:{l_dist}cm > R:{r_dist}cm)"
            else:
                self.state = "TURNING_RIGHT"
                self.state_start_time = now
                return 'R', self.SPEED_TURN, f"Rock obstacle ahead (F:{f_dist}cm) -> Initiating RIGHT turn (R:{r_dist}cm > L:{l_dist}cm)"

        # 3. Tunnel Centerline Guidance (Reactive PID)
        # Lateral error: positive if closer to right wall, negative if closer to left wall
        # Only apply if both walls are within sensing range (< 180cm)
        if l_dist < 180 and r_dist < 180:
            lateral_error = l_dist - r_dist # e = L - R
            d_error = lateral_error - self.last_lateral_error
            self.last_lateral_error = lateral_error
            
            # Significant drift correction
            if lateral_error > 25:
                # Too close to right wall -> steer slightly left
                return 'L', self.SPEED_TURN, f"Centering: Biased to Right wall (L:{l_dist}cm, R:{r_dist}cm) -> Nudging Left"
            elif lateral_error < -25:
                # Too close to left wall -> steer slightly right
                return 'R', self.SPEED_TURN, f"Centering: Biased to Left wall (L:{l_dist}cm, R:{r_dist}cm) -> Nudging Right"

        # 4. Standard Cruise
        return 'F', self.SPEED_CRUISE, f"Cruising Centerline (F:{f_dist}cm, L:{l_dist}cm, R:{r_dist}cm)"

    def _execute_waypoint_navigation(self, f_dist, r_dist, l_dist, b_dist):
        """Navigates through imported CAD/DXF waypoints while maintaining safety reflexes."""
        if not self.slam or self.current_waypoint_idx >= len(self.waypoints):
            return 'S', 0, "All DXF Waypoints Completed!"
            
        target_wx, target_wy = self.waypoints[self.current_waypoint_idx]
        current_x, current_y, current_theta = self.slam.x, self.slam.y, self.slam.theta
        
        # Distance to target waypoint
        dist_to_wp = math.hypot(target_wx - current_x, target_wy - current_y)
        
        # Check if reached waypoint
        if dist_to_wp < self.waypoint_reach_threshold:
            self.current_waypoint_idx += 1
            if self.current_waypoint_idx >= len(self.waypoints):
                return 'S', 0, "🏁 Mission Complete: Reached final DXF waypoint!"
            return 'F', self.SPEED_CREEP, f"✓ Reached Waypoint {self.current_waypoint_idx}/{len(self.waypoints)}"

        # 1. Emergency Obstacle Reflex overrides waypoint if blocked by cave-in!
        if f_dist < self.FRONT_CRITICAL_CM:
            if l_dist >= r_dist:
                return 'L', self.SPEED_TURN, f"[Cave-In Avoidance] Detouring Left around unmapped rockfall (F:{f_dist}cm)"
            else:
                return 'R', self.SPEED_TURN, f"[Cave-In Avoidance] Detouring Right around unmapped rockfall (F:{f_dist}cm)"

        # 2. Heading Angle Calculation
        target_heading = math.atan2(target_wy - current_y, target_wx - current_x)
        angle_diff = target_heading - current_theta
        
        # Normalize to [-pi, pi]
        angle_diff = (angle_diff + math.pi) % (2 * math.pi) - math.pi
        
        # Turn to align if heading error > 20 degrees (0.35 rad)
        if angle_diff > 0.35:
            return 'L', self.SPEED_TURN, f"Orienting to Waypoint {self.current_waypoint_idx+1} (Turn Left {math.degrees(angle_diff):.0f}°)"
        elif angle_diff < -0.35:
            return 'R', self.SPEED_TURN, f"Orienting to Waypoint {self.current_waypoint_idx+1} (Turn Right {math.degrees(-angle_diff):.0f}°)"
        else:
            return 'F', self.SPEED_CRUISE, f"Tracking to Waypoint {self.current_waypoint_idx+1} (Dist: {dist_to_wp:.2f}m)"
