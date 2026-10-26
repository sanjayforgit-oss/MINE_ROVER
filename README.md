# ⛏️ M.I.N.E.R.S. — Mobile Intelligent Navigation & Emergency Rescue System

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![ROS 2](https://img.shields.io/badge/ROS_2-Humble%20%2F%20Iron-blue.svg)](https://docs.ros.org/)
[![Arduino](https://img.shields.io/badge/Firmware-Arduino%20Mega%202560%20%26%20ESP8266-00979D.svg)](https://www.arduino.cc/)
[![Python](https://img.shields.io/badge/Python-3.10%20%2F%203.11-3776AB.svg)](https://www.python.org/)
[![Gazebo](https://img.shields.io/badge/Simulation-Gazebo%20Garden-orange.svg)](https://gazebosim.org/)
[![AI Perception](https://img.shields.io/badge/AI-YOLOv8%20Object%20Detection-FF6F00.svg)](https://ultralytics.com/)

**An autonomous, hazard-aware robotic reconnaissance and rescue system engineered to navigate dangerous underground mine collapses, detect trapped miners, compute safe egress escape corridors ("God Path"), and relay vital situational telemetry to surface rescue teams.**

[Overview](#-overview) • [Core Capabilities](#-key-capabilities) • [Hardware Architecture](#-hardware-architecture) • [Software Pipeline](#-software-architecture) • [Simulation](#-simulation--digital-twin) • [Mechanical Design](#-mechanical-design--cad) • [Quickstart](#-quickstart--installation)

</div>

---

## 📌 Overview

Underground mining accidents—such as rockfalls, gas explosions, toxic leaks, and cave-ins—pose severe risks to human rescue crews. Hostile subterranean environments suffer from **zero visibility, hazardous atmosphere (methane, carbon monoxide), physical debris, and complete wireless signal attenuation (dead zones)**.

**M.I.N.E.R.S.** is a ruggedized, low-cost autonomous search-and-rescue rover deployed into disaster zones before human first responders enter. Its primary mission:
1. **Explore & Map Subterranean Tunnels**: Autonomous 2D/3D simultaneous localization and mapping (SLAM) in unmapped or altered tunnels.
2. **Atmospheric & Structural Hazard Analysis**: Real-time multi-gas monitoring ($CH_4$, $CO$, Smoke/LPG) and obstacle clearance mapping.
3. **Survivor Localization**: Multimodal AI detection (RGB camera + thermal signature + posture detection + acoustic awareness) to spot trapped or unconscious miners.
4. **"God Path" Safe Evacuation Guidance**: Computes the optimal, safest path through the mine, steering survivors clear of toxic gas pockets and unstable cave-in zones.
5. **Communication-Resilient Bounded Autonomy**: Operates seamlessly through total Wi-Fi/radio link dropouts. The rover executes autonomous search patterns, logs all findings locally in flash memory, and synchronizes telemetry upon reconnecting with the base station or deploying wireless repeater nodes.

---

## 🚀 Key Capabilities

```
                  ┌─────────────────────────────────────────┐
                  │          UNDERGROUND COLLAPSE           │
                  │   (Zero Visibility, Gas Leaks, Comms 0)  │
                  └────────────────────┬────────────────────┘
                                       │
                         [ROVER AUTONOMOUS INFILTRATION]
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        ▼                              ▼                              ▼
┌───────────────┐              ┌───────────────┐              ┌───────────────┐
│ HAZARD SENSING│              │ SURVIVOR AI   │              │ BOUNDED SLAM  │
│ • MQ-4 (CH₄)  │              │ • YOLOv8 Vision│              │ • LiDAR / Dual│
│ • MQ-7 (CO)   │              │ • Thermal Sig │              │   Sonar Array │
│ • MQ-2 (Smoke)│              │ • Vital Signs │              │ • Local Nav   │
└───────┬───────┘              └───────┬───────┘              └───────┬───────┘
        │                              │                              │
        └──────────────────────────────┼──────────────────────────────┘
                                       ▼
                       ┌───────────────────────────────┐
                       │   "GOD PATH" ESCAPE ENGINE    │
                       │ Computes safest hazard-free   │
                       │ evacuation route for survivors│
                       └───────────────┬───────────────┘
                                       │
                         [COMMUNICATION RECOVERY]
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │  SURFACE RESCUE COMMAND HUB   │
                       │ Live HUD, Telemetry, Gas Maps,│
                       │ & First-Responder Deploy Plan │
                       └───────────────────────────────┘
```

### 1. 🛡️ Bounded Autonomy & Loss-of-Signal Recovery
Underground rock and ore formations heavily attenuate RF signals. When communication with the surface station drops:
- The rover **does not freeze or halt in dangerous zones**.
- It engages **Bounded Mission Mode**: continuing search patterns along predefined boundary limits using onboard SLAM.
- All environmental logs, gas hotspots, and survivor coordinates are cached locally.
- When the mission phase concludes or battery thresholds trigger, the rover returns along its mapped trajectory to re-establish the RF link.

### 2. 🦺 "God Path" Survivor Guidance
Once trapped personnel are identified:
- The rover analyzes dynamic environmental risks (elevated methane zones, low oxygen pockets, structural blockages).
- It calculates an optimal evacuation corridor—the **"God Path"**—which prioritizes **lowest atmospheric toxicity and maximum structural clearance**, rather than merely the shortest geometric distance.
- Serves as a localized visual and audio beacon guiding disoriented workers to safety.

### 3. 🧪 Multi-Gas Atmospheric Profiling
Continuous analog sampling of dangerous gases:
- **MQ-4**: Methane ($CH_4$) — Prevents ignition by identifying explosive lower explosive limit (LEL) zones.
- **MQ-7**: Carbon Monoxide ($CO$) — Detects lethal, odorless asphyxiant gases generated after underground fires.
- **MQ-2**: Flammable gases, smoke, and liquefied petroleum hydrocarbons.

### 4. 🎛️ Dual-Level Safety Governor
An independent hardware/software failsafe monitors ultrasonic and LiDAR clearance. If human operators or high-level autonomous planners issue a command that would drive the rover into an obstacle or drop-off, the **Obstacle Governor** automatically overrides and halts motion.

---

## ⚡ Hardware Architecture

The rover is powered by a multi-tiered embedded distributed architecture:

| Tier | Component | Function |
| :--- | :--- | :--- |
| **Real-Time Motion Master** | **Arduino Mega 2560** | Low-latency PWM motor driver signaling, 8x ultrasonic timing, analog gas acquisition, safety governor. |
| **Wireless Telemetry Bridge**| **Wemos D1 Mini (ESP8266)** | Creates an autonomous local Wi-Fi Access Point (`MINERS_ROVER`), bridging UART serial from the Mega to WebSockets / HTTP. |
| **Surface Base Station** | **ESP32 / Laptop Edge Unit** | Hosts the surface Rescue Station Dashboard, executes YOLOv8 inference, processes telemetry packets. |
| **Motor Drivers** | **Dual BTS7960 (V1326 43A)** | High-power dual H-bridge drivers capable of handling peak stall currents of 12V high-torque DC gear motors. |
| **Drivetrain** | **4WD Skid-Steer** | Zero-radius tank turning allowing navigation through narrow, debris-cluttered mine shafts. |
| **Obstacle Sensing** | **8x HC-SR04 Sensors** | Dual-sensor redundant pairs oriented in 4 cardinal directions (Front, Back, Left, Right). |
| **Power Supply** | **Dual-Rail Isolated Power** | Dedicated 12V Li-ion battery pack for motors + filtered 5V logic rail to prevent inductive noise spikes. |

### Motor Control & Enable Logic (BTS7960 / V1326)
Both BTS7960 drivers utilize bidirectional half-bridge PWM control with hardware enable bridging:
- **Left Motors**: Forward on `Pin D2 (RPWM)`, Reverse on `Pin D3 (LPWM)`, Enable on `Pin D30 (R_EN + L_EN)`.
- **Right Motors**: Forward on `Pin D4 (RPWM)`, Reverse on `Pin D5 (LPWM)`, Enable on `Pin D32 (R_EN + L_EN)`.

---

## 💻 Software Architecture

```
e:\miners\
├── mega2560_rover_master/          # Arduino Mega 2560 Master Rover Firmware
│   └── mega2560_rover_master.ino   # Real-time drive, 8-sonar scan, gas telemetry
├── wemos_d1_wifi_bridge/           # ESP8266 Wi-Fi Bridge Firmware
│   └── wemos_d1_wifi_bridge.ino    # Serial-to-WebSocket/HTTP telemetry streamer
├── esp32_rover_main/               # Alternative ESP32 Integrated Node Firmware
├── motor_hardware_diagnostic/      # BMS-safe isolated motor driver diagnostic sketch
├── ros2_gazebo_package/            # ROS 2 & Gazebo Subterranean Simulation Suite
│   ├── miners_rover.urdf.xacro     # Physics, inertial, lidar & visual robot model
│   ├── dxf_to_gazebo_world.py      # Procedural mine world generator from DXF maps
│   └── gazebo_ros_simulation_launch.py # Complete launch sequence for Gazebo & ROS 2
├── rescue_station.py               # Tkinter/PyQt Surface Command Center GUI
├── rescue_station_esp32.py         # Surface Rescue Station with ESP32 direct integration
├── live_slam_mapper.py             # Real-time LiDAR / Sonar SLAM mapper
├── autonomous_nav_engine.py        # Comms-loss autonomous path planner & God Path engine
├── generate_cnc_link_dxf.py        # CNC Router & laser cutting CAD generator
└── MINERS_Complete_Wiring_Guide.pdf # Complete 10-page prototype schematic & wiring guide
```

---

## 🌐 Simulation & Digital Twin

A high-fidelity simulation environment is developed in **ROS 2 Humble / Gazebo Garden**:
- **Procedural Tunnel Generation**: Converts AutoCAD DXF mine blueprints directly into 3D Gazebo collision worlds (`.world`).
- **Sensor Plugins**: Simulates 360° planar LiDAR, depth sensors, differential/skid-steer drive odometry, and IMU.
- **Web 3D Visualizer**: `gazebo_ros_mine_simulation_3d.html` provides a browser-accessible Three.js 3D rendering of the rover navigating mine drifts.

Run the simulation:
```bash
python ros2_gazebo_package/dxf_to_gazebo_world.py --input sample_mine_drift_blueprint.dxf
python ros2_gazebo_package/gazebo_ros_simulation_launch.py
```

---

## 🛠️ Mechanical Design & CAD

The rover chassis and suspension components are designed for high ground clearance and lightweight structural rigidity:
- **Chassis Geometry**: Hexagonal / Stealth Octagonal baseplate layouts optimized for impact resistance against falling rocks.
- **CNC Milled Link Arms**: Custom 120 mm × 8 mm × 2 mm link brackets with Ø3.0 mm mounting holes spaced at **105.0 mm inner clearance** (`link_plate_120x8mm.dxf`), fabricated via 3-axis CNC router / ArtCAM Pro.
- **Shock Brackets**: Dual-wheel board spacer clips and crossbars to distribute impact loads across the axle frames.

---

## 🚦 Quickstart & Installation

### 1. Prerequisites
- **Python 3.10+**:
  ```bash
  pip install opencv-python ultralytics numpy matplotlib ezdxf reportlab pyserial websockets
  ```
- **Arduino IDE**: Install board packages for `Arduino Mega 2560` and `ESP8266 by ESP8266 Community`.

### 2. Flash Microcontrollers
1. Connect **Arduino Mega 2560** via USB $\rightarrow$ Open `mega2560_rover_master/mega2560_rover_master.ino` $\rightarrow$ Select Board & Port $\rightarrow$ **Upload**.
2. Connect **Wemos D1 Mini** $\rightarrow$ Open `wemos_d1_wifi_bridge/wemos_d1_wifi_bridge.ino` $\rightarrow$ **Upload**.

### 3. Launch Surface Rescue Command Station
Power the rover. Connect your laptop to the rover's Wi-Fi network (`MINERS_ROVER`, pass: `miners123`) or plug in the serial telemetry cable, then launch:
```bash
python rescue_station_esp32.py
```
From the dashboard:
- View live atmospheric gas levels ($CH_4$, $CO$, Smoke).
- Observe 4-direction sonar proximity radar.
- Switch between **Manual Remote Drive** and **Autonomous Exploration Mode**.
- Activate/deactivate the **Obstacle Safety Governor**.

---

## 👥 Target Beneficiaries & Impact

- **Mine Rescue & Emergency Teams**: Provides safe preliminary reconnaissance without risking responders' lives.
- **Trapped Underground Workers**: Rapid localization and guided evacuation pathfinding during critical golden hours.
- **Mine Safety Engineers**: Post-accident structural assessment, heat mapping, and toxic pocket identification.

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).

---

<div align="center">
<b>M.I.N.E.R.S. Project</b> — Built to save lives where human eyes cannot see and wireless signals cannot reach.
</div>
