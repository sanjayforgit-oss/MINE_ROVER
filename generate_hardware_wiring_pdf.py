import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def build_wiring_pdf():
    pdf_filename = "MINERS_Hardware_Wiring_Guide.pdf"
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a'),
        alignment=1,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#0284c7'),
        alignment=1,
        spaceAfter=10
    )

    h2_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=14.5,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=9,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#334155'),
        spaceAfter=4
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#991b1b')
    )

    story = []

    # Title & Header
    story.append(Paragraph("M.I.N.E.R.S. ROVER HARDWARE WIRING GUIDE", title_style))
    story.append(Paragraph("Arduino Mega 2560 (Master) + Wemos D1 ESP8266 (Wi-Fi Bridge) | 4-Direction Dual Sonar", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284c7'), spaceAfter=8))

    # Common Ground Box
    warning_data = [[
        Paragraph("<b>CRITICAL COMMON GROUND:</b> Connect all GND lines together on the Breadboard Negative Rail (-): Arduino Mega GND, Wemos D1 GND, all 8 Sonar GNDs, all 3 Gas Sensor GNDs, Left L298N GND, Right L298N GND, and both Battery Negative Black Wires.", callout_style)
    ]]
    warning_table = Table(warning_data, colWidths=[540])
    warning_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fef2f2')),
        ('BORDER', (0,0), (-1,-1), 1, colors.HexColor('#f87171')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(warning_table)
    story.append(Spacer(1, 4))

    # Section 1: Power & Battery
    story.append(Paragraph("1. Power Distribution", h2_style))
    story.append(Paragraph("• <b>Logic Power:</b> USB Powerbank plugs into <b>Arduino Mega 2560 USB port</b>. Connect <b>Mega 5V</b> to <b>Breadboard +5V Rail</b>. Connect <b>Wemos D1 5V/VIN</b> to <b>Breadboard +5V Rail</b>.<br/>• <b>Motor Power:</b> Battery Pack 1 (+7.6V) to <b>Left L298N VCC</b>. Battery Pack 2 (+7.6V) to <b>Right L298N VCC</b>. Both Battery (-) black wires to <b>Breadboard GND Rail (-)</b>.", body_style))
    story.append(Spacer(1, 4))

    # Section 2: Mega to Wemos D1
    story.append(Paragraph("2. Arduino Mega 2560 <---> Wemos D1 ESP8266 Serial Link", h2_style))
    comm_data = [
        ["Arduino Mega 2560 Pin", "Wemos D1 ESP8266 Pin", "Function"],
        ["TX1 (Pin 18)", "RX (GPIO 3)", "Mega sends telemetry string to Wemos Wi-Fi bridge"],
        ["RX1 (Pin 19)", "TX (GPIO 1)", "Wemos sends laptop commands to Mega"],
        ["GND", "GND", "Common Ground Reference"]
    ]
    comm_table = Table(comm_data, colWidths=[150, 160, 230])
    comm_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0284c7')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('PADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(comm_table)
    story.append(Spacer(1, 4))

    # Section 3: Mega to Dual L298N
    story.append(Paragraph("3. Arduino Mega 2560 to Dual L298N Motor Drivers", h2_style))
    story.append(Paragraph("<i>Remove black jumpers from ENA and ENB on both L298N boards.</i>", body_style))
    motor_data = [
        ["Driver / Motor", "Arduino Mega 2560 Pin", "Function"],
        ["Left L298N -> IN1", "Pin 30", "Left Motors Direction 1"],
        ["Left L298N -> IN2", "Pin 31", "Left Motors Direction 2"],
        ["Left L298N -> ENA", "Pin 2 (PWM)", "Left Motors PWM Speed"],
        ["Left L298N OUT1 & OUT2", "Left-Front + Left-Rear Motors", "Parallel Motor Pair Wires"],
        ["Right L298N -> IN3", "Pin 32", "Right Motors Direction 1"],
        ["Right L298N -> IN4", "Pin 33", "Right Motors Direction 2"],
        ["Right L298N -> ENB", "Pin 3 (PWM)", "Right Motors PWM Speed"],
        ["Right L298N OUT3 & OUT4", "Right-Front + Right-Rear Motors", "Parallel Motor Pair Wires"]
    ]
    motor_table = Table(motor_data, colWidths=[160, 180, 200])
    motor_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('PADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(motor_table)
    story.append(Spacer(1, 4))

    # Section 4: 4-Direction Dual Sonar
    story.append(Paragraph("4. 4-Direction Dual Ultrasonic Array (2 Sensors per Direction = 8 Total)", h2_style))
    story.append(Paragraph("<i>All 8 Sonar VCC -> Breadboard +5V Rail | All 8 Sonar GND -> Breadboard GND Rail (-)</i>", body_style))
    sonar_data = [
        ["Direction Zone", "Sensor Unit", "Trig Pin (Mega)", "Echo Pin (Mega)"],
        ["FRONT DIRECTION", "Front-1 Sensor", "Pin 22", "Pin 23"],
        ["FRONT DIRECTION", "Front-2 Sensor", "Pin 42", "Pin 43"],
        ["RIGHT DIRECTION", "Right-1 Sensor", "Pin 26", "Pin 27"],
        ["RIGHT DIRECTION", "Right-2 Sensor", "Pin 46", "Pin 47"],
        ["REAR DIRECTION",  "Rear-1 Sensor",  "Pin 50", "Pin 51"],
        ["REAR DIRECTION",  "Rear-2 Sensor",  "Pin 48", "Pin 49"],
        ["LEFT DIRECTION",  "Left-1 Sensor",  "Pin 24", "Pin 25"],
        ["LEFT DIRECTION",  "Left-2 Sensor",  "Pin 40", "Pin 41"]
    ]
    sonar_table = Table(sonar_data, colWidths=[140, 130, 130, 140])
    sonar_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0284c7')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('PADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(sonar_table)
    story.append(Spacer(1, 4))

    # Section 5: Mega to 3 Gas Sensors
    story.append(Paragraph("5. Arduino Mega 2560 to 3x Gas Sensor Array", h2_style))
    gas_data = [
        ["Sensor Module", "Analog Output Pin (AO)", "Arduino Mega 2560 Pin", "Target Gas Detected"],
        ["MQ-4", "AO Wire", "Pin A0", "CH4 Methane Gas"],
        ["MQ-7", "AO Wire", "Pin A1", "Carbon Monoxide (CO)"],
        ["MQ-2", "AO Wire", "Pin A2", "Smoke / LPG / Flammable Gas"]
    ]
    gas_table = Table(gas_data, colWidths=[130, 130, 130, 150])
    gas_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#059669')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('PADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(gas_table)

    doc.build(story)
    print(f"Generated PDF successfully: {pdf_filename}")

if __name__ == '__main__':
    build_wiring_pdf()
