# M.I.N.E.R.S. Project - Antigravity Agent Handoff Context

## Project Overview
*   **Name:** M.I.N.E.R.S. (Mobile Intelligent Navigation and Emergency Rescue System)
*   **Problem Statement:** AI-Powered Underground Mine Safety, Monitoring and Rescue System (Govt. of Jharkhand).
*   **PS ID:** 26039 (Smart India Hackathon 2026).

## Hardware & Architecture Specs
*   **Edge Compute:** Raspberry Pi 5 (8GB) + AI HAT+ (26 TOPS).
*   **Microcontroller:** Arduino Mega 2560 (handles low-level safety, data acquisition).
*   **Sensors:** 
    *   360° 2D LiDAR (NOTE: **NO 3D LiDAR** is used).
    *   Stereo RGB-D Camera (serves as both RGB and Depth, does not see through rocks).
    *   Thermal Camera.
    *   Gas sensors (MQ series), Temp/Humidity/Dust/Water sensors.
    *   IMU + Encoders, Ultrasonic.
*   **Actuation:** 4WD rugged chassis, 12V DC geared motors, BTS7960 drivers, Pan-Tilt mechanism for the camera.
*   **Communication:** Wi-Fi, Breadcrumb Relay Mesh Nodes (deployable), and Store-and-Forward on an SD card for absolute comms loss.

## Presentation & Branding Preferences
*   **Aesthetic:** The user strongly prefers the "UDAAN!" SIH slide aesthetic (clean white background, pastel containers like lavender/cyan, 3D cylindrical pipeline tubes, curved Tech Stack ribbon at the bottom).
*   **Messaging Constraints:** 
    *   Emphasize "Bounded Autonomous Operation" upon communication loss (NOT unrestricted autonomy).
    *   Rule: "AI Assists Detection — Rescue Team Makes the Final Decision".
    *   Do NOT claim medical diagnosis, DGMS/ATEX certification (yet), or fake performance numbers. Highlight the "Safety Governor" (hard constraints).
*   **Infographics Created:** We successfully created multiple precisely sized graphics: a 16:9 System Architecture, a 3.8:1 landscape engineering banner (rover illustration), a 3:4 vertical "Feasibility" card, and a 16:9 + 3:4 vertical "Comparison Matrix" against Gemini-Scout, AgileX, and IIT(ISM).

## Recent Code Accomplishments
*   **Camera Initialization Fixes:** Modified both `rescue_station.py` and `rescue_station_v2.py` to default to `current_cam_idx = 1` (Integrated Laptop Webcam) to bypass a virtual camera driver stall at index 0. Added dropdown UIs to switch sources.
*   **Thread Safety:** Added a `cam_lock` during the `on_closing()` event and robust `try-except` blocks for Tkinter `after` events to ensure clean shutdowns without console tracebacks.
*   **Transcripts:** We previously parsed React Router Turbo stream payloads to reconstruct older ChatGPT conversation transcripts.

## Current Goal
The project workspace was just migrated from `C:\Users\sanja\Documents\miners` to `E:\miners`. The new agent should read this document to understand the full technical constraints and aesthetic preferences before proceeding with new code or infographic generation.
