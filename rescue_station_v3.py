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

# Global YOLO state
model = None
YOLO_AVAILABLE = False
yolo_loading = True

def load_yolo_background():
    global model, YOLO_AVAILABLE, yolo_loading
    try:
        from ultralytics import YOLO
        print('[AI V3] Loading YOLOv8n pretrained model...')
        model = YOLO('yolov8n.pt')
        YOLO_AVAILABLE = True
        print('[AI V3] YOLOv8n loaded successfully!')
    except Exception as e:
        YOLO_AVAILABLE = False
        print(f'[AI Warning] YOLOv8 not available ({e}).')
    finally:
        yolo_loading = False

threading.Thread(target=load_yolo_background, daemon=True).start()

class MineRescueRoverStationV3:
    def __init__(self, root):
        self.root = root
        self.root.title('M.I.N.E.R.S. V3 - Standalone Map-Guided Autonomous Navigation System')
        self.root.geometry('1300x780')
        self.root.minsize(1080, 680)
        self.root.configure(bg='#0f111a')
        
        try:
            self.root.state('zoomed')
        except:
            pass

        # Hardware & Comms State
        self.ser = None
        self.serial_connected = False
        self.sim_mode = True  # Default to active simulation mode for easy map testing
        
        # Telemetry State (5 Ultrasonics + Multi-Gas + Rain + Autonomous Map State)
        self.telemetry = {
            'front': 100, 
            'front_left': 100, 
            'front_right': 100,
            'left': 100, 
            'right': 100,
            'mq2': 110, 
            'mq4': 120, 
            'mq7': 90,
            'rain': 1023,
            'temp': 28.5,
            'motion': 'S',
            'dist_m': 0.0,
            'state': 1  # 1 = NAVIGATING_CORRIDOR
        }
        
        # Map Specification State
        self.map_corridor_len = 10.0  # 10 meters
        self.map_corridor_width = 2.0  # 2 meters
        self.map_turn = 'RIGHT'       # Turn right at intersection
        self.map_post_turn_len = 3.0  # 3 meters post-turn
        
        self.state_names = {
            0: 'IDLE / STANDBY',
            1: 'NAVIGATING 10m CORRIDOR',
            2: 'BYPASSING OBSTACLE (AUTONOMOUS DETOUR)',
            3: 'T-JUNCTION INTERSECTION DETECTED',
            4: 'EXECUTING 90° RIGHT TURN',
            5: 'NAVIGATING POST-TURN BRANCH (3m)',
            6: 'MISSION COMPLETE / DESTINATION REACHED',
            7: 'EMERGENCY HALT'
        }

        # Video State
        self.cap = None
        self.current_cam_idx = 1
        self.cam_lock = threading.Lock()
        self.running = True

        self.setup_ui()
        self.bind_keyboard_controls()
        
        self.start_video_stream()
        self.start_radar_animation_loop()

    def setup_ui(self):
        # 1. Top Title Header
        header_frame = tk.Frame(self.root, bg='#16192b', height=48)
        header_frame.pack(fill=tk.X, padx=6, pady=(4, 2))
        
        title_lbl = tk.Label(header_frame, text='⛏️ M.I.N.E.R.S. VERSION-3: STANDALONE AUTONOMOUS MAP NAVIGATION', 
                             fg='#00d2d3', bg='#16192b', font=('Segoe UI', 13, 'bold'))
        title_lbl.pack(side=tk.LEFT, padx=12, pady=6)

        sih_lbl = tk.Label(header_frame, text='SIH PS ID: 26039 | Autonomous Map-Guided Rover Engine', 
                           fg='#a4b0be', bg='#16192b', font=('Segoe UI', 9, 'italic'))
        sih_lbl.pack(side=tk.LEFT, padx=8, pady=6)

        self.btn_sim = tk.Button(header_frame, text='🎮 Mode: VIRTUAL SIMULATOR', bg='#10ac84', fg='white', 
                                 font=('Segoe UI', 9, 'bold'), padx=8, pady=2, command=self.toggle_sim_mode)
        self.btn_sim.pack(side=tk.RIGHT, padx=12, pady=6)

        # 2. Map Configuration & Connection Toolbar
        conn_frame = tk.Frame(self.root, bg='#0f111a')
        conn_frame.pack(fill=tk.X, padx=10, pady=2)

        tk.Label(conn_frame, text='COM Port:', fg='#ffffff', bg='#0f111a', font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT, padx=4)
        self.port_combo = ttk.Combobox(conn_frame, width=12, state='readonly')
        self.refresh_ports()
        self.port_combo.pack(side=tk.LEFT, padx=4)

        btn_refresh = tk.Button(conn_frame, text='🔄 Refresh', bg='#485460', fg='white', font=('Segoe UI', 8), command=self.refresh_ports)
        btn_refresh.pack(side=tk.LEFT, padx=3)

        self.btn_connect = tk.Button(conn_frame, text='⚡ Connect Mega (Serial / ESP Wi-Fi)', bg='#341f97', fg='white', 
                                     font=('Segoe UI', 9, 'bold'), padx=8, command=self.toggle_serial)
        self.btn_connect.pack(side=tk.LEFT, padx=6)

        # Camera Source Selector
        tk.Label(conn_frame, text='🎥 Cam:', fg='#00d2d3', bg='#0f111a', font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT, padx=(10, 2))
        self.cam_combo = ttk.Combobox(conn_frame, width=22, state='readonly')
        self.cam_combo['values'] = ['Camera 1: Laptop Webcam', 'Camera 0: External Cam']
        self.cam_combo.current(0)
        self.cam_combo.pack(side=tk.LEFT, padx=2)

        self.status_lbl = tk.Label(conn_frame, text='Status: Standalone Autonomous Simulator Ready', fg='#1dd1a1', bg='#0f111a', font=('Segoe UI', 9, 'bold'))
        self.status_lbl.pack(side=tk.LEFT, padx=8)

        # 3. Main Dashboard Body
        main_body = tk.Frame(self.root, bg='#0f111a')
        main_body.pack(fill=tk.BOTH, expand=True, padx=8, pady=2)

        # Left Column: Video & Interactive Map Visualizer
        left_col = tk.Frame(main_body, bg='#0f111a')
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3, pady=2)

        self.video_box = tk.LabelFrame(left_col, text='🎥 Live Vision Feed & AI Detection', fg='#00d2d3', bg='#16192b', font=('Segoe UI', 9, 'bold'))
        self.video_box.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self.video_label = tk.Label(self.video_box, bg='#000000')
        self.video_label.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)

        # Map Visualizer & State Banner
        self.map_box = tk.LabelFrame(left_col, text='🗺️ Live Autonomous Map Navigation Visualizer (Text Map Specs: 10m Length, 2m Width -> Right Turn)', 
                                    fg='#00d2d3', bg='#16192b', font=('Segoe UI', 9, 'bold'))
        self.map_box.pack(fill=tk.X, padx=2, pady=2)

        self.map_canvas = tk.Canvas(self.map_box, bg='#080910', height=210, highlightthickness=0)
        self.map_canvas.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)

        # Right Column: Controls, Telemetry & Sensor Gauges
        right_col = tk.Frame(main_body, bg='#0f111a', width=520)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, padx=3, pady=2)

        # State Banner Card
        state_card = tk.LabelFrame(right_col, text='🤖 Autonomous Navigation State Machine', fg='#00d2d3', bg='#16192b', font=('Segoe UI', 9, 'bold'))
        state_card.pack(fill=tk.X, pady=2)

        self.lbl_state = tk.Label(state_card, text='STATE: NAVIGATING 10m CORRIDOR (Progress: 0.0m / 10.0m)', 
                                  fg='#1dd1a1', bg='#16192b', font=('Segoe UI', 10, 'bold'), wraplength=480, justify=tk.LEFT)
        self.lbl_state.pack(fill=tk.X, padx=6, pady=6)

        # Log Box
        log_frame = tk.LabelFrame(right_col, text='📝 Live Autonomous Decision Log', fg='#00d2d3', bg='#16192b', font=('Segoe UI', 8, 'bold'))
        log_frame.pack(fill=tk.X, pady=2)

        self.log_listbox = tk.Listbox(log_frame, bg='#080910', fg='#c8d6e5', height=4, font=('Consolas', 8), bd=0, highlightthickness=0)
        self.log_listbox.pack(fill=tk.X, padx=4, pady=2)
        self.add_nav_log('V3 System active. Standalone Map Engine Initialized.')

        # 5-Ultrasonic Gauges
        u_card = tk.LabelFrame(right_col, text='📐 5-Point Ultrasonic Obstacle Gauges', fg='#00d2d3', bg='#16192b', font=('Segoe UI', 8, 'bold'))
        u_card.pack(fill=tk.X, pady=2)

        u_grid = tk.Frame(u_card, bg='#16192b')
        u_grid.pack(fill=tk.X, padx=3, pady=2)

        self.lbl_dist_left  = tk.Label(u_grid, text='LEFT\n100cm', bg='#222f3e', fg='#1dd1a1', font=('Segoe UI', 8, 'bold'), width=9, height=3)
        self.lbl_dist_left.grid(row=0, column=0, padx=1, sticky='ew')
        self.lbl_dist_fl    = tk.Label(u_grid, text='F-LEFT\n100cm', bg='#222f3e', fg='#1dd1a1', font=('Segoe UI', 8, 'bold'), width=9, height=3)
        self.lbl_dist_fl.grid(row=0, column=1, padx=1, sticky='ew')
        self.lbl_dist_front = tk.Label(u_grid, text='FRONT\n100cm', bg='#222f3e', fg='#1dd1a1', font=('Segoe UI', 8, 'bold'), width=9, height=3)
        self.lbl_dist_front.grid(row=0, column=2, padx=1, sticky='ew')
        self.lbl_dist_fr    = tk.Label(u_grid, text='F-RIGHT\n100cm', bg='#222f3e', fg='#1dd1a1', font=('Segoe UI', 8, 'bold'), width=9, height=3)
        self.lbl_dist_fr.grid(row=0, column=3, padx=1, sticky='ew')
        self.lbl_dist_right = tk.Label(u_grid, text='RIGHT\n100cm', bg='#222f3e', fg='#1dd1a1', font=('Segoe UI', 8, 'bold'), width=9, height=3)
        self.lbl_dist_right.grid(row=0, column=4, padx=1, sticky='ew')

        for i in range(5):
            u_grid.columnconfigure(i, weight=1)

        # Environmental Sensors Card
        gas_card = tk.LabelFrame(right_col, text='☣️ Gas, Rain & Temperature Sensors', fg='#00d2d3', bg='#16192b', font=('Segoe UI', 8, 'bold'))
        gas_card.pack(fill=tk.X, pady=2)

        gas_inner = tk.Frame(gas_card, bg='#16192b')
        gas_inner.pack(fill=tk.X, padx=6, pady=2)

        self.lbl_gas = tk.Label(gas_inner, text='🔥 MQ-2: Normal (110) | ⚠️ MQ-4: Normal (120) | ⚠️ MQ-7: Normal (90)', fg='#1dd1a1', bg='#16192b', font=('Segoe UI', 8, 'bold'))
        self.lbl_gas.pack(anchor=tk.W, pady=1)

        self.lbl_rain = tk.Label(gas_inner, text='🌧️ Rain Sensor (A3): Normal (Dry - 1023) | 🌡️ Temp: 28.5 °C', fg='#1dd1a1', bg='#16192b', font=('Segoe UI', 8, 'bold'))
        self.lbl_rain.pack(anchor=tk.W, pady=1)

        # Interactive Simulation Controls
        ctrl_card = tk.LabelFrame(right_col, text='🎮 Interactive Simulation Controls & Triggers', fg='#00d2d3', bg='#16192b', font=('Segoe UI', 8, 'bold'))
        ctrl_card.pack(fill=tk.BOTH, expand=True, pady=2)

        btn_grid = tk.Frame(ctrl_card, bg='#16192b')
        btn_grid.pack(pady=2)

        tk.Button(btn_grid, text='▶ Advance +1.0m', bg='#0984e3', fg='white', font=('Segoe UI', 8, 'bold'), 
                  command=lambda: self.sim_advance_dist(1.0)).grid(row=0, column=0, padx=2, pady=2)
        tk.Button(btn_grid, text='🛑 Place Obstacle Ahead', bg='#e17055', fg='white', font=('Segoe UI', 8, 'bold'), 
                  command=self.sim_trigger_obstacle).grid(row=0, column=1, padx=2, pady=2)
        tk.Button(btn_grid, text='↪️ Trigger Intersection', bg='#a55eea', fg='white', font=('Segoe UI', 8, 'bold'), 
                  command=self.sim_trigger_intersection).grid(row=0, column=2, padx=2, pady=2)
        tk.Button(btn_grid, text='🔄 Reset Map Mission', bg='#27ae60', fg='white', font=('Segoe UI', 8, 'bold'), 
                  command=self.sim_reset_mission).grid(row=1, column=1, padx=2, pady=2)

    def refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.current(0)

    def toggle_sim_mode(self):
        self.sim_mode = not self.sim_mode
        if self.sim_mode:
            self.btn_sim.config(text='🎮 Mode: VIRTUAL SIMULATOR', bg='#10ac84', fg='white')
            self.status_lbl.config(text='Status: Standalone Autonomous Simulator Active', fg='#1dd1a1')
        else:
            self.btn_sim.config(text='🎮 Mode: HARDWARE MEGA', bg='#3d3d5c', fg='#dfe4ea')
            self.status_lbl.config(text='Status: Hardware Mode (Connect Arduino Mega)', fg='#f39c12')

    def toggle_serial(self):
        if not self.serial_connected:
            port = self.port_combo.get()
            if not port:
                return
            try:
                self.ser = serial.Serial(port, 115200, timeout=0.1)
                time.sleep(1.5)
                self.serial_connected = True
                self.btn_connect.config(text='🔌 Disconnect', bg='#ee5253')
                self.status_lbl.config(text=f'Connected to Mega ({port})', fg='#1dd1a1')
                threading.Thread(target=self.read_serial_loop, daemon=True).start()
            except Exception as e:
                self.status_lbl.config(text=f'Serial Error: {e}', fg='#ff6b6b')
        else:
            self.serial_connected = False
            if self.ser:
                try: self.ser.close()
                except: pass
            self.btn_connect.config(text='⚡ Connect Mega', bg='#341f97')

    def read_serial_loop(self):
        while self.serial_connected and self.running:
            try:
                if self.ser and self.ser.in_waiting:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if line.startswith('{') and line.endswith('}'):
                        data = json.loads(line)
                        self.telemetry.update(data)
                        self.root.after(0, self.update_dashboard)
            except:
                pass
            time.sleep(0.02)

    def sim_advance_dist(self, amount):
        st = self.telemetry.get('state', 1)
        if st in [1, 5]:
            self.telemetry['dist_m'] += amount
            self.add_nav_log(f'🎮 [SIM] Rover advanced +{amount:.1f}m. Total: {self.telemetry["dist_m"]:.1f}m')
            if st == 1 and self.telemetry['dist_m'] >= 10.0:
                self.telemetry['state'] = 3
                self.add_nav_log('🎯 10m Target Distance Reached! T-Junction Intersection Detected.')
            elif st == 5 and self.telemetry['dist_m'] >= 13.0:
                self.telemetry['state'] = 6
                self.add_nav_log('🏁 Final 3m Post-Turn Segment Complete! MISSION SUCCEEDED!')
        self.update_dashboard()

    def sim_trigger_obstacle(self):
        self.telemetry['front'] = 4
        self.telemetry['state'] = 2
        self.add_nav_log('🛑 [SIM] Obstacle placed ahead (4cm). Triggering Autonomous Bypassing Detour!')
        self.root.after(1500, self.clear_sim_obstacle)
        self.update_dashboard()

    def clear_sim_obstacle(self):
        self.telemetry['front'] = 100
        self.telemetry['state'] = 1
        self.add_nav_log('🟢 [SIM] Obstacle bypassed! Re-aligned forward into 10m corridor.')
        self.update_dashboard()

    def sim_trigger_intersection(self):
        self.telemetry['right'] = 150
        self.telemetry['state'] = 3
        self.add_nav_log('↪️ [SIM] Side-Right Wall Opening Detected (>120cm). T-Junction Reached!')
        self.root.after(1000, self.execute_sim_turn)
        self.update_dashboard()

    def execute_sim_turn(self):
        self.telemetry['state'] = 4
        self.add_nav_log('🔄 Executing Calibrated 90° RIGHT Turn into Right Branch...')
        self.root.after(1200, self.complete_sim_turn)
        self.update_dashboard()

    def complete_sim_turn(self):
        self.telemetry['state'] = 5
        self.telemetry['right'] = 100
        self.add_nav_log('✅ Right Turn Executed! Navigating Post-Turn 3m Branch...')
        self.update_dashboard()

    def sim_reset_mission(self):
        self.telemetry['front'] = 100
        self.telemetry['left'] = 100
        self.telemetry['right'] = 100
        self.telemetry['dist_m'] = 0.0
        self.telemetry['state'] = 1
        self.add_nav_log('🔄 Mission Reset: Rover placed at starting point of 10m corridor.')
        self.update_dashboard()

    def update_dashboard(self):
        st_val = self.telemetry.get('state', 1)
        st_text = self.state_names.get(st_val, f'STATE {st_val}')
        dist_m = self.telemetry.get('dist_m', 0.0)

        self.lbl_state.config(text=f'STATE: {st_text}\nProgress: {dist_m:.1f}m / 10.0m Corridor')

        # Update Gauges
        def set_u_lbl(lbl, text, val):
            if val <= 5:
                lbl.config(text=f'{text}\n{val}cm\n[🛑 STOP]', bg='#c0392b', fg='white')
            elif val <= 20:
                lbl.config(text=f'{text}\n{val}cm\n[⚠️ Detour]', bg='#e67e22', fg='white')
            else:
                lbl.config(text=f'{text}\n{val}cm\n[Safe]', bg='#222f3e', fg='#1dd1a1')

        set_u_lbl(self.lbl_dist_left, 'LEFT', self.telemetry.get('left', 100))
        set_u_lbl(self.lbl_dist_fl, 'F-LEFT', self.telemetry.get('front_left', 100))
        set_u_lbl(self.lbl_dist_front, 'FRONT', self.telemetry.get('front', 100))
        set_u_lbl(self.lbl_dist_fr, 'F-RIGHT', self.telemetry.get('front_right', 100))
        set_u_lbl(self.lbl_dist_right, 'RIGHT', self.telemetry.get('right', 100))

    def add_nav_log(self, msg):
        ts = time.strftime('%H:%M:%S')
        self.log_listbox.insert(tk.END, f'[{ts}] {msg}')
        if self.log_listbox.size() > 50:
            self.log_listbox.delete(0)
        self.log_listbox.see(tk.END)

    def draw_map_visualizer(self):
        c = self.map_canvas
        c.delete('all')
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 50 or h < 50:
            return

        st_val = self.telemetry.get('state', 1)
        dist_m = self.telemetry.get('dist_m', 0.0)

        # Render 2D T-Junction Corridor Map
        # 10m Corridor (vertical/horizontal segment)
        cx0, cy0 = 60, h - 40
        corridor_pixel_len = w * 0.55
        cx1 = cx0 + corridor_pixel_len
        cy1 = cy0

        # Corridor Walls (2m wide representation)
        c.create_line(cx0, cy0 - 25, cx1, cy1 - 25, fill='#34495e', width=3)
        c.create_line(cx0, cy0 + 25, cx1, cy1 + 25, fill='#34495e', width=3)
        c.create_text(cx0 + corridor_pixel_len/2, cy0 + 38, text='Corridor Segment 1 (Length: 10m, Width: 2m)', fill='#8395a7', font=('Segoe UI', 8, 'bold'))

        # Intersection (T-Junction on Right)
        ix0, iy0 = cx1, cy0
        # Right Branch
        c.create_line(ix0, iy0 + 25, ix0, iy0 + 80, fill='#34495e', width=3)
        c.create_line(ix0 + 50, iy0 + 25, ix0 + 50, iy0 + 80, fill='#34495e', width=3)
        c.create_text(ix0 + 25, iy0 + 92, text='Right Branch (3m)', fill='#8395a7', font=('Segoe UI', 8, 'bold'))

        # Left Branch (Closed/Open representation)
        c.create_line(ix0, iy0 - 25, ix0, iy0 - 70, fill='#34495e', width=3)
        c.create_line(ix0 + 50, iy0 - 25, ix0 + 50, iy0 - 70, fill='#34495e', width=3)
        c.create_text(ix0 + 25, iy0 - 82, text='Left Branch', fill='#8395a7', font=('Segoe UI', 8))

        # Calculate Rover Position on Canvas
        clamped_dist = max(0.0, min(10.0, dist_m))
        rover_x = cx0 + (clamped_dist / 10.0) * corridor_pixel_len
        rover_y = cy0

        if st_val in [4, 5, 6]:
            rover_x = ix0 + 25
            post_d = max(0.0, min(3.0, dist_m - 10.0))
            rover_y = iy0 + (post_d / 3.0) * 50

        # Draw Rover Node
        r_color = '#ff4757' if st_val == 2 else ('#a55eea' if st_val in [3, 4] else '#1dd1a1')
        c.create_rectangle(rover_x - 12, rover_y - 10, rover_x + 12, rover_y + 10, fill=r_color, outline='#ffffff', width=2)
        c.create_text(rover_x, rover_y, text='ROVER', fill='black', font=('Segoe UI', 7, 'bold'))

        # Draw Front Sensor Beam
        f_dist = self.telemetry.get('front', 100)
        if f_dist <= 25:
            c.create_line(rover_x + 12, rover_y, rover_x + 35, rover_y, fill='#ff4757', width=3, arrow=tk.LAST)
            c.create_text(rover_x + 45, rover_y - 12, text=f'Obstacle ({f_dist}cm)', fill='#ff4757', font=('Segoe UI', 8, 'bold'))

    def start_radar_animation_loop(self):
        def loop_worker():
            while self.running:
                self.root.after(0, self.draw_map_visualizer)
                time.sleep(0.1)

        threading.Thread(target=loop_worker, daemon=True).start()

    def bind_keyboard_controls(self):
        self.root.bind_all('<Up>', lambda e: self.sim_advance_dist(0.5))
        self.root.bind_all('<Right>', lambda e: self.sim_trigger_intersection())
        self.root.bind_all('<space>', lambda e: self.sim_trigger_obstacle())

    def start_video_stream(self):
        with self.cam_lock:
            try:
                self.cap = cv2.VideoCapture(self.current_cam_idx, cv2.CAP_DSHOW)
                if not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(self.current_cam_idx)
            except:
                pass
        threading.Thread(target=self.video_loop, daemon=True).start()

    def video_loop(self):
        while self.running:
            frame = None
            with self.cam_lock:
                if self.cap and self.cap.isOpened():
                    try:
                        ret, raw = self.cap.read()
                        if ret and raw is not None:
                            frame = raw
                    except:
                        frame = None

            if frame is not None:
                frame = cv2.flip(frame, 1)
                h, w, _ = frame.shape
                cv2.putText(frame, 'M.I.N.E.R.S. V3 - MAP NAVIGATION HUD', (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 210, 211), 2)
                try:
                    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img_pil = Image.fromarray(img_rgb).resize((540, 320))
                    img_tk = ImageTk.PhotoImage(image=img_pil)
                    self.video_label.imgtk = img_tk
                    self.video_label.configure(image=img_tk)
                except:
                    break
            time.sleep(0.04)

if __name__ == '__main__':
    root = tk.Tk()
    app = MineRescueRoverStationV3(root)
    root.mainloop()
