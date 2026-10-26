import cv2
import serial
import serial.tools.list_ports
import json
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import math
from PIL import Image, ImageTk

# YOLO Global state
model = None
YOLO_AVAILABLE = False
yolo_loading = True

def load_yolo_background():
    global model, YOLO_AVAILABLE, yolo_loading
    try:
        from ultralytics import YOLO
        print('[AI] Loading YOLOv8n pretrained model in background...')
        model = YOLO('yolov8n.pt')
        YOLO_AVAILABLE = True
        print('[AI] YOLOv8n loaded successfully!')
    except Exception as e:
        YOLO_AVAILABLE = False
        print(f'[AI Warning] Ultralytics not available ({e}). Running in standard vision mode.')
    finally:
        yolo_loading = False

# Start loading YOLO in background thread immediately so GUI opens with zero delay
threading.Thread(target=load_yolo_background, daemon=True).start()

class MineRescueRoverStation:
    def __init__(self, root):
        self.root = root
        self.root.title('AI-Powered Underground Mine Rescue & Reconnaissance System - SIH PS 26039')
        self.root.geometry('1380x850')
        self.root.minsize(1150, 700)
        self.root.configure(bg='#12141d')
        
        try:
            self.root.state('zoomed') # Maximize for clean display
        except:
            pass

        # Serial / Hardware State
        self.ser = None
        self.serial_connected = False
        self.sim_mode = False
        
        # Telemetry State
        self.telemetry = {
            'front': 100, 'left': 100, 'right': 100,
            'front_left': 100, 'front_right': 100,
            'mq4': 120, 'mq7': 90, 'mq2': 110,
            'temp': 28.5,
            'motion': 'S'
        }
        
        # Navigation & Situational Awareness State
        self.nav_decision_text = 'INITIALIZING SENSORY RADAR & AI ENGINE...'
        self.nav_decision_color = '#00d2d3'
        self.nav_log_history = []
        self.last_logged_action = ''

        # AI Perception State
        self.human_detected = False
        self.confidence_score = 0.0

        # Radar & Topography State
        self.radar_angle = 0
        self.radar_direction = 1

        # Emergency & Blinking State
        self.emergency_active = False
        self.emergency_gas_type = ''
        self.emergency_value = 0
        self.blink_phase = False
        self.popup_open = False
        self.popup_window = None

        # Camera & Video State
        self.cap = None
        self.current_cam_idx = 1 # Default to laptop integrated camera (Index 1)
        self.cam_lock = threading.Lock()
        self.running = True

        self.setup_ui()
        self.bind_keyboard_controls()
        
        # Start Video and Periodic Loops
        self.start_video_stream()
        self.start_radar_animation_loop()
        self.start_emergency_blink_loop()
        
    def setup_ui(self):
        # 1. Top Header Bar
        self.header_frame = tk.Frame(self.root, bg='#1a1c29', height=50)
        self.header_frame.pack(fill=tk.X, padx=8, pady=(6, 2))
        
        title_lbl = tk.Label(self.header_frame, text='⛏️ AI-POWERED UNDERGROUND MINE SAFETY, MONITORING & RESCUE SYSTEM', 
                             fg='#00d2d3', bg='#1a1c29', font=('Segoe UI', 14, 'bold'))
        title_lbl.pack(side=tk.LEFT, padx=15, pady=8)

        sih_lbl = tk.Label(self.header_frame, text='SIH PS ID: 26039 | Govt. of Jharkhand', 
                           fg='#a4b0be', bg='#1a1c29', font=('Segoe UI', 10, 'italic'))
        sih_lbl.pack(side=tk.LEFT, padx=10, pady=8)

        # Simulation Mode Toggle Button
        self.btn_sim = tk.Button(self.header_frame, text='🎮 Virtual Simulator: OFF', bg='#3d3d5c', fg='#dfe4ea', 
                                 font=('Segoe UI', 9, 'bold'), padx=8, pady=2, command=self.toggle_sim_mode)
        self.btn_sim.pack(side=tk.RIGHT, padx=15, pady=8)

        # 2. Connection & Video Source Bar
        conn_frame = tk.Frame(self.root, bg='#12141d')
        conn_frame.pack(fill=tk.X, padx=12, pady=3)

        # Hardware COM Controls
        tk.Label(conn_frame, text='COM Port:', fg='#ffffff', bg='#12141d', font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=(2, 4))
        self.port_combo = ttk.Combobox(conn_frame, width=12, state='readonly')
        self.refresh_ports()
        self.port_combo.pack(side=tk.LEFT, padx=4)

        btn_refresh = tk.Button(conn_frame, text='🔄', bg='#485460', fg='white', font=('Segoe UI', 9), command=self.refresh_ports)
        btn_refresh.pack(side=tk.LEFT, padx=2)

        self.btn_connect = tk.Button(conn_frame, text='⚡ Connect Arduino', bg='#10ac84', fg='white', 
                                     font=('Segoe UI', 9, 'bold'), padx=8, command=self.toggle_serial)
        self.btn_connect.pack(side=tk.LEFT, padx=6)

        # Camera Source Selector (Allows manual override if Smart Connect / Phone Cam is active)
        tk.Label(conn_frame, text='🎥 Video Source:', fg='#00d2d3', bg='#12141d', font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=(18, 4))
        self.cam_combo = ttk.Combobox(conn_frame, width=28, state='readonly')
        self.populate_camera_list()
        self.cam_combo.pack(side=tk.LEFT, padx=4)
        self.cam_combo.bind('<<ComboboxSelected>>', self.on_camera_dropdown_changed)

        btn_switch_cam = tk.Button(conn_frame, text='🔄 Switch Cam (C)', bg='#341f97', fg='white', 
                                   font=('Segoe UI', 9, 'bold'), padx=6, command=self.cycle_camera)
        btn_switch_cam.pack(side=tk.LEFT, padx=4)

        self.status_lbl = tk.Label(conn_frame, text='Status: Ready (Select COM or Enable Simulation)', fg='#f39c12', bg='#12141d', font=('Segoe UI', 9, 'bold'))
        self.status_lbl.pack(side=tk.LEFT, padx=10)

        # 3. Main Dashboard Body (Left & Right Split)
        main_body = tk.Frame(self.root, bg='#12141d')
        main_body.pack(fill=tk.BOTH, expand=True, padx=10, pady=3)

        # ==========================================
        # LEFT COLUMN: Live Camera HUD & 180° Radar Map
        # ==========================================
        left_col = tk.Frame(main_body, bg='#12141d')
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=2)

        # Video Frame
        self.video_box = tk.LabelFrame(left_col, text='🎥 Live AI Reconnaissance Feed (Survivor & Trap Detection)', 
                                       fg='#00d2d3', bg='#1a1c29', font=('Segoe UI', 10, 'bold'))
        self.video_box.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self.video_label = tk.Label(self.video_box, bg='#000000')
        self.video_label.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # 180° Radar & Topography Contour Scanner Frame
        self.scanner_box = tk.LabelFrame(left_col, text='📡 180° Front Sector Radar & Terrain Topography Contour Map', 
                                         fg='#00d2d3', bg='#1a1c29', font=('Segoe UI', 10, 'bold'))
        self.scanner_box.pack(fill=tk.X, padx=2, pady=(4, 2))

        # Canvas for Radar and Topography Profile
        self.scanner_canvas = tk.Canvas(self.scanner_box, bg='#0d0f18', height=205, highlightthickness=0)
        self.scanner_canvas.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # ==========================================
        # RIGHT COLUMN: Situational Awareness, Sensors & Controls
        # ==========================================
        right_col = tk.Frame(main_body, bg='#12141d', width=530)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, padx=4, pady=2)

        # A. AI Situational Awareness & Movement Action Banner
        self.decision_box = tk.Frame(right_col, bg='#1a1c29', bd=2, relief=tk.RIDGE)
        self.decision_box.pack(fill=tk.X, pady=3)

        tk.Label(self.decision_box, text='🤖 AI AUTONOMOUS NAVIGATION & ENVIRONMENT AWARENESS', 
                 fg='#00d2d3', bg='#1a1c29', font=('Segoe UI', 9, 'bold')).pack(anchor=tk.W, padx=8, pady=(4, 1))

        self.lbl_decision = tk.Label(self.decision_box, text=self.nav_decision_text, 
                                     fg='#1dd1a1', bg='#1a1c29', font=('Segoe UI', 11, 'bold'), wraplength=490, justify=tk.LEFT)
        self.lbl_decision.pack(fill=tk.X, padx=8, pady=(2, 6))

        # B. Real-Time Autonomous Decision Log Box
        log_frame = tk.LabelFrame(right_col, text='📝 Live Reactive Navigation Decision Log', fg='#00d2d3', bg='#1a1c29', font=('Segoe UI', 9, 'bold'))
        log_frame.pack(fill=tk.X, pady=3)

        self.log_listbox = tk.Listbox(log_frame, bg='#0d0f18', fg='#c8d6e5', height=4, font=('Consolas', 9), 
                                      selectbackground='#222f3e', bd=0, highlightthickness=0)
        self.log_listbox.pack(fill=tk.X, padx=6, pady=4)
        self.add_nav_log('System initialized. Monitoring 3-axis ultrasonics and multi-gas array.')

        # C. 3-Axis Ultrasonic Obstacle Gauge Cards
        ultra_card = tk.LabelFrame(right_col, text='📐 3-Axis Obstacle Collision Distance Gauges', fg='#00d2d3', bg='#1a1c29', font=('Segoe UI', 9, 'bold'))
        ultra_card.pack(fill=tk.X, pady=3)

        u_grid = tk.Frame(ultra_card, bg='#1a1c29')
        u_grid.pack(fill=tk.X, padx=8, pady=4)

        # Left Gauge
        self.lbl_dist_left = tk.Label(u_grid, text='LEFT (D24/25)\n100 cm\n[Safe]', bg='#222f3e', fg='#1dd1a1', 
                                      font=('Segoe UI', 9, 'bold'), width=15, height=3, relief=tk.GROOVE)
        self.lbl_dist_left.grid(row=0, column=0, padx=3, pady=2, sticky='ew')

        # Front Gauge
        self.lbl_dist_front = tk.Label(u_grid, text='FRONT (D22/23)\n100 cm\n[Safe]', bg='#222f3e', fg='#1dd1a1', 
                                       font=('Segoe UI', 9, 'bold'), width=16, height=3, relief=tk.GROOVE)
        self.lbl_dist_front.grid(row=0, column=1, padx=3, pady=2, sticky='ew')

        # Right Gauge
        self.lbl_dist_right = tk.Label(u_grid, text='RIGHT (D26/27)\n100 cm\n[Safe]', bg='#222f3e', fg='#1dd1a1', 
                                       font=('Segoe UI', 9, 'bold'), width=15, height=3, relief=tk.GROOVE)
        self.lbl_dist_right.grid(row=0, column=2, padx=3, pady=2, sticky='ew')
        u_grid.columnconfigure(0, weight=1)
        u_grid.columnconfigure(1, weight=1)
        u_grid.columnconfigure(2, weight=1)

        # D. Gas & Atmospheric Hazards Card
        self.gas_card = tk.LabelFrame(right_col, text='☣️ Atmospheric Toxicity & Lighter Gas Telemetry', fg='#00d2d3', bg='#1a1c29', font=('Segoe UI', 9, 'bold'))
        self.gas_card.pack(fill=tk.X, pady=3)

        gas_inner = tk.Frame(self.gas_card, bg='#1a1c29')
        gas_inner.pack(fill=tk.X, padx=8, pady=3)

        self.lbl_mq2 = tk.Label(gas_inner, text='🔥 MQ-2 (Lighter / Butane / Smoke): Normal (110)', fg='#1dd1a1', bg='#1a1c29', font=('Segoe UI', 9, 'bold'))
        self.lbl_mq2.pack(anchor=tk.W, pady=1)

        self.lbl_mq4 = tk.Label(gas_inner, text='⚠️ MQ-4 (Methane CH4 / Explosive):  Normal (120)', fg='#1dd1a1', bg='#1a1c29', font=('Segoe UI', 9, 'bold'))
        self.lbl_mq4.pack(anchor=tk.W, pady=1)

        self.lbl_mq7 = tk.Label(gas_inner, text='⚠️ MQ-7 (Carbon Monoxide CO / Toxic): Normal (90)', fg='#1dd1a1', bg='#1a1c29', font=('Segoe UI', 9, 'bold'))
        self.lbl_mq7.pack(anchor=tk.W, pady=1)

        self.lbl_temp = tk.Label(gas_inner, text='🌡️ LM35 Temperature:               Normal (28.5 °C)', fg='#1dd1a1', bg='#1a1c29', font=('Segoe UI', 9, 'bold'))
        self.lbl_temp.pack(anchor=tk.W, pady=1)

        # E. Control Pad & Quick Test Triggers
        ctrl_card = tk.LabelFrame(right_col, text='🎮 Rover Movement Controls & Simulation Quick-Triggers', fg='#00d2d3', bg='#1a1c29', font=('Segoe UI', 9, 'bold'))
        ctrl_card.pack(fill=tk.BOTH, expand=True, pady=3)

        btn_grid = tk.Frame(ctrl_card, bg='#1a1c29')
        btn_grid.pack(pady=3)

        btn_w = tk.Button(btn_grid, text='▲ FORWARD (W)', width=14, height=1, bg='#341f97', fg='white', font=('Segoe UI', 9, 'bold'), command=lambda: self.send_command('W'))
        btn_w.grid(row=0, column=1, padx=3, pady=2)

        btn_a = tk.Button(btn_grid, text='◀ LEFT (A)', width=12, height=1, bg='#341f97', fg='white', font=('Segoe UI', 9, 'bold'), command=lambda: self.send_command('A'))
        btn_a.grid(row=1, column=0, padx=3, pady=2)

        btn_s_stop = tk.Button(btn_grid, text='■ STOP (Space)', width=14, height=1, bg='#ee5253', fg='white', font=('Segoe UI', 9, 'bold'), command=lambda: self.send_command(' '))
        btn_s_stop.grid(row=1, column=1, padx=3, pady=2)

        btn_d = tk.Button(btn_grid, text='▶ RIGHT (D)', width=12, height=1, bg='#341f97', fg='white', font=('Segoe UI', 9, 'bold'), command=lambda: self.send_command('D'))
        btn_d.grid(row=1, column=2, padx=3, pady=2)

        btn_s_back = tk.Button(btn_grid, text='▼ BACK (S)', width=14, height=1, bg='#341f97', fg='white', font=('Segoe UI', 9, 'bold'), command=lambda: self.send_command('S'))
        btn_s_back.grid(row=2, column=1, padx=3, pady=2)

        self.motion_status = tk.Label(ctrl_card, text='Current Motion: STOPPED', fg='#c8d6e5', bg='#1a1c29', font=('Segoe UI', 9, 'bold'))
        self.motion_status.pack(pady=1)

        # Quick Test Trigger Buttons for instant demonstration (especially without battery)
        sim_trig_frame = tk.Frame(ctrl_card, bg='#1a1c29')
        sim_trig_frame.pack(fill=tk.X, padx=4, pady=2)

        tk.Label(sim_trig_frame, text='⚡ Quick Interactive Simulation Triggers (Test Without Battery):', fg='#a4b0be', bg='#1a1c29', font=('Segoe UI', 8, 'italic')).pack(anchor=tk.W)

        btn_row = tk.Frame(sim_trig_frame, bg='#1a1c29')
        btn_row.pack(fill=tk.X, pady=2)

        tk.Button(btn_row, text='🔥 Test Lighter Gas (MQ-2)', bg='#d63031', fg='white', font=('Segoe UI', 8, 'bold'), 
                  command=lambda: self.simulate_hazard('LIGHTER_GAS')).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        tk.Button(btn_row, text='🛑 Front Obstacle (4 cm)', bg='#e17055', fg='white', font=('Segoe UI', 8, 'bold'), 
                  command=lambda: self.simulate_obstacle('FRONT')).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        tk.Button(btn_row, text='◀ Left (3 cm)', bg='#e67e22', fg='white', font=('Segoe UI', 8, 'bold'), 
                  command=lambda: self.simulate_obstacle('LEFT')).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        tk.Button(btn_row, text='▶ Right (3 cm)', bg='#e67e22', fg='white', font=('Segoe UI', 8, 'bold'), 
                  command=lambda: self.simulate_obstacle('RIGHT')).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        tk.Button(btn_row, text='🔄 Reset Clear', bg='#27ae60', fg='white', font=('Segoe UI', 8, 'bold'), 
                  command=self.reset_simulation).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)

    def populate_camera_list(self):
        # Index 1 = Physical Integrated Laptop Camera; Index 0/2 = Smart Connect Virtual Camera
        self.cam_mapping = [1, 0, 2]
        options = [
            'Camera 1: Laptop Integrated Webcam (Default)',
            'Camera 0: Smart Connect (Phone Cam)',
            'Camera 2: Smart Connect (Phone Cam Alt)'
        ]
        self.cam_combo['values'] = options
        self.cam_combo.current(0) # Select Camera 1 as default

    def on_camera_dropdown_changed(self, event=None):
        combo_sel = self.cam_combo.current()
        if combo_sel >= 0 and combo_sel < len(self.cam_mapping):
            target_idx = self.cam_mapping[combo_sel]
            if target_idx != self.current_cam_idx:
                self.switch_camera_to_index(target_idx)

    def cycle_camera(self):
        # Cycle through [1, 0, 2]
        cur_pos = 0
        if self.current_cam_idx in self.cam_mapping:
            cur_pos = self.cam_mapping.index(self.current_cam_idx)
        next_idx = self.cam_mapping[next_pos]
        self.switch_camera_to_index(next_idx)
        self.cam_combo.current(next_pos)

    def switch_camera_to_index(self, new_idx):
        self.add_nav_log(f'Switching video feed to Camera {new_idx}...')
        with self.cam_lock:
            if self.cap:
                try:
                    self.cap.release()
                except:
                    pass
            try:
                self.cap = cv2.VideoCapture(new_idx, cv2.CAP_DSHOW)
                if not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(new_idx)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self.current_cam_idx = new_idx
                self.add_nav_log(f'Connected to Camera {new_idx}.')
            except Exception as e:
                self.add_nav_log(f'Error switching to Camera {new_idx}: {e}')

    def refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.current(0)

    def toggle_sim_mode(self):
        self.sim_mode = not self.sim_mode
        if self.sim_mode:
            self.btn_sim.config(text='🎮 Virtual Simulator: ON', bg='#10ac84', fg='white')
            self.status_lbl.config(text='Status: Running in Advanced Virtual Simulator Mode', fg='#10ac84')
            self.add_nav_log('🎮 Virtual Rover Simulation Mode ACTIVE.')
        else:
            self.btn_sim.config(text='🎮 Virtual Simulator: OFF', bg='#3d3d5c', fg='#dfe4ea')
            self.status_lbl.config(text='Status: Hardware Mode (Connect Arduino Mega)', fg='#f39c12')
            self.add_nav_log('Hardware Mode Selected.')

    def toggle_serial(self):
        if not self.serial_connected:
            selected_port = self.port_combo.get()
            if not selected_port:
                self.status_lbl.config(text='Status: No COM port selected', fg='#ff6b6b')
                return
            try:
                self.ser = serial.Serial(selected_port, 115200, timeout=0.1)
                time.sleep(1.5) # Allow Mega reboot
                self.serial_connected = True
                self.btn_connect.config(text='🔌 Disconnect', bg='#ee5253')
                self.status_lbl.config(text=f'Status: Connected to Arduino Mega ({selected_port})', fg='#1dd1a1')
                self.add_nav_log(f'Connected to Arduino Mega on {selected_port} @ 115200 baud.')
                
                self.serial_thread = threading.Thread(target=self.read_serial_loop, daemon=True)
                self.serial_thread.start()
            except Exception as ex:
                self.status_lbl.config(text=f'Connection Error: {ex}', fg='#ff6b6b')
        else:
            self.serial_connected = False
            if self.ser:
                try:
                    self.ser.close()
                except:
                    pass
            self.btn_connect.config(text='⚡ Connect Arduino Mega', bg='#10ac84')
            self.status_lbl.config(text='Status: Disconnected', fg='#ff9f43')
            self.add_nav_log('Disconnected from Arduino Mega.')

    def read_serial_loop(self):
        while self.serial_connected and self.running:
            try:
                if self.ser and self.ser.in_waiting:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if line.startswith('{') and line.endswith('}'):
                        data = json.loads(line)
                        self.telemetry.update(data)
                        self.root.after(0, self.process_telemetry_and_navigation)
            except Exception as e:
                pass
            time.sleep(0.02)

    def process_telemetry_and_navigation(self):
        f_dist = self.telemetry.get('front', 100)
        l_dist = self.telemetry.get('left', 100)
        r_dist = self.telemetry.get('right', 100)

        fl_dist = self.telemetry.get('front_left', 100)
        fr_dist = self.telemetry.get('front_right', 100)

        action_text = ''
        action_color = '#1dd1a1'

        if 0 < f_dist <= 5:
            action_text = f'🛑 STOP: Front Obstacle Detected ({f_dist} cm)! Emergency Braking Active.'
            action_color = '#ff4757'
            self.telemetry['motion'] = 'S'

        elif 0 < l_dist <= 4:
            action_text = f'⚠️ Obstacle on LEFT ({l_dist} cm)! Adjusting Trajectory: Steer Slightly RIGHT ↗️'
            action_color = '#ffa502'
            self.telemetry['motion'] = 'R'

        elif 0 < r_dist <= 4:
            action_text = f'⚠️ Obstacle on RIGHT ({r_dist} cm)! Adjusting Trajectory: Steer Slightly LEFT ↖️'
            action_color = '#ffa502'
            self.telemetry['motion'] = 'L'

        else:
            motion_char = self.telemetry.get('motion', 'S')
            if motion_char == 'F':
                action_text = f'🟢 Path Clear (Front: {f_dist} cm). Rover Navigating FORWARD ▲'
                action_color = '#1dd1a1'
            elif motion_char == 'B':
                action_text = f'🔵 Rover Navigating BACKWARD ▼'
                action_color = '#54a0ff'
            elif motion_char == 'L':
                action_text = f'🔄 Rover Turning LEFT ◀'
                action_color = '#a55eea'
            elif motion_char == 'R':
                action_text = f'🔄 Rover Turning RIGHT ▶'
                action_color = '#a55eea'
            else:
                action_text = f'✅ Environment Aware: Path Clear (Front: {f_dist}cm | Left: {l_dist}cm | Right: {r_dist}cm). Rover Standby.'
                action_color = '#00d2d3'

        self.lbl_decision.config(text=action_text, fg=action_color)

        if action_text != self.last_logged_action:
            self.add_nav_log(action_text)
            self.last_logged_action = action_text

        # Left Gauge
        if 0 < l_dist <= 4:
            self.lbl_dist_left.config(text=f'LEFT (D24/25)\n{l_dist} cm\n[⚠️ CLOSE: Steer Right]', bg='#e74c3c', fg='#ffffff')
        elif l_dist < 15:
            self.lbl_dist_left.config(text=f'LEFT (D24/25)\n{l_dist} cm\n[Caution]', bg='#e67e22', fg='#ffffff')
        else:
            self.lbl_dist_left.config(text=f'LEFT (D24/25)\n{l_dist} cm\n[Safe]', bg='#222f3e', fg='#1dd1a1')

        # Front Gauge
        if 0 < f_dist <= 5:
            self.lbl_dist_front.config(text=f'FRONT (D22/23)\n{f_dist} cm\n[🛑 STOP OBSTACLE]', bg='#c0392b', fg='#ffffff')
        elif f_dist < 20:
            self.lbl_dist_front.config(text=f'FRONT (D22/23)\n{f_dist} cm\n[Caution Ahead]', bg='#e67e22', fg='#ffffff')
        else:
            self.lbl_dist_front.config(text=f'FRONT (D22/23)\n{f_dist} cm\n[Safe]', bg='#222f3e', fg='#1dd1a1')

        # Right Gauge
        if 0 < r_dist <= 4:
            self.lbl_dist_right.config(text=f'RIGHT (D26/27)\n{r_dist} cm\n[⚠️ CLOSE: Steer Left]', bg='#e74c3c', fg='#ffffff')
        elif r_dist < 15:
            self.lbl_dist_right.config(text=f'RIGHT (D26/27)\n{r_dist} cm\n[Caution]', bg='#e67e22', fg='#ffffff')
        else:
            self.lbl_dist_right.config(text=f'RIGHT (D26/27)\n{r_dist} cm\n[Safe]', bg='#222f3e', fg='#1dd1a1')

        # Gas Telemetry
        mq2 = self.telemetry.get('mq2', 0)
        mq4 = self.telemetry.get('mq4', 0)
        mq7 = self.telemetry.get('mq7', 0)
        temp = self.telemetry.get('temp', 28.0)

        hazard_triggered = False
        hazard_title = ''
        hazard_details = ''

        # Lighter Gas / Butane Detection (MQ-2)
        if mq2 > 300:
            self.lbl_mq2.config(text=f'🔥 MQ-2 (Lighter / Butane / Smoke): 🚨 DANGER ({mq2})', fg='#ff4757')
            hazard_triggered = True
            hazard_title = '🔥 BUTANE / LIGHTER GAS DETECTED!'
            hazard_details = f'MQ-2 Sensor Spike: Value {mq2} (Threshold 300).\nCombustible Hydrocarbon / Butane / Flammable Gas present.'
            self.emergency_gas_type = 'MQ-2 Butane / Lighter Gas'
            self.emergency_value = mq2
        else:
            self.lbl_mq2.config(text=f'🔥 MQ-2 (Lighter / Butane / Smoke): Normal ({mq2})', fg='#1dd1a1')

        # Methane Detection (MQ-4)
        if mq4 > 450:
            self.lbl_mq4.config(text=f'⚠️ MQ-4 (Methane CH4 / Explosive):  🚨 CRITICAL ({mq4})', fg='#ff4757')
            hazard_triggered = True
            hazard_title = '⚠️ EXPLOSIVE METHANE (CH4) LEAK DETECTED!'
            hazard_details = f'MQ-4 Sensor Spike: Value {mq4} (Threshold 450).\nHigh risk of firedamp atmospheric explosion in mine tunnel.'
            self.emergency_gas_type = 'MQ-4 Methane (CH4)'
            self.emergency_value = mq4
        else:
            self.lbl_mq4.config(text=f'⚠️ MQ-4 (Methane CH4 / Explosive):  Normal ({mq4})', fg='#1dd1a1')

        # Carbon Monoxide Detection (MQ-7)
        if mq7 > 320:
            self.lbl_mq7.config(text=f'⚠️ MQ-7 (Carbon Monoxide CO / Toxic): 🚨 HIGH TOXICITY ({mq7})', fg='#ff4757')
            hazard_triggered = True
            hazard_title = '☠️ TOXIC CARBON MONOXIDE (CO) DETECTED!'
            hazard_details = f'MQ-7 Sensor Spike: Value {mq7} (Threshold 320).\nDeadly asphyxiation danger for underground personnel.'
            self.emergency_gas_type = 'MQ-7 Carbon Monoxide (CO)'
            self.emergency_value = mq7
        else:
            self.lbl_mq7.config(text=f'⚠️ MQ-7 (Carbon Monoxide CO / Toxic): Normal ({mq7})', fg='#1dd1a1')

        # Temperature
        if temp > 45.0:
            self.lbl_temp.config(text=f'🌡️ LM35 Temperature:               🔥 THERMAL SPIKE ({temp:.1f} °C)', fg='#ff4757')
            hazard_triggered = True
            hazard_title = '🔥 SUBTERRANEAN THERMAL SPIKE!'
            hazard_details = f'LM35 Sensor: {temp:.1f} °C (Threshold 45.0 °C).\nPossible underground spontaneous combustion / fire.'
            self.emergency_gas_type = 'LM35 Thermal Anomaly'
            self.emergency_value = temp
        else:
            self.lbl_temp.config(text=f'🌡️ LM35 Temperature:               Normal ({temp:.1f} °C)', fg='#1dd1a1')

        motion_char = self.telemetry.get('motion', 'S')
        labels = {'F': 'FORWARD (W) ▲', 'B': 'BACKWARD (S) ▼', 'L': 'TURNING LEFT (A) ◀', 'R': 'TURNING RIGHT (D) ▶', 'S': 'STOPPED ■'}
        self.motion_status.config(text=f'Current Motion: {labels.get(motion_char, "STOPPED")}')

        if hazard_triggered:
            if not self.emergency_active:
                self.emergency_active = True
                self.show_emergency_popup(hazard_title, hazard_details)
        else:
            self.emergency_active = False

    def add_nav_log(self, msg):
        timestamp = time.strftime('%H:%M:%S')
        entry = f'[{timestamp}] {msg}'
        self.log_listbox.insert(tk.END, entry)
        if self.log_listbox.size() > 50:
            self.log_listbox.delete(0)
        self.log_listbox.see(tk.END)

    def show_emergency_popup(self, title, details):
        if self.popup_open:
            return
        self.popup_open = True
        self.popup_window = tk.Toplevel(self.root)
        self.popup_window.title('🚨 CRITICAL MINE ATMOSPHERE EMERGENCY ALERT')
        self.popup_window.geometry('520x280')
        self.popup_window.configure(bg='#2d1316')
        self.popup_window.attributes('-topmost', True)
        self.popup_window.geometry(f'+{self.root.winfo_x() + 400}+{self.root.winfo_y() + 250}')

        p_header = tk.Frame(self.popup_window, bg='#c0392b', height=45)
        p_header.pack(fill=tk.X)
        tk.Label(p_header, text='⚠️ CRITICAL SUBTERRANEAN HAZARD ALERT', fg='white', bg='#c0392b', font=('Segoe UI', 12, 'bold')).pack(pady=8)

        body_frame = tk.Frame(self.popup_window, bg='#2d1316')
        body_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        tk.Label(body_frame, text=title, fg='#ff7675', bg='#2d1316', font=('Segoe UI', 13, 'bold'), wraplength=480).pack(anchor=tk.W, pady=4)
        tk.Label(body_frame, text=details, fg='#dfe6e9', bg='#2d1316', font=('Segoe UI', 10), justify=tk.LEFT, wraplength=480).pack(anchor=tk.W, pady=6)
        tk.Label(body_frame, text='⚡ SYSTEM ACTION: Automatic Rover Standby | Emergency Beacon Broadcasting', 
                 fg='#ffeaa7', bg='#2d1316', font=('Segoe UI', 9, 'bold')).pack(anchor=tk.W, pady=4)

        btn_dismiss = tk.Button(self.popup_window, text='✓ Acknowledge & Continue Reconnaissance', bg='#c0392b', fg='white', 
                                font=('Segoe UI', 10, 'bold'), padx=10, pady=4, command=self.close_popup)
        btn_dismiss.pack(pady=10)

    def close_popup(self):
        if self.popup_window:
            self.popup_window.destroy()
        self.popup_open = False

    def start_emergency_blink_loop(self):
        def blink_worker():
            while self.running:
                if self.emergency_active:
                    self.blink_phase = not self.blink_phase
                    if self.blink_phase:
                        self.root.after(0, lambda: self.header_frame.config(bg='#5c1d24'))
                        self.root.after(0, lambda: self.decision_box.config(bg='#5c1d24'))
                    else:
                        self.root.after(0, lambda: self.header_frame.config(bg='#1a1c29'))
                        self.root.after(0, lambda: self.decision_box.config(bg='#1a1c29'))
                else:
                    self.blink_phase = False
                time.sleep(0.4)

        self.blink_thread = threading.Thread(target=blink_worker, daemon=True)
        self.blink_thread.start()

    def start_radar_animation_loop(self):
        def radar_worker():
            while self.running:
                self.radar_angle += 4 * self.radar_direction
                if self.radar_angle >= 180:
                    self.radar_direction = -1
                elif self.radar_angle <= 0:
                    self.radar_direction = 1

                try:
                    self.root.after(0, self.draw_radar_and_topography)
                except:
                    break
                time.sleep(0.04)

        self.radar_thread = threading.Thread(target=radar_worker, daemon=True)
        self.radar_thread.start()

    def draw_radar_and_topography(self):
        c = self.scanner_canvas
        c.delete('all')
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 50 or h < 50:
            return

        r_w = int(w * 0.48)
        topo_x0 = int(w * 0.52)
        topo_w = w - topo_x0

        # 1. Polar Radar Scanner
        ox = int(r_w / 2)
        oy = h - 20
        max_r = min(ox - 15, oy - 25)

        radii = [0.2, 0.4, 0.6, 0.8, 1.0]
        labels = ['5cm', '15cm', '30cm', '50cm', '100cm']
        for r_pct, lbl in zip(radii, labels):
            rad = max_r * r_pct
            c.create_arc(ox - rad, oy - rad, ox + rad, oy + rad, start=0, extent=180, 
                         style=tk.ARC, outline='#222f3e', width=1, dash=(3, 3))
            c.create_text(ox + rad - 2, oy - 8, text=lbl, fill='#576574', font=('Segoe UI', 7))

        angles_deg = [0, 45, 90, 135, 180]
        angle_names = ['R (+90°)', 'FR (+45°)', 'FRONT (0°)', 'FL (-45°)', 'L (-90°)']
        for ad, an in zip(angles_deg, angle_names):
            ar = math.radians(ad)
            gx = ox + max_r * math.cos(ar)
            gy = oy - max_r * math.sin(ar)
            c.create_line(ox, oy, gx, gy, fill='#222f3e', width=1)
            lx = ox + (max_r + 14) * math.cos(ar)
            ly = oy - (max_r + 14) * math.sin(ar)
            c.create_text(lx, ly, text=an, fill='#8395a7', font=('Segoe UI', 7, 'bold'))

        sweep_rad = math.radians(self.radar_angle)
        sx = ox + max_r * math.cos(sweep_rad)
        sy = oy - max_r * math.sin(sweep_rad)
        c.create_line(ox, oy, sx, sy, fill='#00d2d3', width=2)

        f_dist = self.telemetry.get('front', 100)
        l_dist = self.telemetry.get('left', 100)
        r_dist = self.telemetry.get('right', 100)
        fl_dist = self.telemetry.get('front_left', 100)
        fr_dist = self.telemetry.get('front_right', 100)

        sensor_data = [
            (180, l_dist, 'L'),
            (135, fl_dist, 'FL'),
            (90,  f_dist, 'F'),
            (45,  fr_dist, 'FR'),
            (0,   r_dist, 'R')
        ]

        blip_points = []
        for adeg, dist, name in sensor_data:
            clamped_d = max(1, min(100, dist))
            blip_r = (clamped_d / 100.0) * max_r
            rad = math.radians(adeg)
            bx = ox + blip_r * math.cos(rad)
            by = oy - blip_r * math.sin(rad)
            blip_points.append((bx, by, clamped_d))

            if clamped_d <= 5:
                b_color = '#ff4757'
            elif clamped_d <= 15:
                b_color = '#ffa502'
            else:
                b_color = '#1dd1a1'

            c.create_oval(bx - 4, by - 4, bx + 4, by + 4, fill=b_color, outline='#ffffff', width=1)
            c.create_text(bx, by - 8, text=f'{dist}cm', fill=b_color, font=('Segoe UI', 7, 'bold'))

        if len(blip_points) >= 2:
            poly_coords = [ox, oy]
            for bx, by, _ in blip_points:
                poly_coords.extend([bx, by])
            poly_coords.extend([ox, oy])
            c.create_polygon(poly_coords, fill='#00d2d3', outline='#00d2d3', stipple='gray25', width=1)

        c.create_text(ox, 12, text='180° RADAR SWEEP SCANNER', fill='#00d2d3', font=('Segoe UI', 8, 'bold'))

        # 2. Topography Profile
        c.create_text(topo_x0 + topo_w / 2, 12, text='FRONT TERRAIN TOPOGRAPHY ELEVATION CONTOUR', fill='#00d2d3', font=('Segoe UI', 8, 'bold'))
        
        ty_bottom = h - 25
        ty_top = 35
        th_max = ty_bottom - ty_top

        c.create_line(topo_x0, ty_bottom, topo_x0 + topo_w, ty_bottom, fill='#222f3e', width=1)
        
        topo_coords = [topo_x0, ty_bottom]
        xs = [topo_x0, 
              topo_x0 + int(topo_w * 0.25), 
              topo_x0 + int(topo_w * 0.50), 
              topo_x0 + int(topo_w * 0.75), 
              topo_x0 + topo_w]
        
        dists = [l_dist, fl_dist, f_dist, fr_dist, r_dist]
        labels_x = ['Left', 'F-Left', 'Center (Front)', 'F-Right', 'Right']

        for px, d_val, lx in zip(xs, dists, labels_x):
            clamped_d = max(1, min(100, d_val))
            proximity_factor = (100.0 - clamped_d) / 100.0
            py = ty_bottom - (proximity_factor * th_max)
            topo_coords.extend([px, py])

            c.create_text(px, ty_bottom + 12, text=lx, fill='#8395a7', font=('Segoe UI', 7))
            
            p_col = '#ff4757' if clamped_d <= 5 else ('#ffa502' if clamped_d <= 15 else '#1dd1a1')
            c.create_oval(px - 3, py - 3, px + 3, py + 3, fill=p_col, outline='white')
            c.create_text(px, py - 8, text=f'{d_val}cm', fill=p_col, font=('Segoe UI', 7, 'bold'))

        topo_coords.extend([topo_x0 + topo_w, ty_bottom])

        top_color = '#ff4757' if (f_dist <= 5 or l_dist <= 4 or r_dist <= 4) else '#0984e3'
        c.create_polygon(topo_coords, fill=top_color, outline='#74b9ff', width=2, stipple='gray50')

    def simulate_hazard(self, hazard_type):
        self.sim_mode = True
        self.btn_sim.config(text='🎮 Virtual Simulator: ON', bg='#10ac84', fg='white')
        if hazard_type == 'LIGHTER_GAS':
            self.telemetry['mq2'] = 520
            self.add_nav_log('🔥 [SIMULATION] Lighter Gas (Butane / LPG) released near MQ-2 sensor!')
        self.process_telemetry_and_navigation()

    def simulate_obstacle(self, direction):
        self.sim_mode = True
        self.btn_sim.config(text='🎮 Virtual Simulator: ON', bg='#10ac84', fg='white')
        if direction == 'FRONT':
            self.telemetry['front'] = 4
            self.add_nav_log('🛑 [SIMULATION] Front Obstacle placed at 4 cm!')
        elif direction == 'LEFT':
            self.telemetry['left'] = 3
            self.add_nav_log('⚠️ [SIMULATION] Left Wall placed at 3 cm!')
        elif direction == 'RIGHT':
            self.telemetry['right'] = 3
            self.add_nav_log('⚠️ [SIMULATION] Right Wall placed at 3 cm!')
        self.process_telemetry_and_navigation()

    def reset_simulation(self):
        self.telemetry['front'] = 100
        self.telemetry['left'] = 100
        self.telemetry['right'] = 100
        self.telemetry['mq2'] = 110
        self.telemetry['mq4'] = 120
        self.telemetry['mq7'] = 90
        self.telemetry['temp'] = 28.5
        self.emergency_active = False
        self.close_popup()
        self.add_nav_log('🔄 Environment reset: All paths clear, atmosphere normal.')
        self.process_telemetry_and_navigation()

    def send_command(self, cmd):
        m_map = {'W': 'F', 'w': 'F', 'S': 'B', 's': 'B', 'A': 'L', 'a': 'L', 'D': 'R', 'd': 'R', ' ': 'S'}
        target_motion = m_map.get(cmd, 'S')

        if target_motion == 'F' and (0 < self.telemetry.get('front', 100) <= 5):
            self.add_nav_log('🚫 Forward Command Rejected: Critical Front Obstacle (<5cm)!')
            self.telemetry['motion'] = 'S'
            self.process_telemetry_and_navigation()
            return

        if self.serial_connected and self.ser:
            try:
                self.ser.write(cmd.encode('utf-8'))
            except Exception as e:
                print('Serial send error:', e)
        else:
            self.telemetry['motion'] = target_motion
            self.process_telemetry_and_navigation()

    def bind_keyboard_controls(self):
        self.root.bind('<w>', lambda e: self.send_command('W'))
        self.root.bind('<W>', lambda e: self.send_command('W'))
        self.root.bind('<s>', lambda e: self.send_command('S'))
        self.root.bind('<S>', lambda e: self.send_command('S'))
        self.root.bind('<a>', lambda e: self.send_command('A'))
        self.root.bind('<A>', lambda e: self.send_command('A'))
        self.root.bind('<d>', lambda e: self.send_command('D'))
        self.root.bind('<D>', lambda e: self.send_command('D'))
        self.root.bind('<space>', lambda e: self.send_command(' '))
        self.root.bind('<c>', lambda e: self.cycle_camera())
        self.root.bind('<C>', lambda e: self.cycle_camera())

    def start_video_stream(self):
        # Open default camera (Index 1 = Laptop Integrated Webcam)
        with self.cam_lock:
            try:
                self.cap = cv2.VideoCapture(self.current_cam_idx, cv2.CAP_DSHOW)
                if not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(self.current_cam_idx)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                print(f"[Vision] Connected to Camera Index {self.current_cam_idx} (Integrated Laptop Webcam)")
            except Exception as e:
                print(f'Camera {self.current_cam_idx} init error:', e)
                
        self.video_thread = threading.Thread(target=self.video_loop, daemon=True)
        self.video_thread.start()

    def video_loop(self):
        frame_count = 0
        while self.running:
            frame = None
            with self.cam_lock:
                if self.cap and self.cap.isOpened():
                    try:
                        ret, raw_frame = self.cap.read()
                        if ret and raw_frame is not None:
                            frame = raw_frame
                    except:
                        frame = None

            if frame is not None:
                frame = cv2.flip(frame, 1)
                h, w, _ = frame.shape
                
                frame_count += 1
                detected_person = False
                
                if YOLO_AVAILABLE and model is not None:
                    small_frame = cv2.resize(frame, (416, 416))
                    results = model(small_frame, classes=[0], verbose=False)
                    
                    for r in results:
                        boxes = r.boxes
                        for box in boxes:
                            conf = float(box.conf[0])
                            if conf > 0.45:
                                detected_person = True
                                self.confidence_score = conf
                                
                                x1, y1, x2, y2 = box.xyxy[0]
                                x1 = int(x1 * w / 416)
                                y1 = int(y1 * h / 416)
                                x2 = int(x2 * w / 416)
                                y2 = int(y2 * h / 416)

                                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                label_text = f'SURVIVOR DETECTED ({conf*100:.1f}%)'
                                cv2.putText(frame, label_text, (x1, max(y1 - 10, 20)),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                if self.emergency_active and self.blink_phase:
                    red_layer = np.zeros_like(frame, dtype=np.uint8)
                    red_layer[:] = (0, 0, 180)
                    frame = cv2.addWeighted(frame, 0.78, red_layer, 0.22, 0)

                    cv2.rectangle(frame, (0, 0), (w, 45), (0, 0, 200), -1)
                    alert_msg = f'🚨 EMERGENCY: {self.emergency_gas_type} SPIKE ({self.emergency_value})!'
                    cv2.putText(frame, alert_msg, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
                else:
                    cam_tag = f'CAMERA {self.current_cam_idx} ACTIVE'
                    cv2.putText(frame, f'AI MINE VISION HUD: {cam_tag}', (15, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 210, 211), 2)

                try:
                    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img_pil = Image.fromarray(img_rgb)
                    img_pil = img_pil.resize((580, 360))
                    img_tk = ImageTk.PhotoImage(image=img_pil)

                    self.video_label.imgtk = img_tk
                    self.video_label.configure(image=img_tk)
                except:
                    break

            time.sleep(0.03)

    def on_closing(self):
        self.running = False
        self.serial_connected = False
        with self.cam_lock:
            if self.cap:
                try:
                    self.cap.release()
                except:
                    pass
        if self.ser:
            try:
                self.ser.close()
            except:
                pass
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = MineRescueRoverStation(root)
    root.protocol('WM_DELETE_WINDOW', app.on_closing)
    root.mainloop()
