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
        print(f'[AI Warning] YOLOv8 not available ({e}). Running in standard vision mode.')
    finally:
        yolo_loading = False

# Start loading YOLO in background thread immediately so GUI opens with zero delay
threading.Thread(target=load_yolo_background, daemon=True).start()

class MineRescueRoverStationV2:
    def __init__(self, root):
        self.root = root
        self.root.title('AI-Powered Underground Mine Rescue & Reconnaissance System V2 - SIH PS 26039')
        
        # Responsive sizing for standard laptop screens (1366x768, 1920x1080)
        self.root.geometry('1280x750')
        self.root.minsize(1050, 650)
        self.root.configure(bg='#12141d')
        
        try:
            self.root.state('zoomed') # Maximize on Windows for full immersion
        except:
            pass

        # Serial / Hardware State
        self.ser = None
        self.serial_connected = False
        self.sim_mode = False
        self.swap_fl_fr = tk.BooleanVar(master=self.root, value=False)
        
        # Telemetry State (5-Point Ultrasonic Array + Multi-Gas)
        self.telemetry = {
            'front': 100, 
            'front_left': 100, 
            'front_right': 100,
            'left': 100, 
            'right': 100,
            'mq2': 110, # LPG / Butane / Smoke
            'mq4': 120, # Methane CH4
            'mq7': 90,  # Carbon Monoxide CO
            'rain': 1023, # Rain Drop / Water Level Sensor (A3)
            'temp': 28.5,
            'motion': 'S'
        }
        
        # Navigation & Situational Awareness State
        self.nav_decision_text = 'INITIALIZING 5-AXIS SENSORY RADAR & AI ENGINE...'
        self.nav_decision_color = '#00d2d3'
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

        # Video & Camera State
        self.cap = None
        self.current_cam_idx = 1 # Default to Laptop Integrated Camera (Index 1)
        self.cam_lock = threading.Lock()
        self.running = True

        self.setup_ui()
        self.bind_keyboard_controls()
        
        # Start Periodic Loops & Video
        self.start_video_stream()
        self.start_radar_animation_loop()
        self.start_emergency_blink_loop()
        
    def setup_ui(self):
        # 1. Top Header Bar
        self.header_frame = tk.Frame(self.root, bg='#1a1c29', height=48)
        self.header_frame.pack(fill=tk.X, padx=6, pady=(4, 2))
        
        title_lbl = tk.Label(self.header_frame, text='⛏️ AI-POWERED UNDERGROUND MINE SAFETY, MONITORING & RESCUE SYSTEM (V2)', 
                             fg='#00d2d3', bg='#1a1c29', font=('Segoe UI', 13, 'bold'))
        title_lbl.pack(side=tk.LEFT, padx=12, pady=6)

        # SIH Tag
        sih_lbl = tk.Label(self.header_frame, text='SIH PS ID: 26039 | Govt. of Jharkhand', 
                           fg='#a4b0be', bg='#1a1c29', font=('Segoe UI', 9, 'italic'))
        sih_lbl.pack(side=tk.LEFT, padx=8, pady=6)

        # Simulation Mode Toggle Button
        self.btn_sim = tk.Button(self.header_frame, text='🎮 Virtual Simulator: OFF', bg='#3d3d5c', fg='#dfe4ea', 
                                 font=('Segoe UI', 9, 'bold'), padx=8, pady=2, command=self.toggle_sim_mode)
        self.btn_sim.pack(side=tk.RIGHT, padx=12, pady=6)

        # 2. Connection & Sensor Config Bar
        conn_frame = tk.Frame(self.root, bg='#12141d')
        conn_frame.pack(fill=tk.X, padx=10, pady=2)

        tk.Label(conn_frame, text='COM Port:', fg='#ffffff', bg='#12141d', font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT, padx=4)
        self.port_combo = ttk.Combobox(conn_frame, width=12, state='readonly')
        self.refresh_ports()
        self.port_combo.pack(side=tk.LEFT, padx=4)

        btn_refresh = tk.Button(conn_frame, text='🔄 Refresh', bg='#485460', fg='white', font=('Segoe UI', 8), command=self.refresh_ports)
        btn_refresh.pack(side=tk.LEFT, padx=3)

        self.btn_connect = tk.Button(conn_frame, text='⚡ Connect Arduino Mega', bg='#10ac84', fg='white', 
                                     font=('Segoe UI', 9, 'bold'), padx=8, command=self.toggle_serial)
        self.btn_connect.pack(side=tk.LEFT, padx=6)

        # Live Swap Checkbox (in case FL & FR wires are reversed physically)
        chk_swap = tk.Checkbutton(conn_frame, text='🔀 Swap FL/FR', variable=self.swap_fl_fr,
                                  bg='#12141d', fg='#f1c40f', selectcolor='#2c3e50', activebackground='#12141d',
                                  activeforeground='#f1c40f', font=('Segoe UI', 8, 'bold'), command=self.on_swap_changed)
        chk_swap.pack(side=tk.LEFT, padx=6)

        # Camera Source Selector
        tk.Label(conn_frame, text='🎥 Cam:', fg='#00d2d3', bg='#12141d', font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT, padx=(10, 2))
        self.cam_combo = ttk.Combobox(conn_frame, width=22, state='readonly')
        self.populate_camera_list()
        self.cam_combo.pack(side=tk.LEFT, padx=2)
        self.cam_combo.bind('<<ComboboxSelected>>', self.on_camera_dropdown_changed)

        btn_switch_cam = tk.Button(conn_frame, text='🔄 Switch', bg='#341f97', fg='white', 
                                   font=('Segoe UI', 8, 'bold'), padx=4, command=self.cycle_camera)
        btn_switch_cam.pack(side=tk.LEFT, padx=2)

        self.status_lbl = tk.Label(conn_frame, text='Status: Ready', fg='#f39c12', bg='#12141d', font=('Segoe UI', 9, 'bold'))
        self.status_lbl.pack(side=tk.LEFT, padx=8)

        # 3. Main Dashboard Body (Left & Right Split)
        main_body = tk.Frame(self.root, bg='#12141d')
        main_body.pack(fill=tk.BOTH, expand=True, padx=8, pady=2)

        # ==========================================
        # LEFT COLUMN: Live Camera HUD & 180° Radar Map
        # ==========================================
        left_col = tk.Frame(main_body, bg='#12141d')
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3, pady=2)

        # Video Frame
        self.video_box = tk.LabelFrame(left_col, text='🎥 Live AI Reconnaissance Feed (Survivor & Hazard Detection)', 
                                       fg='#00d2d3', bg='#1a1c29', font=('Segoe UI', 9, 'bold'))
        self.video_box.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self.video_label = tk.Label(self.video_box, bg='#000000')
        self.video_label.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)

        # 180° Radar & Topography Contour Scanner Frame
        self.scanner_box = tk.LabelFrame(left_col, text='📡 180° Front Sector Radar & Terrain Topography Elevation Map (5 Sensors)', 
                                         fg='#00d2d3', bg='#1a1c29', font=('Segoe UI', 9, 'bold'))
        self.scanner_box.pack(fill=tk.X, padx=2, pady=(3, 1))

        # Canvas for Radar and Topography Profile
        self.scanner_canvas = tk.Canvas(self.scanner_box, bg='#0d0f18', height=195, highlightthickness=0)
        self.scanner_canvas.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)

        # ==========================================
        # RIGHT COLUMN: Situational Awareness, 5 Gauges & Controls
        # ==========================================
        right_col = tk.Frame(main_body, bg='#12141d', width=540)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, padx=3, pady=2)

        # A. AI Situational Awareness & Movement Action Banner
        self.decision_box = tk.Frame(right_col, bg='#1a1c29', bd=2, relief=tk.RIDGE)
        self.decision_box.pack(fill=tk.X, pady=2)

        tk.Label(self.decision_box, text='🤖 AI AUTONOMOUS NAVIGATION & ENVIRONMENT AWARENESS', 
                 fg='#00d2d3', bg='#1a1c29', font=('Segoe UI', 8, 'bold')).pack(anchor=tk.W, padx=6, pady=(3, 1))

        self.lbl_decision = tk.Label(self.decision_box, text=self.nav_decision_text, 
                                     fg='#1dd1a1', bg='#1a1c29', font=('Segoe UI', 10, 'bold'), wraplength=500, justify=tk.LEFT)
        self.lbl_decision.pack(fill=tk.X, padx=6, pady=(2, 4))

        # B. Real-Time Autonomous Decision Log Box
        log_frame = tk.LabelFrame(right_col, text='📝 Live Reactive Navigation Decision Log', fg='#00d2d3', bg='#1a1c29', font=('Segoe UI', 8, 'bold'))
        log_frame.pack(fill=tk.X, pady=2)

        self.log_listbox = tk.Listbox(log_frame, bg='#0d0f18', fg='#c8d6e5', height=3, font=('Consolas', 8), 
                                      selectbackground='#222f3e', bd=0, highlightthickness=0)
        self.log_listbox.pack(fill=tk.X, padx=4, pady=2)
        self.add_nav_log('V2 System initialized. 5 ultrasonic sensors + multi-gas ready.')

        # C. 5-Point Ultrasonic Collision Distance Gauges
        ultra_card = tk.LabelFrame(right_col, text='📐 5-Point Ultrasonic Obstacle Gauges (Full 180° Sector)', fg='#00d2d3', bg='#1a1c29', font=('Segoe UI', 8, 'bold'))
        ultra_card.pack(fill=tk.X, pady=2)

        u_grid = tk.Frame(ultra_card, bg='#1a1c29')
        u_grid.pack(fill=tk.X, padx=3, pady=2)

        # 1. Left (D24/25)
        self.lbl_dist_left = tk.Label(u_grid, text='LEFT\n(D24/25)\n100cm\n[Safe]', bg='#222f3e', fg='#1dd1a1', 
                                      font=('Segoe UI', 8, 'bold'), width=10, height=4, relief=tk.GROOVE)
        self.lbl_dist_left.grid(row=0, column=0, padx=2, pady=1, sticky='ew')

        # 2. Front-Left (D40/41)
        self.lbl_dist_fl = tk.Label(u_grid, text='F-LEFT\n(D40/41)\n100cm\n[Safe]', bg='#222f3e', fg='#1dd1a1', 
                                    font=('Segoe UI', 8, 'bold'), width=10, height=4, relief=tk.GROOVE)
        self.lbl_dist_fl.grid(row=0, column=1, padx=2, pady=1, sticky='ew')

        # 3. Center Front (D22/23)
        self.lbl_dist_front = tk.Label(u_grid, text='FRONT\n(D22/23)\n100cm\n[Safe]', bg='#222f3e', fg='#1dd1a1', 
                                       font=('Segoe UI', 8, 'bold'), width=10, height=4, relief=tk.GROOVE)
        self.lbl_dist_front.grid(row=0, column=2, padx=2, pady=1, sticky='ew')

        # 4. Front-Right (D42/43)
        self.lbl_dist_fr = tk.Label(u_grid, text='F-RIGHT\n(D42/43)\n100cm\n[Safe]', bg='#222f3e', fg='#1dd1a1', 
                                    font=('Segoe UI', 8, 'bold'), width=10, height=4, relief=tk.GROOVE)
        self.lbl_dist_fr.grid(row=0, column=3, padx=2, pady=1, sticky='ew')

        # 5. Right (D26/27)
        self.lbl_dist_right = tk.Label(u_grid, text='RIGHT\n(D26/27)\n100cm\n[Safe]', bg='#222f3e', fg='#1dd1a1', 
                                       font=('Segoe UI', 8, 'bold'), width=10, height=4, relief=tk.GROOVE)
        self.lbl_dist_right.grid(row=0, column=4, padx=2, pady=1, sticky='ew')

        for i in range(5):
            u_grid.columnconfigure(i, weight=1)

        # D. Gas & Atmospheric Hazards Card
        self.gas_card = tk.LabelFrame(right_col, text='☣️ Atmospheric Toxicity & LPG / Combustible Gas Telemetry', fg='#00d2d3', bg='#1a1c29', font=('Segoe UI', 8, 'bold'))
        self.gas_card.pack(fill=tk.X, pady=2)

        gas_inner = tk.Frame(self.gas_card, bg='#1a1c29')
        gas_inner.pack(fill=tk.X, padx=6, pady=2)

        self.lbl_mq2 = tk.Label(gas_inner, text='🔥 MQ-2 (LPG / Butane / Lighter Gas): Normal (110)', fg='#1dd1a1', bg='#1a1c29', font=('Segoe UI', 8, 'bold'))
        self.lbl_mq2.pack(anchor=tk.W, pady=1)

        self.lbl_mq4 = tk.Label(gas_inner, text='⚠️ MQ-4 (Methane CH4 / Explosive):    Normal (120)', fg='#1dd1a1', bg='#1a1c29', font=('Segoe UI', 8, 'bold'))
        self.lbl_mq4.pack(anchor=tk.W, pady=1)

        self.lbl_mq7 = tk.Label(gas_inner, text='⚠️ MQ-7 (Carbon Monoxide CO / Toxic):   Normal (90)', fg='#1dd1a1', bg='#1a1c29', font=('Segoe UI', 8, 'bold'))
        self.lbl_mq7.pack(anchor=tk.W, pady=1)

        self.lbl_temp = tk.Label(gas_inner, text='🌡️ LM35 Temperature:                 Normal (28.5 °C)', fg='#1dd1a1', bg='#1a1c29', font=('Segoe UI', 8, 'bold'))
        self.lbl_temp.pack(anchor=tk.W, pady=1)

        self.lbl_rain = tk.Label(gas_inner, text='🌧️ Rain / Water Sensor (A3):         Normal (Dry - 1023)', fg='#1dd1a1', bg='#1a1c29', font=('Segoe UI', 8, 'bold'))
        self.lbl_rain.pack(anchor=tk.W, pady=1)

        # E. Control Pad & Simulation Quick-Triggers
        ctrl_card = tk.LabelFrame(right_col, text='🎮 Rover Movement Controls & Simulation Quick-Triggers', fg='#00d2d3', bg='#1a1c29', font=('Segoe UI', 8, 'bold'))
        ctrl_card.pack(fill=tk.BOTH, expand=True, pady=2)

        btn_grid = tk.Frame(ctrl_card, bg='#1a1c29')
        btn_grid.pack(pady=1)

        btn_w = tk.Button(btn_grid, text='▲ FORWARD (W)', width=14, height=1, bg='#341f97', fg='white', font=('Segoe UI', 8, 'bold'), command=lambda: self.send_command('W'))
        btn_w.grid(row=0, column=1, padx=2, pady=1)

        btn_a = tk.Button(btn_grid, text='◀ LEFT (A)', width=11, height=1, bg='#341f97', fg='white', font=('Segoe UI', 8, 'bold'), command=lambda: self.send_command('A'))
        btn_a.grid(row=1, column=0, padx=2, pady=1)

        btn_s_stop = tk.Button(btn_grid, text='■ STOP (Space)', width=14, height=1, bg='#ee5253', fg='white', font=('Segoe UI', 8, 'bold'), command=lambda: self.send_command(' '))
        btn_s_stop.grid(row=1, column=1, padx=2, pady=1)

        btn_d = tk.Button(btn_grid, text='▶ RIGHT (D)', width=11, height=1, bg='#341f97', fg='white', font=('Segoe UI', 8, 'bold'), command=lambda: self.send_command('D'))
        btn_d.grid(row=1, column=2, padx=2, pady=1)

        btn_s_back = tk.Button(btn_grid, text='▼ BACK (S)', width=14, height=1, bg='#341f97', fg='white', font=('Segoe UI', 8, 'bold'), command=lambda: self.send_command('S'))
        btn_s_back.grid(row=2, column=1, padx=2, pady=1)

        self.motion_status = tk.Label(ctrl_card, text='Current Motion: STOPPED', fg='#c8d6e5', bg='#1a1c29', font=('Segoe UI', 8, 'bold'))
        self.motion_status.pack(pady=1)

        # Quick Test Trigger Buttons
        sim_trig_frame = tk.Frame(ctrl_card, bg='#1a1c29')
        sim_trig_frame.pack(fill=tk.X, padx=4, pady=1)

        tk.Label(sim_trig_frame, text='⚡ Quick Interactive Simulation Triggers (Test All 5 Sensors & LPG):', fg='#a4b0be', bg='#1a1c29', font=('Segoe UI', 8, 'italic')).pack(anchor=tk.W)

        btn_row1 = tk.Frame(sim_trig_frame, bg='#1a1c29')
        btn_row1.pack(fill=tk.X, pady=1)

        tk.Button(btn_row1, text='🔥 Test LPG Gas (MQ-2)', bg='#d63031', fg='white', font=('Segoe UI', 8, 'bold'), 
                  command=lambda: self.simulate_hazard('LPG_GAS')).pack(side=tk.LEFT, padx=1, expand=True, fill=tk.X)
        tk.Button(btn_row1, text='💧 Test Water (A3)', bg='#0984e3', fg='white', font=('Segoe UI', 8, 'bold'), 
                  command=lambda: self.simulate_hazard('WATER')).pack(side=tk.LEFT, padx=1, expand=True, fill=tk.X)
        tk.Button(btn_row1, text='🛑 Front (4 cm)', bg='#e17055', fg='white', font=('Segoe UI', 8, 'bold'), 
                  command=lambda: self.simulate_obstacle('FRONT')).pack(side=tk.LEFT, padx=1, expand=True, fill=tk.X)
        tk.Button(btn_row1, text='🔄 Reset Clear', bg='#27ae60', fg='white', font=('Segoe UI', 8, 'bold'), 
                  command=self.reset_simulation).pack(side=tk.LEFT, padx=1, expand=True, fill=tk.X)

        btn_row2 = tk.Frame(sim_trig_frame, bg='#1a1c29')
        btn_row2.pack(fill=tk.X, pady=1)

        tk.Button(btn_row2, text='◀ Left (3 cm)', bg='#e67e22', fg='white', font=('Segoe UI', 7, 'bold'), 
                  command=lambda: self.simulate_obstacle('LEFT')).pack(side=tk.LEFT, padx=1, expand=True, fill=tk.X)
        tk.Button(btn_row2, text='↖️ F-Left (3 cm)', bg='#e67e22', fg='white', font=('Segoe UI', 7, 'bold'), 
                  command=lambda: self.simulate_obstacle('FRONT_LEFT')).pack(side=tk.LEFT, padx=1, expand=True, fill=tk.X)
        tk.Button(btn_row2, text='↗️ F-Right (3 cm)', bg='#e67e22', fg='white', font=('Segoe UI', 7, 'bold'), 
                  command=lambda: self.simulate_obstacle('FRONT_RIGHT')).pack(side=tk.LEFT, padx=1, expand=True, fill=tk.X)
        tk.Button(btn_row2, text='▶ Right (3 cm)', bg='#e67e22', fg='white', font=('Segoe UI', 7, 'bold'), 
                  command=lambda: self.simulate_obstacle('RIGHT')).pack(side=tk.LEFT, padx=1, expand=True, fill=tk.X)

    def populate_camera_list(self):
        self.cam_mapping = [1, 0, 2]
        options = [
            'Camera 1: Laptop Webcam (Default)',
            'Camera 0: Smart Connect (Phone Cam)',
            'Camera 2: Smart Connect (Phone Cam Alt)'
        ]
        self.cam_combo['values'] = options
        self.cam_combo.current(0)

    def on_camera_dropdown_changed(self, event=None):
        combo_sel = self.cam_combo.current()
        if combo_sel >= 0 and combo_sel < len(self.cam_mapping):
            target_idx = self.cam_mapping[combo_sel]
            if target_idx != self.current_cam_idx:
                self.switch_camera_to_index(target_idx)

    def cycle_camera(self):
        cur_pos = 0
        if self.current_cam_idx in self.cam_mapping:
            cur_pos = self.cam_mapping.index(self.current_cam_idx)
        next_pos = (cur_pos + 1) % len(self.cam_mapping)
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

    def on_swap_changed(self):
        state = 'SWAPPED' if self.swap_fl_fr.get() else 'NORMAL'
        self.add_nav_log(f'🔀 Sensor Mapping: Front-Left / Front-Right set to {state}.')
        self.process_telemetry_and_navigation()

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

        raw_fl = self.telemetry.get('front_left', 100)
        raw_fr = self.telemetry.get('front_right', 100)

        # Handle hardware pin swap checkbox
        if self.swap_fl_fr.get():
            fl_dist = raw_fr
            fr_dist = raw_fl
        else:
            fl_dist = raw_fl
            fr_dist = raw_fr

        action_text = ''
        action_color = '#1dd1a1'

        # Reactive Decision Logic for 5 Sensors
        if 0 < f_dist <= 5:
            action_text = f'🛑 STOP: Front Obstacle Detected ({f_dist} cm)! Emergency Braking Active.'
            action_color = '#ff4757'
            self.telemetry['motion'] = 'S'

        elif 0 < fl_dist <= 4:
            action_text = f'⚠️ Obstacle on FRONT-LEFT ({fl_dist} cm)! Adjusting: Steer Slightly RIGHT ↗️'
            action_color = '#ffa502'
            self.telemetry['motion'] = 'R'

        elif 0 < fr_dist <= 4:
            action_text = f'⚠️ Obstacle on FRONT-RIGHT ({fr_dist} cm)! Adjusting: Steer Slightly LEFT ↖️'
            action_color = '#ffa502'
            self.telemetry['motion'] = 'L'

        elif 0 < l_dist <= 4:
            action_text = f'⚠️ Obstacle on 90° LEFT ({l_dist} cm)! Adjusting Trajectory: Steer RIGHT ↗️'
            action_color = '#ffa502'
            self.telemetry['motion'] = 'R'

        elif 0 < r_dist <= 4:
            action_text = f'⚠️ Obstacle on 90° RIGHT ({r_dist} cm)! Adjusting Trajectory: Steer LEFT ↖️'
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
                action_text = f'✅ Environment Aware: Path Clear (F:{f_dist}cm | FL:{fl_dist}cm | FR:{fr_dist}cm | L:{l_dist}cm | R:{r_dist}cm). Rover Standby.'
                action_color = '#00d2d3'

        self.lbl_decision.config(text=action_text, fg=action_color)

        if action_text != self.last_logged_action:
            self.add_nav_log(action_text)
            self.last_logged_action = action_text

        # Helper to update gauge cards
        def update_gauge(lbl, name, pin, dist, stop_th=5, close_th=15):
            if 0 < dist <= stop_th:
                lbl.config(text=f'{name}\n({pin})\n{dist}cm\n[🛑 CLOSE]', bg='#c0392b', fg='#ffffff')
            elif dist <= close_th:
                lbl.config(text=f'{name}\n({pin})\n{dist}cm\n[⚠️ Caution]', bg='#e67e22', fg='#ffffff')
            else:
                lbl.config(text=f'{name}\n({pin})\n{dist}cm\n[Safe]', bg='#222f3e', fg='#1dd1a1')

        # Update all 5 Gauge Cards
        update_gauge(self.lbl_dist_left, 'LEFT', 'D24/25', l_dist, 4, 15)
        update_gauge(self.lbl_dist_fl, 'F-LEFT', 'D40/41', fl_dist, 4, 15)
        update_gauge(self.lbl_dist_front, 'FRONT', 'D22/23', f_dist, 5, 20)
        update_gauge(self.lbl_dist_fr, 'F-RIGHT', 'D42/43', fr_dist, 4, 15)
        update_gauge(self.lbl_dist_right, 'RIGHT', 'D26/27', r_dist, 4, 15)

        # Gas & Atmospheric Telemetry (Calibrated for LPG / Lighter Gas)
        mq2 = self.telemetry.get('mq2', 0)
        mq4 = self.telemetry.get('mq4', 0)
        mq7 = self.telemetry.get('mq7', 0)
        temp = self.telemetry.get('temp', 28.0)

        hazard_triggered = False
        hazard_title = ''
        hazard_details = ''

        # LPG / Butane / Lighter Gas Detection (MQ-2) - Threshold calibrated to 260
        if mq2 > 260:
            self.lbl_mq2.config(text=f'🔥 MQ-2 (LPG / Butane / Lighter Gas): 🚨 DANGER ({mq2})', fg='#ff4757')
            hazard_triggered = True
            hazard_title = '🔥 COMBUSTIBLE LPG / BUTANE GAS LEAK DETECTED!'
            hazard_details = f'MQ-2 Sensor Spike: Value {mq2} (Threshold 260).\nHigh concentration of LPG / Butane / Combustible Gas detected in corridor.'
            self.emergency_gas_type = 'MQ-2 LPG / Butane Gas'
            self.emergency_value = mq2
        else:
            self.lbl_mq2.config(text=f'🔥 MQ-2 (LPG / Butane / Lighter Gas): Normal ({mq2})', fg='#1dd1a1')

        # Methane Detection (MQ-4)
        if mq4 > 450:
            self.lbl_mq4.config(text=f'⚠️ MQ-4 (Methane CH4 / Explosive):    🚨 CRITICAL ({mq4})', fg='#ff4757')
            hazard_triggered = True
            hazard_title = '⚠️ EXPLOSIVE METHANE (CH4) LEAK DETECTED!'
            hazard_details = f'MQ-4 Sensor Spike: Value {mq4} (Threshold 450).\nHigh risk of firedamp atmospheric explosion in mine tunnel.'
            self.emergency_gas_type = 'MQ-4 Methane (CH4)'
            self.emergency_value = mq4
        else:
            self.lbl_mq4.config(text=f'⚠️ MQ-4 (Methane CH4 / Explosive):    Normal ({mq4})', fg='#1dd1a1')

        # Carbon Monoxide Detection (MQ-7)
        if mq7 > 320:
            self.lbl_mq7.config(text=f'⚠️ MQ-7 (Carbon Monoxide CO / Toxic):   🚨 HIGH TOXICITY ({mq7})', fg='#ff4757')
            hazard_triggered = True
            hazard_title = '☠️ TOXIC CARBON MONOXIDE (CO) DETECTED!'
            hazard_details = f'MQ-7 Sensor Spike: Value {mq7} (Threshold 320).\nDeadly asphyxiation danger for underground personnel.'
            self.emergency_gas_type = 'MQ-7 Carbon Monoxide (CO)'
            self.emergency_value = mq7
        else:
            self.lbl_mq7.config(text=f'⚠️ MQ-7 (Carbon Monoxide CO / Toxic):   Normal ({mq7})', fg='#1dd1a1')

        # Temperature (LM35)
        if temp > 45.0:
            self.lbl_temp.config(text=f'🌡️ LM35 Temperature:                 🔥 THERMAL SPIKE ({temp:.1f} °C)', fg='#ff4757')
            hazard_triggered = True
            hazard_title = '🔥 SUBTERRANEAN THERMAL SPIKE!'
            hazard_details = f'LM35 Sensor: {temp:.1f} °C (Threshold 45.0 °C).\nPossible underground spontaneous combustion / fire.'
            self.emergency_gas_type = 'LM35 Thermal Anomaly'
            self.emergency_value = temp
        else:
            self.lbl_temp.config(text=f'🌡️ LM35 Temperature:                 Normal ({temp:.1f} °C)', fg='#1dd1a1')

        # Rain Drop / Water Level Sensor (A3) - Lower value means wet/water present (threshold < 450)
        rain_val = self.telemetry.get('rain', 1023)
        if rain_val < 450:
            self.lbl_rain.config(text=f'🌧️ Rain / Water Sensor (A3):         💧 WATER DETECTED ({rain_val})', fg='#ff4757')
            hazard_triggered = True
            hazard_title = '💧 SUBTERRANEAN WATER ACCUMULATION / FLOOD DETECTED!'
            hazard_details = f'Rain/Water Sensor (A3): Analog Value {rain_val} (Wet threshold < 450).\nSubterranean water accumulation or leakage detected along rover path.'
            self.emergency_gas_type = 'Water Sensor Flooding'
            self.emergency_value = rain_val
        else:
            self.lbl_rain.config(text=f'🌧️ Rain / Water Sensor (A3):         Normal (Dry - {rain_val})', fg='#1dd1a1')

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
        self.popup_window.geometry('520x270')
        self.popup_window.configure(bg='#2d1316')
        self.popup_window.attributes('-topmost', True)
        self.popup_window.geometry(f'+{self.root.winfo_x() + 350}+{self.root.winfo_y() + 200}')

        p_header = tk.Frame(self.popup_window, bg='#c0392b', height=40)
        p_header.pack(fill=tk.X)
        tk.Label(p_header, text='⚠️ CRITICAL SUBTERRANEAN HAZARD ALERT', fg='white', bg='#c0392b', font=('Segoe UI', 11, 'bold')).pack(pady=6)

        body_frame = tk.Frame(self.popup_window, bg='#2d1316')
        body_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        tk.Label(body_frame, text=title, fg='#ff7675', bg='#2d1316', font=('Segoe UI', 12, 'bold'), wraplength=480).pack(anchor=tk.W, pady=3)
        tk.Label(body_frame, text=details, fg='#dfe6e9', bg='#2d1316', font=('Segoe UI', 9), justify=tk.LEFT, wraplength=480).pack(anchor=tk.W, pady=5)
        tk.Label(body_frame, text='⚡ SYSTEM ACTION: Automatic Rover Standby | Emergency Beacon Broadcasting', 
                 fg='#ffeaa7', bg='#2d1316', font=('Segoe UI', 8, 'bold')).pack(anchor=tk.W, pady=3)

        btn_dismiss = tk.Button(self.popup_window, text='✓ Acknowledge & Continue Reconnaissance', bg='#c0392b', fg='white', 
                                font=('Segoe UI', 9, 'bold'), padx=8, pady=3, command=self.close_popup)
        btn_dismiss.pack(pady=8)

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

                self.root.after(0, self.draw_radar_and_topography)
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
        oy = h - 18
        max_r = min(ox - 15, oy - 22)

        radii = [0.2, 0.4, 0.6, 0.8, 1.0]
        labels = ['5cm', '15cm', '30cm', '50cm', '100cm']
        for r_pct, lbl in zip(radii, labels):
            rad = max_r * r_pct
            c.create_arc(ox - rad, oy - rad, ox + rad, oy + rad, start=0, extent=180, 
                         style=tk.ARC, outline='#222f3e', width=1, dash=(3, 3))
            c.create_text(ox + rad - 2, oy - 8, text=lbl, fill='#576574', font=('Segoe UI', 7))

        angles_deg = [0, 45, 90, 135, 180]
        angle_names = ['Right (+90°)', 'F-Right (+45°)', 'Front (0°)', 'F-Left (-45°)', 'Left (-90°)']
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

        raw_fl = self.telemetry.get('front_left', 100)
        raw_fr = self.telemetry.get('front_right', 100)
        fl_dist = raw_fr if self.swap_fl_fr.get() else raw_fl
        fr_dist = raw_fl if self.swap_fl_fr.get() else raw_fr

        # 5-point sensor array mapped in order: Left (180), Front-Left (135), Front (90), Front-Right (45), Right (0)
        sensor_data = [
            (180, l_dist, 'Left'),
            (135, fl_dist, 'FL'),
            (90,  f_dist, 'Front'),
            (45,  fr_dist, 'FR'),
            (0,   r_dist, 'Right')
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

            c.create_oval(bx - 3, by - 3, bx + 3, by + 3, fill=b_color, outline='#ffffff', width=1)
            c.create_text(bx, by - 8, text=f'{dist}cm', fill=b_color, font=('Segoe UI', 7, 'bold'))

        if len(blip_points) >= 2:
            poly_coords = [ox, oy]
            for bx, by, _ in blip_points:
                poly_coords.extend([bx, by])
            poly_coords.extend([ox, oy])
            c.create_polygon(poly_coords, fill='#00d2d3', outline='#00d2d3', stipple='gray25', width=1)

        c.create_text(ox, 10, text='180° RADAR SWEEP (5 SENSORS)', fill='#00d2d3', font=('Segoe UI', 8, 'bold'))

        # 2. Topography Profile (5 Sensors)
        c.create_text(topo_x0 + topo_w / 2, 10, text='FRONT TERRAIN TOPOGRAPHY CONTOUR ("MOUNTAINS & DOWNS")', fill='#00d2d3', font=('Segoe UI', 8, 'bold'))
        
        ty_bottom = h - 22
        ty_top = 30
        th_max = ty_bottom - ty_top

        c.create_line(topo_x0, ty_bottom, topo_x0 + topo_w, ty_bottom, fill='#222f3e', width=1)
        
        topo_coords = [topo_x0, ty_bottom]
        xs = [topo_x0, 
              topo_x0 + int(topo_w * 0.25), 
              topo_x0 + int(topo_w * 0.50), 
              topo_x0 + int(topo_w * 0.75), 
              topo_x0 + topo_w]
        
        dists = [l_dist, fl_dist, f_dist, fr_dist, r_dist]
        labels_x = ['Left', 'F-Left', 'Center', 'F-Right', 'Right']

        for px, d_val, lx in zip(xs, dists, labels_x):
            clamped_d = max(1, min(100, d_val))
            proximity_factor = (100.0 - clamped_d) / 100.0
            py = ty_bottom - (proximity_factor * th_max)
            topo_coords.extend([px, py])

            c.create_text(px, ty_bottom + 10, text=lx, fill='#8395a7', font=('Segoe UI', 7))
            
            p_col = '#ff4757' if clamped_d <= 5 else ('#ffa502' if clamped_d <= 15 else '#1dd1a1')
            c.create_oval(px - 3, py - 3, px + 3, py + 3, fill=p_col, outline='white')
            c.create_text(px, py - 8, text=f'{d_val}cm', fill=p_col, font=('Segoe UI', 7, 'bold'))

        topo_coords.extend([topo_x0 + topo_w, ty_bottom])

        top_color = '#ff4757' if (f_dist <= 5 or fl_dist <= 4 or fr_dist <= 4 or l_dist <= 4 or r_dist <= 4) else '#0984e3'
        c.create_polygon(topo_coords, fill=top_color, outline='#74b9ff', width=2, stipple='gray50')

    def simulate_hazard(self, hazard_type):
        self.sim_mode = True
        self.btn_sim.config(text='🎮 Virtual Simulator: ON', bg='#10ac84', fg='white')
        if hazard_type == 'LPG_GAS':
            self.telemetry['mq2'] = 520
            self.add_nav_log('🔥 [SIMULATION] LPG / Butane Gas released near MQ-2 sensor!')
        elif hazard_type == 'WATER':
            self.telemetry['rain'] = 280
            self.add_nav_log('💧 [SIMULATION] Water droplets detected on Rain Sensor (A3)!')
        self.process_telemetry_and_navigation()

    def simulate_obstacle(self, direction):
        self.sim_mode = True
        self.btn_sim.config(text='🎮 Virtual Simulator: ON', bg='#10ac84', fg='white')
        if direction == 'FRONT':
            self.telemetry['front'] = 4
            self.add_nav_log('🛑 [SIMULATION] Front Obstacle placed at 4 cm!')
        elif direction == 'FRONT_LEFT':
            self.telemetry['front_left'] = 3
            self.add_nav_log('⚠️ [SIMULATION] Front-Left Obstacle placed at 3 cm!')
        elif direction == 'FRONT_RIGHT':
            self.telemetry['front_right'] = 3
            self.add_nav_log('⚠️ [SIMULATION] Front-Right Obstacle placed at 3 cm!')
        elif direction == 'LEFT':
            self.telemetry['left'] = 3
            self.add_nav_log('⚠️ [SIMULATION] Left Wall placed at 3 cm!')
        elif direction == 'RIGHT':
            self.telemetry['right'] = 3
            self.add_nav_log('⚠️ [SIMULATION] Right Wall placed at 3 cm!')
        self.process_telemetry_and_navigation()

    def reset_simulation(self):
        self.telemetry['front'] = 100
        self.telemetry['front_left'] = 100
        self.telemetry['front_right'] = 100
        self.telemetry['left'] = 100
        self.telemetry['right'] = 100
        self.telemetry['mq2'] = 110
        self.telemetry['mq4'] = 120
        self.telemetry['mq7'] = 90
        self.telemetry['rain'] = 1023
        self.telemetry['temp'] = 28.5
        self.emergency_active = False
        self.close_popup()
        self.add_nav_log('🔄 Environment reset: All 5 paths clear, atmosphere normal, sensors dry.')
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
        # Keyboard Movement (Arrow Keys & WASD)
        self.root.bind_all('<Up>', lambda e: self.send_command('W'))
        self.root.bind_all('<Down>', lambda e: self.send_command('S'))
        self.root.bind_all('<Left>', lambda e: self.send_command('A'))
        self.root.bind_all('<Right>', lambda e: self.send_command('D'))

        self.root.bind_all('<w>', lambda e: self.send_command('W'))
        self.root.bind_all('<W>', lambda e: self.send_command('W'))
        self.root.bind_all('<s>', lambda e: self.send_command('S'))
        self.root.bind_all('<S>', lambda e: self.send_command('S'))
        self.root.bind_all('<a>', lambda e: self.send_command('A'))
        self.root.bind_all('<A>', lambda e: self.send_command('A'))
        self.root.bind_all('<d>', lambda e: self.send_command('D'))
        self.root.bind_all('<D>', lambda e: self.send_command('D'))

        # Emergency Stop Keys
        self.root.bind_all('<space>', lambda e: self.send_command(' '))
        self.root.bind_all('<x>', lambda e: self.send_command(' '))
        self.root.bind_all('<X>', lambda e: self.send_command(' '))
        self.root.bind_all('<q>', lambda e: self.send_command(' '))
        self.root.bind_all('<Q>', lambda e: self.send_command(' '))

        # Camera Cycling Shortcut
        self.root.bind_all('<c>', lambda e: self.cycle_camera())
        self.root.bind_all('<C>', lambda e: self.cycle_camera())

    def start_video_stream(self):
        with self.cam_lock:
            try:
                self.cap = cv2.VideoCapture(self.current_cam_idx, cv2.CAP_DSHOW)
                if not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(self.current_cam_idx)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                print(f"[Vision] Connected to Camera Index {self.current_cam_idx} (Laptop Webcam)")
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

                        cv2.rectangle(frame, (0, 0), (w, 40), (0, 0, 200), -1)
                        alert_msg = f'🚨 EMERGENCY: {self.emergency_gas_type} SPIKE ({self.emergency_value})!'
                        cv2.putText(frame, alert_msg, (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    else:
                        cv2.putText(frame, 'AI MINE VISION HUD: ACTIVE', (15, 28),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 210, 211), 2)

                    try:
                        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        img_pil = Image.fromarray(img_rgb)
                        img_pil = img_pil.resize((560, 340))
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
    app = MineRescueRoverStationV2(root)
    root.protocol('WM_DELETE_WINDOW', app.on_closing)
    root.mainloop()
