#!/usr/bin/env python3
"""
AI-Deck Bus Concept Verification Script
Tests I2C and SPI communication between ESP32-S3 (DUT Master) and Pico 2 (Co-Processor Sniffer).

Pin Connections Tested:
  - ESP32 GPIO 12 -> Pico GP2  (SPI SCK)
  - ESP32 GPIO 10 -> Pico GP1  (SPI CSn)
  - ESP32 GPIO 11 -> Pico GP0  (SPI MOSI)
  - ESP32 GPIO 13 -> Pico GP3  (SPI MISO)
  - ESP32 GPIO 8  -> Pico GP16 (I2C SDA)
  - ESP32 GPIO 9  -> Pico GP17 (I2C SCL)
"""

import sys
import time
import json
import threading
from pathlib import Path

# Add harness dir to sys.path
HARNESS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HARNESS_DIR))

try:
    from port_detect import detect_ports
except ImportError:
    def detect_ports(esp_override=None, pico_override=None):
        return (esp_override or "/dev/ttyACM1"), (pico_override or "/dev/ttyACM0")

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("Error: pyserial is required. Run: pip install pyserial")
    sys.exit(1)


def run_bus_test(esp32_port: str, pico_port: str, duration_sec: int = 10):
    print("==================================================================")
    print("   AI-Deck Bus Test: ESP32-S3 <-> Pico 2 (RP2350)                 ")
    print("==================================================================")
    print(f"[*] ESP32-S3 Master Port : {esp32_port}")
    print(f"[*] Pico 2 Sniffer Port  : {pico_port}")
    print(f"[*] Test Duration        : {duration_sec} seconds")
    print("==================================================================\n")

    try:
        pico_ser = serial.Serial(pico_port, 115200, timeout=1.0)
    except Exception as e:
        print(f"[!] Could not open Pico port ({pico_port}): {e}")
        return
    time.sleep(0.1)

    # 1. Ping Pico 2
    print("[1/3] Pinging Pico 2 Co-Processor...")
    pico_ser.write(b'{"cmd": "PING"}\n')
    time.sleep(0.2)
    resp = pico_ser.readline().decode("utf-8", errors="ignore").strip()
    print(f"      Response: {resp}")

    # 2. Check Bus Electrical Levels
    print("\n[2/3] Checking Bus Electrical Health...")
    pico_ser.write(b'{"cmd": "HEALTH"}\n')
    time.sleep(0.2)
    resp = pico_ser.readline().decode("utf-8", errors="ignore").strip()
    try:
        health = json.loads(resp)
        i2c_h = health.get("i2c", {})
        spi_h = health.get("spi", {})
        print(f"      I2C Lines: SDA(GP16)={i2c_h.get('sda_gp16')}, SCL(GP17)={i2c_h.get('scl_gp17')}")
        print(f"      I2C Pull-ups Present: {i2c_h.get('pullups_detected')}")
        print(f"      SPI Lines: SCK(GP2)={spi_h.get('sck_gp2')}, CS(GP1)={spi_h.get('cs_gp1')}, MOSI(GP0)={spi_h.get('mosi_gp0')}")
    except Exception:
        print(f"      Raw Health Response: {resp}")

    # 3. Stream Live Packet Telemetry
    print(f"\n[3/3] Capturing Real-Time Traffic for {duration_sec}s...")
    print("------------------------------------------------------------------")

    stop_event = threading.Event()

    def read_esp32():
        try:
            esp_ser = serial.Serial(esp32_port, 115200, timeout=0.5)
            while not stop_event.is_set():
                if esp_ser.in_waiting:
                    line = esp_ser.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        print(f"  [ESP32-S3 TX] {line}")
                time.sleep(0.01)
            esp_ser.close()
        except Exception as e:
            print(f"  [!] ESP32 monitor error: {e}")

    def read_pico():
        try:
            while not stop_event.is_set():
                if pico_ser.in_waiting:
                    line = pico_ser.readline().decode("utf-8", errors="ignore").strip()
                    if line.startswith("{") and line.endswith("}"):
                        try:
                            data = json.loads(line)
                            ev = data.get("event")
                            if ev == "SPI_BURST":
                                print(f"  --> [PICO SPI RX] {data.get('bytes')} (len={data.get('length')})")
                            elif ev == "I2C_FRAME":
                                addr = data.get('target_addr') or data.get('address')
                                rw = data.get('rw', '?')
                                frames = data.get('frames') or data.get('payload') or []
                                frame_str = ", ".join([f"{f.get('byte')}(ACK={f.get('ack')})" for f in frames if isinstance(f, dict)]) or str(frames)
                                print(f"  --> [PICO I2C RX] Target Addr: {addr} ({rw}) | Bytes: [{frame_str}]")
                            else:
                                print(f"  --> [PICO EVENT] {line}")
                        except Exception:
                            print(f"  --> [PICO] {line}")
                    elif line:
                        print(f"  --> [PICO] {line}")
                time.sleep(0.01)
        except Exception as e:
            print(f"  [!] Pico monitor error: {e}")

    t_esp = threading.Thread(target=read_esp32, daemon=True)
    t_pico = threading.Thread(target=read_pico, daemon=True)

    t_esp.start()
    t_pico.start()

    time.sleep(duration_sec)
    stop_event.set()
    t_esp.join(timeout=1.0)
    t_pico.join(timeout=1.0)
    pico_ser.close()

    print("------------------------------------------------------------------")
    print("[SUCCESS] Test capture complete!\n")


if __name__ == "__main__":
    cli_arg1 = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None
    cli_arg2 = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("-") else None
    duration = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    esp_port, pico_port = detect_ports(cli_arg1, cli_arg2)

    # Check for inverted arguments
    try:
        for p in serial.tools.list_ports.comports():
            if p.device == esp_port and p.vid == 0x2E8A:
                esp_port, pico_port = pico_port, esp_port
                break
    except Exception:
        pass

    run_bus_test(esp_port, pico_port, duration_sec=duration)
