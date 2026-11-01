#!/usr/bin/env python3
"""
AI-Deck Mixed-Signal Closed-Loop Autograder Verification:
ESP32-S3 (I2C DAC Master) -> MCP4725 VOUT -> Pico 2 (ADC2 on GP28)

Measures:
  1. I2C Bus Sniffing & ACK Verification
  2. SPI Burst Sniffing
  3. Closed-Loop Analog Voltage Verification (Expected vs Measured)
"""

import sys
import time
import json
import threading
import re
import serial

ESP_PORT = "COM3"
PICO_PORT = "COM8"
DURATION_SEC = 12

print("==================================================================")
print("   AI-Deck Closed-Loop Autograder: MCP4725 DAC <-> Pico 2 ADC2   ")
print("==================================================================")
print(f"[*] ESP32-S3 Master Port : {ESP_PORT}")
print(f"[*] Pico 2 Sniffer/ADC   : {PICO_PORT}")
print(f"[*] Target Hardware      : SparkFun MCP4725 on I2C 0x60")
print(f"[*] Analog Feedback Pin  : Pico GP28 (ADC2)")
print("==================================================================\n")

esp_ser = serial.Serial(ESP_PORT, 115200, timeout=0.5)
pico_ser = serial.Serial(PICO_PORT, 115200, timeout=0.5)
time.sleep(0.2)

stop_event = threading.Event()
results = []
current_target_v = None

def esp_reader():
    global current_target_v
    while not stop_event.is_set():
        if esp_ser.in_waiting:
            line = esp_ser.readline().decode("utf-8", errors="ignore").strip()
            if line:
                m = re.search(r"Target:\s*([\d\.]+)\s*V.*I2C ACK:\s*(.*)", line)
                if m:
                    target_v = float(m.group(1))
                    ack_status = m.group(2).strip()
                    current_target_v = target_v
                    print(f"\n[ESP32 MASTER] -> Set DAC Output: {target_v:.2f} V | ACK: {ack_status}")
                elif "I2C SCAN" in line or "STEP" in line:
                    print(f"[ESP32 MASTER] {line}")
        time.sleep(0.01)

def pico_reader():
    global current_target_v
    while not stop_event.is_set():
        if pico_ser.in_waiting:
            line = pico_ser.readline().decode("utf-8", errors="ignore").strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    data = json.loads(line)
                    ev = data.get("event")
                    if ev == "I2C_FRAME":
                        target_addr = data.get("target_addr")
                        adc_v = data.get("adc2_v")
                        frames = data.get("frames", [])
                        print(f"  [PICO SNIFFER] Captured I2C to {target_addr} | ADC2 Measured: {adc_v:.3f} V")
                        if current_target_v is not None and adc_v is not None:
                            error_mv = abs(adc_v - current_target_v) * 1000.0
                            passed = error_mv < 150.0  # Allow up to 150mV margin (resistor divider / ADC calibration)
                            status_str = "PASS" if passed else "WARN"
                            print(f"  --> [AUTOGRADER EVAL] Expected: {current_target_v:.2f}V | Measured: {adc_v:.3f}V | Error: {error_mv:.1f} mV [{status_str}]")
                            results.append({
                                "target": current_target_v,
                                "measured": adc_v,
                                "error_mv": error_mv,
                                "passed": passed
                            })
                    elif ev == "SPI_BURST":
                        print(f"  [PICO SPI] Intercepted 5 bytes: {data.get('bytes')}")
                except Exception:
                    pass
        time.sleep(0.01)

t1 = threading.Thread(target=esp_reader, daemon=True)
t2 = threading.Thread(target=pico_reader, daemon=True)

t1.start()
t2.start()

time.sleep(DURATION_SEC)
stop_event.set()

t1.join(timeout=1.0)
t2.join(timeout=1.0)
esp_ser.close()
pico_ser.close()

print("\n==================================================================")
print("   FINAL AUTOGRADER REPORT: CLOSED-LOOP MIXED-SIGNAL DAC TEST     ")
print("==================================================================")
if results:
    passed_count = sum(1 for r in results if r["passed"])
    print(f"Total Voltage Steps Evaluated : {len(results)}")
    print(f"Steps Passing Tolerance (±150mV): {passed_count}/{len(results)}")
    for i, r in enumerate(results):
        print(f"  Step #{i+1}: Expected {r['target']:.2f}V -> Measured {r['measured']:.3f}V (Err: {r['error_mv']:.1f}mV) {'[OK]' if r['passed'] else '[FAIL]'}")
    score = (passed_count / len(results)) * 100.0
    print(f"\nAutograder Verification Score : {score:.1f}%")
else:
    print("[!] No evaluation steps captured. Check power and connections.")
print("==================================================================\n")
