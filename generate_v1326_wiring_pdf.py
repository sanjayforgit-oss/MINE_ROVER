"""
Dual BTS7960 (IBT-2) Motor Drivers & 12V Battery Wiring Diagram PDF Generator
-----------------------------------------------------------------------------
Generates a PDF Wiring Reference Guide for the M.I.N.E.R.S. Rover prototype
using TWO BTS7960 43A High-Power Motor Driver Modules (Left Driver & Right Driver),
12V DC Motors, 12V Dedicated Battery, and Arduino Mega 2560 Master.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

OUTPUT_PDF = os.path.join(os.path.dirname(__file__), "BTS7960_Dual_Driver_12V_Wiring_Guide.pdf")

def generate_pdf():
    doc = SimpleDocTemplate(
        OUTPUT_PDF,
        pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#0055aa'), leading=22, spaceAfter=8)
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=13, textColor=colors.HexColor('#222222'), leading=16, spaceBefore=10, spaceAfter=4)
    body_style = ParagraphStyle('Body', parent=styles['BodyText'], fontSize=9.5, textColor=colors.HexColor('#333333'), leading=13, spaceAfter=5)
    alert_style = ParagraphStyle('Alert', parent=styles['BodyText'], fontSize=9.5, textColor=colors.HexColor('#cc0000'), leading=13, spaceAfter=5)

    elements = []

    # Title
    elements.append(Paragraph("M.I.N.E.R.S. Rover - Dual BTS7960 Motor Drivers Wiring Guide", title_style))
    elements.append(Paragraph("Configuration: 2x BTS7960 (IBT-2) 43A High-Power Drivers (Left Side Driver & Right Side Driver), Dedicated 12V Battery, 4WD DC Motors, Arduino Mega 2560", body_style))
    elements.append(Spacer(1, 8))

    # Alert
    elements.append(Paragraph("<b>CRITICAL SAFETY RULE: COMMON GROUND</b>", alert_style))
    elements.append(Paragraph("The 12V Battery Negative Terminal (B-) MUST be connected to BOTH Motor Drivers' B- slots AND to an Arduino Mega GND pin for a shared common ground reference.", alert_style))
    elements.append(Spacer(1, 8))

    # Table 1: Power & Battery Connections for BOTH Drivers
    elements.append(Paragraph("1. Power Terminals (12V Battery $\rightarrow$ Both Motor Drivers)", heading_style))
    power_data = [
        ["Driver Module", "Terminal Slot", "Connection Target", "Cable Type & Details"],
        ["DRIVER 1 (Left)", "B+", "12V Battery POSITIVE (+)", "Thick Power Cable (16 AWG)"],
        ["DRIVER 1 (Left)", "B-", "12V Battery NEGATIVE (-)", "Thick Power Cable (Connect to Arduino GND!)"],
        ["DRIVER 2 (Right)", "B+", "12V Battery POSITIVE (+)", "Thick Power Cable (16 AWG)"],
        ["DRIVER 2 (Right)", "B-", "12V Battery NEGATIVE (-)", "Thick Power Cable (Connect to Arduino GND!)"]
    ]
    t_power = Table(power_data, colWidths=[110, 90, 180, 160])
    t_power.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0055aa')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f9f9f9')),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_power)
    elements.append(Spacer(1, 10))

    # Table 2: Motor Outputs (Left Driver & Right Driver)
    elements.append(Paragraph("2. Motor Outputs (Connecting 4 Motors across 2 Drivers)", heading_style))
    motor_data = [
        ["Driver Module", "Output Slots", "Connected Motors", "Wiring Setup"],
        ["DRIVER 1 (Left Side)", "M+ & M-", "Front-Left Motor & Rear-Left Motor", "Wire Both Left Motors in Parallel to Driver 1"],
        ["DRIVER 2 (Right Side)", "M+ & M-", "Front-Right Motor & Rear-Right Motor", "Wire Both Right Motors in Parallel to Driver 2"]
    ]
    t_motor = Table(motor_data, colWidths=[130, 90, 170, 150])
    t_motor.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#aa5500')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#fffaf5')),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_motor)
    elements.append(Spacer(1, 10))

    # Table 3: Control Logic Header Pins for Driver 1 (Left) & Driver 2 (Right)
    elements.append(Paragraph("3. Control Signal Pins (Arduino Mega 2560 $\rightarrow$ Both Motor Drivers)", heading_style))
    control_data = [
        ["BTS7960 Header Pin", "DRIVER 1 (Left Side)", "DRIVER 2 (Right Side)", "Function / Purpose"],
        ["VCC", "Arduino Mega 5V", "Arduino Mega 5V", "Logic 5V Power for Optocoupler Isolator"],
        ["GND", "Arduino Mega GND", "Arduino Mega GND", "Logic Signal Ground Reference"],
        ["R_EN (Right Enable)", "Arduino Pin D30 (or 5V)", "Arduino Pin D32 (or 5V)", "Forward Half-Bridge Enable"],
        ["L_EN (Left Enable)", "Arduino Pin D30 (or 5V)", "Arduino Pin D32 (or 5V)", "Reverse Half-Bridge Enable"],
        ["RPWM (Right PWM)", "Arduino Pin D2 (PWM)", "Arduino Pin D4 (PWM)", "Forward Speed PWM Signal (0-255)"],
        ["LPWM (Left PWM)", "Arduino Pin D3 (PWM)", "Arduino Pin D5 (PWM)", "Reverse Speed PWM Signal (0-255)"],
        ["R_IS & L_IS", "LEAVE UNCONNECTED", "LEAVE UNCONNECTED", "Current Sensing Output (Not Needed)"]
    ]
    t_control = Table(control_data, colWidths=[110, 130, 130, 170])
    t_control.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#008855')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f4fbf7')),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_control)
    elements.append(Spacer(1, 10))

    # Testing Tip
    elements.append(Paragraph("<b>Motor Direction Check</b>", heading_style))
    elements.append(Paragraph("If the Left or Right wheels rotate backward when driving FORWARD ('CMD:F' or 'W'), simply swap M+ and M- wires for that specific driver module!", body_style))

    doc.build(elements)
    print(f"Generated Dual BTS7960 PDF Guide: {OUTPUT_PDF}")

if __name__ == "__main__":
    generate_pdf()
