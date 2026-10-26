import sys
import os
import time
import json
import math
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
import numpy as np
from PIL import Image, ImageTk
import websocket
import serial
import serial.tools.list_ports

# Core Mining Autonomy & Mapping Modules
from live_slam_mapper import LiveSonarSLAM
from autonomous_nav_engine import AutonomousNavEngine
from mine_sim_engine import MineSimulatorEngine
from dxf_map_converter import DxfMapConverter

# Optional YOLOv8 import
YOLO_AVAILABLE = False
yolo_model = None
try:
    from ultralytics import YOLO
    print("[AI Laptop Station] Loading YOLOv8 pretrained model...")
    yolo_model = YOLO("yolov8n.pt")
    YOLO_AVAILABLE = True
    print("[AI Laptop Station] YOLOv8 model active!")
except Exception as e:
    print(f"[AI Notice] YOLOv8 not available ({e}). Standard camera mode active.")

class MinersRescueStationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("M.I.N.E.R.S. Autonomous Mine Rescue Station & SLAM Suite")
        self.root.geometry("1460x860")
        self.root.configure(bg="#0f172a")

        # 1. Autonomy & SLAM Instances
        self.slam = LiveSonarSLAM(map_width_m=20.0, map_height_m=20.0, resolution_m=0.05)
        self.autonav = AutonomousNavEngine(self.slam)
        self.sim = MineSimulatorEngine(width_m=16.0, height_m=16.0)
        self.dxf_conv = DxfMapConverter(resolution_m=0.05)

        # 2. System State & Source Selector
        self.data_source = tk.StringVar(value="PHYSICAL") # "PHYSICAL" or "SIMULATOR"
        self.conn_mode = tk.StringVar(value="SERIAL")     # "SERIAL" or "WIFI"
        self.active_op_mode = tk.StringVar(value="MANUAL") # "MANUAL", "AUTO_EXPLORE", "DXF_WAYPOINT"
        
        self.esp32_ip = "192.168.4.1"
        self.ws_url = f"ws://{self.esp32_ip}:8888"
        self.ws = None
        self.serial_port = None
        self.connected = False
        self.packet_count = 0
        self.last_packet_time = time.time()
        self.data_rate_hz = 0.0

        # Telemetry State (Dual-Sensors across 4 Directions)
        self.telemetry = {
            "sector": 1,
            "motion": "S",
            "sonar": {
                "F": 100, "F1": 100, "F2": 100,
                "R": 100, "R1": 100, "R2": 100,
                "B": 100, "B1": 100, "B2": 100,
                "L": 100, "L1": 100, "L2": 100
            },
            "gas": {"mq4": 110, "mq7": 90, "mq2": 105},
            "dist_m": 0.0,
            "gov": 0,
            "segment": 0,
            "total_seg": 2
        }

        self.speed_val = 255
        self.governor_enabled = False # Safety governor bypass for testing

        # Threads & Workers
        self.cap = None
        self.running_video = True
        self.worker_running = True

        self.setup_ui()
        self.bind_keyboard_controls()
        
        # Start Background Workers
        threading.Thread(target=self.network_thread_worker, daemon=True).start()
        threading.Thread(target=self.serial_thread_worker, daemon=True).start()
        threading.Thread(target=self.sim_thread_worker, daemon=True).start()
        threading.Thread(target=self.autonav_thread_worker, daemon=True).start()
        threading.Thread(target=self.video_thread_worker, daemon=True).start()
        
        # Start UI Refresh Loop
        self.update_gui_loop()

    def setup_ui(self):
        # =====================================================================
        # 1. TOP NAVIGATION & SYSTEM CONTROL BAR
        # =====================================================================
        top_bar = tk.Frame(self.root, bg="#1e293b", height=60)
        top_bar.pack(side=tk.TOP, fill=tk.X)

        title_frame = tk.Frame(top_bar, bg="#1e293b")
        title_frame.pack(side=tk.LEFT, padx=10, pady=6)
        tk.Label(title_frame, text="M.I.N.E.R.S.", font=("Helvetica", 14, "bold"), fg="#38bdf8", bg="#1e293b").pack(anchor="w")
        tk.Label(title_frame, text="AUTONOMOUS MINE RESCUE STATION & SLAM SUITE", font=("Helvetica", 8, "bold"), fg="#94a3b8", bg="#1e293b").pack(anchor="w")

        # Source Selector (Physical vs Simulator)
        src_box = tk.LabelFrame(top_bar, text=" DATA SOURCE ", font=("Helvetica", 8, "bold"), fg="#f59e0b", bg="#1e293b")
        src_box.pack(side=tk.LEFT, padx=15, pady=4)

        rb_phys = tk.Radiobutton(src_box, text="Physical Rover", variable=self.data_source, value="PHYSICAL",
                                 font=("Helvetica", 9, "bold"), fg="#38bdf8", bg="#1e293b", selectcolor="#0f172a",
                                 activebackground="#1e293b", command=self.on_source_change)
        rb_phys.pack(side=tk.LEFT, padx=4)

        rb_sim = tk.Radiobutton(src_box, text="Mine Simulator", variable=self.data_source, value="SIMULATOR",
                                font=("Helvetica", 9, "bold"), fg="#10b981", bg="#1e293b", selectcolor="#0f172a",
                                activebackground="#1e293b", command=self.on_source_change)
        rb_sim.pack(side=tk.LEFT, padx=4)

        # Connection Controls
        conn_box = tk.Frame(top_bar, bg="#1e293b")
        conn_box.pack(side=tk.RIGHT, padx=10, pady=6)

        self.rb_serial = tk.Radiobutton(conn_box, text="Direct USB (COM)", variable=self.conn_mode, value="SERIAL",
                                        font=("Helvetica", 9, "bold"), fg="#10b981", bg="#1e293b", selectcolor="#0f172a",
                                        activebackground="#1e293b", command=self.on_mode_change)
        self.rb_serial.pack(side=tk.LEFT, padx=3)

        self.rb_wifi = tk.Radiobutton(conn_box, text="Wi-Fi (AP)", variable=self.conn_mode, value="WIFI",
                                      font=("Helvetica", 9, "bold"), fg="#38bdf8", bg="#1e293b", selectcolor="#0f172a",
                                      activebackground="#1e293b", command=self.on_mode_change)
        self.rb_wifi.pack(side=tk.LEFT, padx=3)

        self.cbo_ports = ttk.Combobox(conn_box, width=10, state="readonly")
        self.cbo_ports.pack(side=tk.LEFT, padx=3)
        self.refresh_com_ports()

        self.btn_refresh_ports = tk.Button(conn_box, text="↻", font=("Helvetica", 8, "bold"), bg="#334155", fg="white", command=self.refresh_com_ports)
        self.btn_refresh_ports.pack(side=tk.LEFT, padx=2)

        self.conn_status_lbl = tk.Label(conn_box, text="READY", font=("Helvetica", 9, "bold"), fg="#10b981", bg="#0f172a", padx=8, pady=3, relief=tk.RIDGE)
        self.conn_status_lbl.pack(side=tk.LEFT, padx=6)

        # =====================================================================
        # 2. MAIN 3-PANEL CONTENT LAYOUT
        # =====================================================================
        main_frame = tk.Frame(self.root, bg="#0f172a")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        left_panel = tk.Frame(main_frame, bg="#1e293b", width=380)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))

        center_panel = tk.Frame(main_frame, bg="#1e293b", width=620)
        center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)

        right_panel = tk.Frame(main_frame, bg="#1e293b", width=420)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=(5, 0))

        # ---------------------------------------------------------------------
        # LEFT PANEL: AUTONOMOUS MODES & NAVIGATION SUITE
        # ---------------------------------------------------------------------
        mode_frame = tk.LabelFrame(left_panel, text=" OPERATING AUTONOMY MODE ", font=("Helvetica", 10, "bold"), fg="#38bdf8", bg="#1e293b", bd=2)
        mode_frame.pack(fill=tk.X, padx=8, pady=4)

        f_modes = tk.Frame(mode_frame, bg="#1e293b")
        f_modes.pack(fill=tk.X, padx=4, pady=4)

        self.btn_mode_manual = tk.Button(f_modes, text="1. MANUAL\nTELEOP", font=("Helvetica", 8, "bold"), bg="#0284c7", fg="white",
                                         command=lambda: self.switch_op_mode("MANUAL"), height=2)
        self.btn_mode_manual.grid(row=0, column=0, padx=2, sticky="nsew")

        self.btn_mode_explore = tk.Button(f_modes, text="2. AUTONOMOUS\nEXPLORATION", font=("Helvetica", 8, "bold"), bg="#334155", fg="#94a3b8",
                                          command=lambda: self.switch_op_mode("AUTO_EXPLORE"), height=2)
        self.btn_mode_explore.grid(row=0, column=1, padx=2, sticky="nsew")

        self.btn_mode_dxf = tk.Button(f_modes, text="3. DXF BLUEPRINT\nWAYPOINTS", font=("Helvetica", 8, "bold"), bg="#334155", fg="#94a3b8",
                                      command=lambda: self.switch_op_mode("DXF_WAYPOINT"), height=2)
        self.btn_mode_dxf.grid(row=0, column=2, padx=2, sticky="nsew")

        f_modes.columnconfigure(0, weight=1)
        f_modes.columnconfigure(1, weight=1)
        f_modes.columnconfigure(2, weight=1)

        # Autonav Status Banner
        self.lbl_autonav_status = tk.Label(mode_frame, text="AUTONOMOUS NAVIGATION: INACTIVE (MANUAL MODE)",
                                           font=("Helvetica", 8, "bold"), fg="#94a3b8", bg="#0f172a", pady=4)
        self.lbl_autonav_status.pack(fill=tk.X, padx=4, pady=4)

        # Manual D-Pad & Speed Controls
        self.dpad_box = tk.LabelFrame(left_panel, text=" MANUAL TELEOPERATION (WASD) ", font=("Helvetica", 9, "bold"), fg="#94a3b8", bg="#1e293b")
        self.dpad_box.pack(fill=tk.X, padx=8, pady=3)

        dpad = tk.Frame(self.dpad_box, bg="#1e293b")
        dpad.pack(pady=2)

        self.btn_fwd = tk.Button(dpad, text="▲ FORWARD (W)", font=("Helvetica", 8, "bold"), width=15, bg="#0284c7", fg="white", command=lambda: self.send_command('F'))
        self.btn_fwd.grid(row=0, column=1, pady=2)

        self.btn_left = tk.Button(dpad, text="◄ LEFT (A)", font=("Helvetica", 8, "bold"), width=11, bg="#0284c7", fg="white", command=lambda: self.send_command('L'))
        self.btn_left.grid(row=1, column=0, padx=2)

        self.btn_stop = tk.Button(dpad, text="█ STOP (Space)", font=("Helvetica", 8, "bold"), width=13, bg="#f43f5e", fg="white", command=lambda: self.send_command('S'))
        self.btn_stop.grid(row=1, column=1, padx=2)

        self.btn_right = tk.Button(dpad, text="RIGHT (D) ►", font=("Helvetica", 8, "bold"), width=11, bg="#0284c7", fg="white", command=lambda: self.send_command('R'))
        self.btn_right.grid(row=1, column=2, padx=2)

        self.btn_back = tk.Button(dpad, text="▼ BACKWARD (S)", font=("Helvetica", 8, "bold"), width=15, bg="#0284c7", fg="white", command=lambda: self.send_command('B'))
        self.btn_back.grid(row=2, column=1, pady=2)

        # Speed Slider
        speed_frame = tk.Frame(self.dpad_box, bg="#1e293b")
        speed_frame.pack(fill=tk.X, padx=6, pady=2)
        tk.Label(speed_frame, text="Speed:", font=("Helvetica", 8, "bold"), fg="#94a3b8", bg="#1e293b").pack(side=tk.LEFT)
        self.scale_speed = tk.Scale(speed_frame, from_=100, to=255, orient=tk.HORIZONTAL, bg="#1e293b", fg="white", highlightthickness=0, command=self.on_speed_change)
        self.scale_speed.set(255)
        self.scale_speed.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=4)

        # DXF Blueprint Ingestor Box
        dxf_box = tk.LabelFrame(left_panel, text=" CAD / DXF MINE BLUEPRINT INGESTOR ", font=("Helvetica", 9, "bold"), fg="#f59e0b", bg="#1e293b")
        dxf_box.pack(fill=tk.X, padx=8, pady=3)

        f_dxf_btns = tk.Frame(dxf_box, bg="#1e293b")
        f_dxf_btns.pack(fill=tk.X, padx=4, pady=2)

        tk.Button(f_dxf_btns, text="📂 Load Sample Mine DXF", font=("Helvetica", 8, "bold"), bg="#334155", fg="white", command=self.load_sample_mine_dxf).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        tk.Button(f_dxf_btns, text="Browse DXF...", font=("Helvetica", 8), bg="#334155", fg="#cbd5e1", command=self.browse_dxf_file).pack(side=tk.RIGHT, padx=2)

        self.lbl_dxf_info = tk.Label(dxf_box, text="No DXF loaded (Ready for Blueprint Ingestion)", font=("Helvetica", 8), fg="#94a3b8", bg="#1e293b")
        self.lbl_dxf_info.pack(anchor="w", padx=6, pady=2)

        # Map Tools & Export Box
        map_tools_box = tk.LabelFrame(left_panel, text=" SLAM MAP TOOLS ", font=("Helvetica", 9, "bold"), fg="#10b981", bg="#1e293b")
        map_tools_box.pack(fill=tk.X, padx=8, pady=3)

        f_tools = tk.Frame(map_tools_box, bg="#1e293b")
        f_tools.pack(fill=tk.X, padx=4, pady=3)

        tk.Button(f_tools, text="🧹 Reset SLAM Map", font=("Helvetica", 8, "bold"), bg="#475569", fg="white", command=self.reset_slam_map).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        tk.Button(f_tools, text="💾 Export ROS2 Map", font=("Helvetica", 8, "bold"), bg="#059669", fg="white", command=self.export_ros2_map).pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=2)

        # ---------------------------------------------------------------------
        # CENTER PANEL: LIVE REAL-TIME SLAM MINE MAP CANVAS & CAMERA FEED
        # ---------------------------------------------------------------------
        map_box = tk.LabelFrame(center_panel, text=" LIVE 2D SLAM MINE MAP & GAS HEATMAP (REAL-TIME) ", font=("Helvetica", 10, "bold"), fg="#10b981", bg="#1e293b", bd=2)
        map_box.pack(fill=tk.BOTH, expand=True, padx=4, pady=3)

        self.lbl_slam_map = tk.Label(map_box, bg="#0f172a", text="[Generating Real-Time SLAM Map...]", fg="#94a3b8")
        self.lbl_slam_map.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Bottom Split: Camera Feed + Real-Time Telemetry Terminal
        bottom_split = tk.Frame(center_panel, bg="#1e293b")
        bottom_split.pack(fill=tk.X, padx=4, pady=3)

        # Camera feed
        cam_box = tk.LabelFrame(bottom_split, text=" LIVE CAMERA / YOLO DETECTION ", font=("Helvetica", 8, "bold"), fg="#38bdf8", bg="#1e293b")
        cam_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 3))

        self.lbl_video = tk.Label(cam_box, bg="#0f172a", text="[Connecting Video...]", fg="#94a3b8", height=8)
        self.lbl_video.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Real-time console
        term_box = tk.LabelFrame(bottom_split, text=" LIVE TELEMETRY LOG ", font=("Helvetica", 8, "bold"), fg="#10b981", bg="#1e293b")
        term_box.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(3, 0))

        self.txt_telemetry = tk.Text(term_box, height=8, width=35, bg="#020617", fg="#4ade80", font=("Courier", 8), wrap="none")
        self.txt_telemetry.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # ---------------------------------------------------------------------
        # RIGHT PANEL: 4-DIRECTION SONAR RADAR & GAS TELEMETRY
        # ---------------------------------------------------------------------
        radar_box = tk.LabelFrame(right_panel, text=" 4-DIRECTION DUAL SONAR RADAR ", font=("Helvetica", 10, "bold"), fg="#38bdf8", bg="#1e293b", bd=2)
        radar_box.pack(fill=tk.BOTH, expand=True, padx=4, pady=3)

        self.canvas_radar = tk.Canvas(radar_box, bg="#0f172a", highlightthickness=0, height=260)
        self.canvas_radar.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Gas Stratification Telemetry Cards
        gas_box = tk.LabelFrame(right_panel, text=" MULTI-TIER HAZARDOUS GAS TELEMETRY ", font=("Helvetica", 9, "bold"), fg="#34d399", bg="#1e293b", bd=2)
        gas_box.pack(fill=tk.X, padx=4, pady=3)

        g_grid = tk.Frame(gas_box, bg="#1e293b")
        g_grid.pack(fill=tk.X, padx=4, pady=4)

        # MQ-4 Methane Card
        self.card_mq4 = tk.Frame(g_grid, bg="#0f172a", bd=1, relief=tk.SOLID)
        self.card_mq4.grid(row=0, column=0, padx=2, pady=2, sticky="nsew")
        tk.Label(self.card_mq4, text="CH4 Methane (Roof)", font=("Helvetica", 8, "bold"), fg="#38bdf8", bg="#0f172a").pack(padx=2, pady=1)
        self.lbl_mq4_val = tk.Label(self.card_mq4, text="-- ADC", font=("Helvetica", 11, "bold"), fg="#f8fafc", bg="#0f172a")
        self.lbl_mq4_val.pack(padx=2, pady=1)
        self.lbl_mq4_status = tk.Label(self.card_mq4, text="NORMAL", font=("Helvetica", 7, "bold"), fg="#10b981", bg="#0f172a")
        self.lbl_mq4_status.pack(padx=2, pady=1)

        # MQ-7 Carbon Monoxide Card
        self.card_mq7 = tk.Frame(g_grid, bg="#0f172a", bd=1, relief=tk.SOLID)
        self.card_mq7.grid(row=0, column=1, padx=2, pady=2, sticky="nsew")
        tk.Label(self.card_mq7, text="CO (Breathing Zone)", font=("Helvetica", 8, "bold"), fg="#fbbf24", bg="#0f172a").pack(padx=2, pady=1)
        self.lbl_mq7_val = tk.Label(self.card_mq7, text="-- ADC", font=("Helvetica", 11, "bold"), fg="#f8fafc", bg="#0f172a")
        self.lbl_mq7_val.pack(padx=2, pady=1)
        self.lbl_mq7_status = tk.Label(self.card_mq7, text="NORMAL", font=("Helvetica", 7, "bold"), fg="#10b981", bg="#0f172a")
        self.lbl_mq7_status.pack(padx=2, pady=1)

        # MQ-2 Smoke Card
        self.card_mq2 = tk.Frame(g_grid, bg="#0f172a", bd=1, relief=tk.SOLID)
        self.card_mq2.grid(row=0, column=2, padx=2, pady=2, sticky="nsew")
        tk.Label(self.card_mq2, text="Smoke / LPG (Floor)", font=("Helvetica", 8, "bold"), fg="#f87171", bg="#0f172a").pack(padx=2, pady=1)
        self.lbl_mq2_val = tk.Label(self.card_mq2, text="-- ADC", font=("Helvetica", 11, "bold"), fg="#f8fafc", bg="#0f172a")
        self.lbl_mq2_val.pack(padx=2, pady=1)
        self.lbl_mq2_status = tk.Label(self.card_mq2, text="NORMAL", font=("Helvetica", 7, "bold"), fg="#10b981", bg="#0f172a")
        self.lbl_mq2_status.pack(padx=2, pady=1)

        g_grid.columnconfigure(0, weight=1)
        g_grid.columnconfigure(1, weight=1)
        g_grid.columnconfigure(2, weight=1)

    # =========================================================================
    # EVENT HANDLERS & NAVIGATION CONTROLS
    # =========================================================================
    def on_source_change(self):
        src = self.data_source.get()
        self.log_terminal(f"[System] Active Data Source: {src}")
        if src == "SIMULATOR":
            self.conn_status_lbl.config(text="SIMULATOR ACTIVE", fg="#10b981", bg="#064e3b")
        else:
            self.conn_status_lbl.config(text="CONNECTING PHYSICAL...", fg="#f43f5e", bg="#450a0a")

    def on_mode_change(self):
        mode = self.conn_mode.get()
        self.log_terminal(f"[System] Connection mode: {mode}")

    def on_speed_change(self, val):
        self.speed_val = int(val)

    def switch_op_mode(self, new_mode):
        self.active_op_mode.set(new_mode)
        self.btn_mode_manual.config(bg="#334155", fg="#94a3b8")
        self.btn_mode_explore.config(bg="#334155", fg="#94a3b8")
        self.btn_mode_dxf.config(bg="#334155", fg="#94a3b8")

        if new_mode == "MANUAL":
            self.btn_mode_manual.config(bg="#0284c7", fg="white")
            self.autonav.enabled = False
            self.lbl_autonav_status.config(text="AUTONOMOUS NAVIGATION: INACTIVE (MANUAL TELEOP)", fg="#94a3b8", bg="#0f172a")
            self.send_raw_command("CMD:S:0")
        elif new_mode == "AUTO_EXPLORE":
            self.btn_mode_explore.config(bg="#10b981", fg="white")
            self.autonav.set_mode("CORRIDOR_EXPLORE")
            self.autonav.enabled = True
            self.lbl_autonav_status.config(text="AUTO EXPLORATION ACTIVE (Corridor Centerline + Sonar SLAM)", fg="#10b981", bg="#064e3b")
        elif new_mode == "DXF_WAYPOINT":
            self.btn_mode_dxf.config(bg="#f59e0b", fg="white")
            self.autonav.set_mode("WAYPOINT_FOLLOW")
            self.autonav.enabled = True
            self.lbl_autonav_status.config(text="DXF BLUEPRINT WAYPOINT NAVIGATION ACTIVE", fg="#f59e0b", bg="#451a03")

    def load_sample_mine_dxf(self):
        dxf_path = "e:/miners/sample_mine_drift_blueprint.dxf"
        if not os.path.exists(dxf_path):
            from create_sample_mine_dxf import create_sample_mine_dxf
            create_sample_mine_dxf(dxf_path)
            
        self.dxf_conv.load_dxf(dxf_path)
        wps = self.dxf_conv.extract_corridor_waypoints(6)
        self.autonav.load_waypoints(wps)
        self.lbl_dxf_info.config(text=f"Loaded: sample_mine_drift_blueprint.dxf ({len(wps)} Waypoints)", fg="#10b981")
        self.log_terminal(f"[DXF] Loaded sample mine blueprint with {len(wps)} waypoints!")
        messagebox.showinfo("DXF Blueprint Loaded", f"Successfully ingested mine blueprint!\nExtracted {len(wps)} autonomous waypoints across drift corridors.")

    def browse_dxf_file(self):
        file_path = filedialog.askopenfilename(title="Select AutoCAD DXF Mine Blueprint", filetypes=[("AutoCAD DXF Files", "*.dxf"), ("All Files", "*.*")])
        if file_path:
            try:
                self.dxf_conv.load_dxf(file_path)
                wps = self.dxf_conv.extract_corridor_waypoints(8)
                self.autonav.load_waypoints(wps)
                self.lbl_dxf_info.config(text=f"Loaded: {os.path.basename(file_path)} ({len(wps)} Waypoints)", fg="#10b981")
                self.log_terminal(f"[DXF] Ingested {os.path.basename(file_path)} with {len(wps)} waypoints!")
                messagebox.showinfo("DXF Blueprint Loaded", f"Ingested {os.path.basename(file_path)}!\nExtracted {len(wps)} navigation waypoints.")
            except Exception as e:
                messagebox.showerror("DXF Error", f"Failed to parse DXF: {e}")

    def reset_slam_map(self):
        self.slam.reset()
        if self.data_source.get() == "SIMULATOR":
            self.sim.reset_rover()
        self.log_terminal("[SLAM] Real-time Occupancy Grid and Gas Heatmap reset.")

    def export_ros2_map(self):
        try:
            yaml_p, pgm_p = self.slam.export_ros2_map("e:/miners/mine_slam_map")
            messagebox.showinfo("Map Exported", f"Successfully exported ROS 2 / Nav2 Occupancy Grid!\nYAML: {yaml_p}\nPGM: {pgm_p}")
            self.log_terminal(f"[Export] Saved ROS2 map files: {yaml_p}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export map: {e}")

    def refresh_com_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.cbo_ports['values'] = ports
        if ports:
            if "COM5" in ports: self.cbo_ports.set("COM5")
            else: self.cbo_ports.set(ports[0])
        else:
            self.cbo_ports.set("No Ports")

    def bind_keyboard_controls(self):
        self.root.bind("<w>", lambda e: self.send_command('F'))
        self.root.bind("<s>", lambda e: self.send_command('B'))
        self.root.bind("<a>", lambda e: self.send_command('L'))
        self.root.bind("<d>", lambda e: self.send_command('R'))
        self.root.bind("<space>", lambda e: self.send_command('S'))

        self.root.bind("<Up>", lambda e: self.send_command('F'))
        self.root.bind("<Down>", lambda e: self.send_command('B'))
        self.root.bind("<Left>", lambda e: self.send_command('L'))
        self.root.bind("<Right>", lambda e: self.send_command('R'))

    def send_command(self, dir_char):
        if dir_char == 'S':
            # STOP command always pauses autonomous navigation for emergency safety!
            if self.autonav.enabled:
                self.autonav.enabled = False
                self.lbl_autonav_status.config(text="⚠️ AUTONAV PAUSED BY OPERATOR OVERRIDE (STOP)", fg="#f43f5e", bg="#450a0a")
                self.log_terminal("[OVERRIDE] Operator pressed STOP -> Paused Autonomous Navigation!")
            self.send_raw_command("CMD:S:0")
        else:
            # Directional override (W, A, S, D) sent directly to rover
            if self.autonav.enabled:
                self.log_terminal(f"[OVERRIDE] Operator manual command '{dir_char}' sent during Autonomous Mode.")
            self.send_raw_command(f"CMD:{dir_char}:{self.speed_val}")

    def send_raw_command(self, msg_str):
        # 1. Simulator Execution
        if self.data_source.get() == "SIMULATOR":
            if msg_str.startswith("CMD:"):
                parts = msg_str.split(":")
                dir_c = parts[1]
                spd_v = int(parts[2]) if len(parts) > 2 else 255
                self.sim.update_physics(dir_c, spd_v, 0.05)
            return

        # 2. Physical Rover Execution
        mode = self.conn_mode.get()
        if mode == "WIFI":
            if self.ws and self.connected:
                try:
                    self.ws.send(msg_str)
                except Exception as e:
                    pass
        elif mode == "SERIAL":
            if self.serial_port and self.serial_port.is_open:
                try:
                    self.serial_port.write((msg_str + "\n").encode('utf-8'))
                except Exception as e:
                    pass

    def log_terminal(self, text):
        try:
            self.txt_telemetry.insert("end", text + "\n")
            self.txt_telemetry.see("end")
            lines = self.txt_telemetry.get("1.0", "end").splitlines()
            if len(lines) > 40:
                self.txt_telemetry.delete("1.0", "2.0")
        except:
            pass

    def handle_incoming_json(self, raw_str):
        try:
            data = json.loads(raw_str)
            if "sonar" in data and "gas" in data:
                self.telemetry = data
                self.packet_count += 1
                now = time.time()
                dt = now - self.last_packet_time
                if dt > 0.05:
                    self.data_rate_hz = 0.9 * self.data_rate_hz + 0.1 * (1.0 / dt)
                self.last_packet_time = now

                # Feed SLAM Mapper directly!
                motion = data.get("motion", "S")
                self.slam.update_sensors(data.get("sonar", {}), data.get("gas", {}), motion)
        except Exception as e:
            pass

    # =========================================================================
    # BACKGROUND WORKER THREADS
    # =========================================================================
    # Thread 1: Autonomous Navigation Decision Engine
    def autonav_thread_worker(self):
        while self.worker_running:
            if self.autonav.enabled:
                dir_c, spd_v, msg = self.autonav.compute_next_action(self.telemetry)
                self.send_raw_command(f"CMD:{dir_c}:{spd_v}")
                self.lbl_autonav_status.config(text=f"AUTONAV: {msg}")
            time.sleep(0.08) # 12.5 Hz Autonav decision rate

    # Thread 2: Simulator Physics Worker
    def sim_thread_worker(self):
        while self.worker_running:
            if self.data_source.get() == "SIMULATOR":
                self.sim.update_physics(self.sim.current_motion, 255, 0.05)
                sim_tel = self.sim.get_simulated_telemetry()
                self.telemetry = sim_tel
                self.packet_count += 1
                self.data_rate_hz = 20.0
                
                # Update SLAM from simulator stream
                self.slam.update_sensors(sim_tel["sonar"], sim_tel["gas"], sim_tel["motion"])
            time.sleep(0.05) # 20 Hz Simulator loop

    # Thread 3: Wi-Fi WebSocket Worker
    def network_thread_worker(self):
        while self.worker_running:
            if self.data_source.get() == "PHYSICAL" and self.conn_mode.get() == "WIFI":
                try:
                    self.ws = websocket.WebSocketApp(
                        self.ws_url,
                        on_open=self.on_ws_open,
                        on_message=self.on_ws_message,
                        on_error=self.on_ws_error,
                        on_close=self.on_ws_close
                    )
                    self.ws.run_forever()
                except Exception as e:
                    pass
                self.connected = False
            time.sleep(1.5)

    def on_ws_open(self, ws):
        if self.data_source.get() == "PHYSICAL" and self.conn_mode.get() == "WIFI":
            self.connected = True
            self.log_terminal("[Wi-Fi] Connected to Rover WebSocket bridge at 192.168.4.1:8888")

    def on_ws_message(self, ws, message):
        if self.data_source.get() == "PHYSICAL" and self.conn_mode.get() == "WIFI":
            self.handle_incoming_json(message)

    def on_ws_error(self, ws, error):
        self.connected = False

    def on_ws_close(self, ws, close_status_code, close_msg):
        self.connected = False

    # Thread 4: Direct USB Serial Worker
    def serial_thread_worker(self):
        while self.worker_running:
            if self.data_source.get() == "PHYSICAL" and self.conn_mode.get() == "SERIAL":
                port_name = self.cbo_ports.get()
                if port_name and "COM" in port_name:
                    try:
                        if not self.serial_port or not self.serial_port.is_open or self.serial_port.port != port_name:
                            self.serial_port = serial.Serial(port_name, 115200, timeout=1.0)
                            self.log_terminal(f"[USB Serial] Connected to {port_name} at 115200 baud")
                            time.sleep(1.5)
                            self.connected = True
                        
                        while self.data_source.get() == "PHYSICAL" and self.conn_mode.get() == "SERIAL" and self.serial_port.is_open:
                            line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                            if line:
                                if line.startswith("{"):
                                    self.handle_incoming_json(line)
                                else:
                                    self.log_terminal(f"[Rover MSG] {line}")
                    except Exception as e:
                        self.connected = False
                        time.sleep(1.5)
                else:
                    self.connected = False
                    time.sleep(1.0)
            else:
                if self.serial_port and self.serial_port.is_open:
                    try: self.serial_port.close()
                    except: pass
                time.sleep(1.0)

    # Thread 5: Camera Feed Worker
    def video_thread_worker(self):
        self.cap = cv2.VideoCapture(0)
        while self.running_video:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.05)
                continue
            
            if YOLO_AVAILABLE and yolo_model is not None:
                try:
                    results = yolo_model(frame, verbose=False)
                    frame = results[0].plot()
                except Exception as e:
                    pass

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img = img.resize((240, 150))
            imgtk = ImageTk.PhotoImage(image=img)

            self.lbl_video.imgtk = imgtk
            self.lbl_video.configure(image=imgtk)
            time.sleep(0.03)

    # =========================================================================
    # GUI REFRESH LOOP
    # =========================================================================
    def update_gui_loop(self):
        src = self.data_source.get()
        mode = self.conn_mode.get()
        
        # 1. Update Connection Status Badge
        if src == "SIMULATOR":
            self.conn_status_lbl.config(
                text=f"SIMULATOR ACTIVE | {self.packet_count} Pkts ({self.data_rate_hz:.1f} Hz)",
                fg="#10b981", bg="#064e3b"
            )
        elif self.connected:
            target = "192.168.4.1" if mode == "WIFI" else self.cbo_ports.get()
            self.conn_status_lbl.config(
                text=f"CONNECTED ({mode}: {target}) | {self.packet_count} Pkts ({self.data_rate_hz:.1f} Hz)",
                fg="#10b981", bg="#064e3b"
            )
        else:
            target = "192.168.4.1" if mode == "WIFI" else self.cbo_ports.get()
            self.conn_status_lbl.config(
                text=f"DISCONNECTED ({mode}: {target})",
                fg="#f43f5e", bg="#450a0a"
            )

        # 2. Update Multi-Tier Gas Readings
        gas_data = self.telemetry.get("gas", {})
        mq4 = gas_data.get("mq4", 0)
        mq7 = gas_data.get("mq7", 0)
        mq2 = gas_data.get("mq2", 0)

        self.lbl_mq4_val.config(text=f"{mq4} ADC")
        if mq4 > 450: self.lbl_mq4_status.config(text="HIGH CH4 HAZARD!", fg="#f43f5e")
        else: self.lbl_mq4_status.config(text="NORMAL", fg="#10b981")

        self.lbl_mq7_val.config(text=f"{mq7} ADC")
        if mq7 > 350: self.lbl_mq7_status.config(text="HIGH CO HAZARD!", fg="#f43f5e")
        else: self.lbl_mq7_status.config(text="NORMAL", fg="#10b981")

        self.lbl_mq2_val.config(text=f"{mq2} ADC")
        if mq2 > 400: self.lbl_mq2_status.config(text="SMOKE DETECTED!", fg="#f43f5e")
        else: self.lbl_mq2_status.config(text="NORMAL", fg="#10b981")

        # 3. Render Live SLAM Occupancy Grid Map Image
        map_pil = self.slam.render_map_image(target_w=580, target_h=420, show_gas_layer=True)
        map_imgtk = ImageTk.PhotoImage(image=map_pil)
        self.lbl_slam_map.imgtk = map_imgtk
        self.lbl_slam_map.configure(image=map_imgtk)

        # 4. Redraw 4-Direction Sonar Radar
        self.draw_4dir_dual_radar()
        
        self.root.after(100, self.update_gui_loop)

    def draw_4dir_dual_radar(self):
        self.canvas_radar.delete("all")
        w = self.canvas_radar.winfo_width()
        h = self.canvas_radar.winfo_height()
        if w < 10 or h < 10: return

        cx, cy = w / 2.0, h / 2.0
        max_r = min(w, h) * 0.36

        # Radar concentric rings (0.5m, 1.0m, 1.5m, 2.0m)
        for r_ratio, label_str in [(0.25, "0.5m"), (0.50, "1.0m"), (0.75, "1.5m"), (1.0, "2.0m")]:
            r_px = max_r * r_ratio
            self.canvas_radar.create_oval(cx - r_px, cy - r_px, cx + r_px, cy + r_px, outline="#334155", width=1)
            self.canvas_radar.create_text(cx + 8, cy - r_px - 8, text=label_str, fill="#64748b", font=("Helvetica", 7))

        # Rover Box Graphic in Center
        self.canvas_radar.create_rectangle(cx - 20, cy - 28, cx + 20, cy + 28, fill="#0284c7", outline="#38bdf8", width=2)
        motion_char = self.telemetry.get("motion", "S")
        self.canvas_radar.create_text(cx, cy, text=f"ROVER\n[{motion_char}]", fill="white", font=("Helvetica", 8, "bold"), justify="center")

        sonar = self.telemetry.get("sonar", {})

        sensors_def = [
            ("F1", sonar.get("F1", 100), 102),
            ("F2", sonar.get("F2", 100), 78),
            ("R1", sonar.get("R1", 100), 12),
            ("R2", sonar.get("R2", 100), 348),
            ("B1", sonar.get("B1", 100), 258),
            ("B2", sonar.get("B2", 100), 282),
            ("L1", sonar.get("L1", 100), 192),
            ("L2", sonar.get("L2", 100), 168),
        ]

        for s_id, dist_cm, angle_deg in sensors_def:
            dist_m = dist_cm / 100.0
            ratio = min(dist_m / 2.0, 1.0)
            r_px = max(max_r * ratio, 28)

            rad = math.radians(angle_deg)
            pt_x = cx + r_px * math.cos(rad)
            pt_y = cy - r_px * math.sin(rad)

            color_code = "#10b981"
            if dist_cm < 35: color_code = "#f43f5e"
            elif dist_cm < 65: color_code = "#fbbf24"

            self.canvas_radar.create_line(cx, cy, pt_x, pt_y, fill=color_code, width=2, dash=(4, 2))
            self.canvas_radar.create_oval(pt_x - 4, pt_y - 4, pt_x + 4, pt_y + 4, fill=color_code, outline="white")
            
            lbl_x = cx + (max_r + 14) * math.cos(rad)
            lbl_y = cy - (max_r + 14) * math.sin(rad)
            self.canvas_radar.create_text(lbl_x, lbl_y, text=f"{dist_cm}c", fill="#f8fafc", font=("Helvetica", 7, "bold"))

        # Direction Summary Badges
        f_min = sonar.get("F", 100)
        r_min = sonar.get("R", 100)
        b_min = sonar.get("B", 100)
        l_min = sonar.get("L", 100)
        
        self.canvas_radar.create_text(cx, cy - max_r - 24, text=f"FRONT: {f_min} cm", fill="#38bdf8", font=("Helvetica", 8, "bold"))
        self.canvas_radar.create_text(cx + max_r + 34, cy, text=f"R: {r_min}cm", fill="#38bdf8", font=("Helvetica", 8, "bold"))
        self.canvas_radar.create_text(cx, cy + max_r + 24, text=f"REAR: {b_min} cm", fill="#38bdf8", font=("Helvetica", 8, "bold"))
        self.canvas_radar.create_text(cx - max_r - 34, cy, text=f"L: {l_min}cm", fill="#38bdf8", font=("Helvetica", 8, "bold"))

if __name__ == "__main__":
    root = tk.Tk()
    app = MinersRescueStationApp(root)
    root.mainloop()
