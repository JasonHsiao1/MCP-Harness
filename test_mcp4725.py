#!/usr/bin/env python3
"""
AI-Deck MCP4725 DAC Quick Verification via Pico 2 Co-Processor.
"""
import sys
import time
import json
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HARNESS_DIR))

try:
    from port_detect import detect_ports
except ImportError:
    def detect_ports(esp_override=None, pico_override=None):
        return (esp_override or "/dev/ttyACM1"), (pico_override or "/dev/ttyACM0")

try:
    import serial
except ImportError:
    print("Error: pyserial is required. Run: pip install pyserial")
    sys.exit(1)

cli_pico = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None
_, pico_port = detect_ports(pico_override=cli_pico)

print("==================================================================")
print("   AI-Deck Mixed-Signal Test: MCP4725 DAC & Pico 2 ADC2           ")
print("==================================================================")
print(f"[*] Connecting to Pico 2 on : {pico_port}")
print("==================================================================\n")

try:
    ser = serial.Serial(pico_port, 115200, timeout=1.0)
except Exception as e:
    print(f"[!] Could not open port {pico_port}: {e}")
    sys.exit(1)

time.sleep(0.2)

# Ping
ser.write(b'{"cmd": "PING"}\n')
time.sleep(0.1)
print("[1] PING:", ser.readline().decode().strip())

# Health & ADC2
ser.write(b'{"cmd": "HEALTH"}\n')
time.sleep(0.1)
h = ser.readline().decode().strip()
print("[2] HEALTH & ADC2:", h)

# Active I2C Scan
ser.write(b'{"cmd": "SCAN"}\n')
time.sleep(0.3)
scan_resp = ser.readline().decode().strip()
print("[3] ACTIVE I2C SCAN FROM PICO:", scan_resp)

ser.close()
