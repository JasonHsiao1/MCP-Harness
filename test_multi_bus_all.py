#!/usr/bin/env python3
"""
AI-Deck Complete Hardware Validation Suite:
Tests 4 simultaneous hardware subsystems:
  1. I2C Bus & MCP4725 DAC (ESP32 p8/p9 <-> Pico GP16/17 <-> MCP4725)
  2. SPI Bus (ESP32 p10/11/12/13 <-> Pico GP0/1/2/3)
  3. UART Full-Duplex (ESP32 p43 TX -> Pico GP5 RX, Pico GP4 TX -> ESP32 p44 RX)
  4. Analog Mixed-Signal (MCP4725 VOUT -> Pico GP28 ADC2)
"""

import sys
import time
import json
import threading
import serial

ESP_PORT = "COM3"
PICO_PORT = "COM8"
DURATION_SEC = 10

print("==================================================================")
print("   AI-Deck Multi-Bus & Mixed-Signal Verification Suite             ")
print("==================================================================")
print(f"[*] ESP32-S3 Master Port : {ESP_PORT}")
print(f"[*] Pico 2 Sniffer Port  : {PICO_PORT}")
print("[*] Subsystems Tested    : I2C (0x60) + SPI (1MHz) + UART0 + ADC2")
print("==================================================================\n")

esp_ser = serial.Serial(ESP_PORT, 115200, timeout=0.5)
pico_ser = serial.Serial(PICO_PORT, 115200, timeout=0.5)
time.sleep(0.2)

stop_event = threading.Event()
uart_verified = False
spi_verified = False
i2c_verified = False
adc_verified = False

def esp_monitor():
    global uart_verified, i2c_verified
    while not stop_event.is_set():
        if esp_ser.in_waiting:
            line = esp_ser.readline().decode("utf-8", errors="ignore").strip()
            if line:
                if "UART RX ECHO" in line:
                    print(f"  [FULL DUPLEX UART] {line}")
                    uart_verified = True
                elif "I2C ACK: YES" in line:
                    print(f"  [I2C MASTER] {line}")
                    i2c_verified = True
                elif "STEP" in line or "I2C SCAN" in line:
                    print(f"  [ESP32] {line}")
        time.sleep(0.01)

def pico_monitor():
    global spi_verified, adc_verified
    while not stop_event.is_set():
        if pico_ser.in_waiting:
            line = pico_ser.readline().decode("utf-8", errors="ignore").strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    data = json.loads(line)
                    ev = data.get("event")
                    if ev == "UART_RX":
                        print(f"  [PICO UART RX] Pico GP5 received: '{data.get('text')}'")
                    elif ev == "SPI_BURST":
                        spi_verified = True
                    elif ev == "I2C_FRAME":
                        adc_v = data.get("adc2_v")
                        if adc_v and adc_v > 0.4:
                            adc_verified = True
                            print(f"  [PICO I2C+ADC] Frame to {data.get('target_addr')} | ADC2 Measured: {adc_v:.3f} V")
                except Exception:
                    pass
        time.sleep(0.01)

t_esp = threading.Thread(target=esp_monitor, daemon=True)
t_pico = threading.Thread(target=pico_monitor, daemon=True)

t_esp.start()
t_pico.start()

time.sleep(DURATION_SEC)
stop_event.set()

t_esp.join(timeout=1.0)
t_pico.join(timeout=1.0)
esp_ser.close()
pico_ser.close()

print("\n==================================================================")
print("   HARDWARE SUBSYSTEM VERIFICATION REPORT                         ")
print("==================================================================")
print(f"  1. I2C Bus & DAC Control (ESP32 p8/p9 <-> MCP4725) : {'[PASS]' if i2c_verified else '[FAIL]'}")
print(f"  2. SPI Bus Sniffing (ESP32 p10-12 <-> Pico GP0-2)   : {'[PASS]' if spi_verified else '[FAIL]'}")
print(f"  3. UART Full-Duplex (ESP32 p43/44 <-> Pico GP4/5)  : {'[PASS]' if uart_verified else '[FAIL]'}")
print(f"  4. Analog Feedback Verification (GP28 ADC2)         : {'[PASS]' if adc_verified else '[FAIL]'}")
print("==================================================================\n")
