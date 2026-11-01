#!/usr/bin/env python3
import sys
import time
import json
import serial

pico_port = "COM8"
esp_port = "COM3"

print("==================================================================")
print("   AI-Deck Mixed-Signal Test: MCP4725 DAC & Pico 2 ADC2           ")
print("==================================================================")

ser = serial.Serial(pico_port, 115200, timeout=1.0)
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
