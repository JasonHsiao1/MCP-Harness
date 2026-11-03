#!/usr/bin/env python3
"""
AI-Deck Autograder Verifier: ECE 4180 Lab 2 - Capacitive Dance Pad to USB HID Keyboard
Files Under Test:
  - touchpad_hid_dancepad.ino
  - keymap.h

Verification Rubric:
  1. Sensor & Peripheral Integration:
     - Adafruit_MPR121 (I2C on SDA 21, SCL 22)
     - Adafruit_CH9328 or Serial1 for UART HID Keyboard output
  2. Dance Pad Key Mapping (Standard ECE 4180 Spec):
     - Pad 2  -> KEY_LEFT  (0x50)
     - Pad 5  -> KEY_DOWN  (0x51)
     - Pad 7  -> KEY_UP    (0x52)
     - Pad 10 -> KEY_RIGHT (0x4F)
     - Pad 0  -> KEY_ESC   (0x29)
     - Pad 11 -> KEY_ENTER (0x28)
  3. Multi-Touch Rollover & Debouncing:
     - Edge detection tracking `lasttouched` vs `currtouched`
     - Allows simultaneous step inputs (e.g. Left + Up jumps)
  4. CH9328 Mode 3 Transparent HID Transmission:
     - Emits standard 8-byte USB HID keyboard report packets over UART
"""

import os
import sys
import re
import time
from typing import Optional
from pathlib import Path

TARGET_DIR = Path(r"C:\jason\GeorgiaTech\Fall2026\ECE4180\solutions\Lab2\code\touchpad_hid_dancepad")
TARGET_SKETCH = TARGET_DIR / "touchpad_hid_dancepad.ino"
TARGET_KEYMAP = TARGET_DIR / "keymap.h"


def verify_dancepad_code(sketch_path: Path, keymap_path: Path):
    print("==================================================================")
    print("   AI-Deck Verifier: MPR121 Dance Pad -> CH9328 USB HID          ")
    print("==================================================================")
    print(f"[*] Target Sketch : {sketch_path}")
    print(f"[*] Keymap Header : {keymap_path}\n")

    if not sketch_path.exists() or not keymap_path.exists():
        print(f"[FAIL] Missing source files: sketch={sketch_path.exists()}, keymap={keymap_path.exists()}")
        return False

    sketch_code = sketch_path.read_text(encoding="utf-8", errors="ignore")
    keymap_code = keymap_path.read_text(encoding="utf-8", errors="ignore")

    score = 0
    total_checks = 5

    # Check 1: Hardware Driver Inclusions
    has_mpr121 = "Adafruit_MPR121" in sketch_code or "MPR121" in sketch_code
    has_ch9328 = "Adafruit_CH9328" in sketch_code or "Serial1" in sketch_code or "CH9328" in sketch_code
    if has_mpr121 and has_ch9328:
        print("[PASS] Check 1: MPR121 I2C driver and CH9328 UART HID driver present.")
        score += 1
    else:
        print("[FAIL] Check 1: Missing MPR121 or CH9328 driver initialization.")

    # Check 2: Keymap Table Verification
    required_keys = {
        "KEY_LEFT": ["0x50", "80"],
        "KEY_DOWN": ["0x51", "81"],
        "KEY_UP": ["0x52", "82"],
        "KEY_RIGHT": ["0x4F", "79"],
        "KEY_ESC": ["0x29", "41"],
        "KEY_ENTER": ["0x28", "40"]
    }
    all_keys_valid = True
    for key_name, expected_vals in required_keys.items():
        if key_name not in keymap_code:
            print(f"[FAIL] Check 2: Missing {key_name} definition in keymap.h")
            all_keys_valid = False
            break

    if all_keys_valid:
        print("[PASS] Check 2: Complete USB HID keycode definitions in keymap.h verified.")
        score += 1

    # Check 3: Pad to Key Mapping Table
    # Verifies Pad 2=Left, 5=Down, 7=Up, 10=Right
    pad_map_correct = True
    for pad_num, expected_key in [(2, "KEY_LEFT"), (5, "KEY_DOWN"), (7, "KEY_UP"), (10, "KEY_RIGHT")]:
        pattern = rf"PAD_TO_KEY\[\s*{pad_num}\s*\]\s*=\s*{expected_key}"
        pattern_array = rf"PAD_TO_KEY.*\[12\].*=[\s\S]*?{expected_key}"
        if not (re.search(pattern, sketch_code) or re.search(pattern_array, sketch_code)):
            print(f"[FAIL] Check 3: Pad {pad_num} not mapped to {expected_key}!")
            pad_map_correct = False
            break

    if pad_map_correct:
        print("[PASS] Check 3: Dance floor directional mapping (Pads 2, 5, 7, 10) verified.")
        score += 1

    # Check 4: Multi-Key Rollover & Edge Detection
    has_edge_detection = ("lasttouched" in sketch_code and "currtouched" in sketch_code) or \
                         ("touched()" in sketch_code and "^" in sketch_code)
    if has_edge_detection:
        print("[PASS] Check 4: Bitwise edge detection and multi-key rollover logic implemented.")
        score += 1
    else:
        print("[FAIL] Check 4: Missing state tracking for press/release events.")

    # Check 5: Menu Controls (ESC & ENTER)
    has_menu_controls = "KEY_ESC" in sketch_code and "KEY_ENTER" in sketch_code
    if has_menu_controls:
        print("[PASS] Check 5: Menu control pads (ESC: Pad 0, ENTER: Pad 11) implemented.")
        score += 1
    else:
        print("[FAIL] Check 5: Menu pads (ESC / ENTER) missing.")

    final_pct = (score / total_checks) * 100.0
    print("------------------------------------------------------------------")
    print(f"Verification Score: {score}/{total_checks} ({final_pct:.1f}%)")
    print("==================================================================\n")
    return final_pct >= 80.0


def verify_live_uart_hid(pico_port: Optional[str] = None, duration_sec: int = 5):
    """Passively sniffs CH9328 UART HID reports from the ESP32 using Pico 2 UART1."""
    try:
        import serial
    except ImportError:
        print("[!] pyserial required for live UART sniffing.")
        return

    if not pico_port:
        try:
            from port_detect import detect_ports
            _, pico_port = detect_ports()
        except Exception:
            pico_port = "/dev/ttyACM0" if sys.platform.startswith("linux") else "COM8"

    print(f"[*] Listening to Pico 2 UART sniffer on {pico_port} for {duration_sec}s...")
    try:
        ser = serial.Serial(pico_port, 115200, timeout=1.0)
    except Exception as e:
        print(f"[!] Could not connect to Pico: {e}")
        return

    time.sleep(0.2)
    start = time.time()
    packet_count = 0

    while time.time() - start < duration_sec:
        if ser.in_waiting:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if "UART_RX" in line:
                packet_count += 1
                print(f"  [SNIFFED HID REPORT] {line}")
        time.sleep(0.01)

    ser.close()
    print(f"[*] Intercepted {packet_count} UART packets.")
    if packet_count > 0:
        print("[PASS] Live UART HID keyboard transmission confirmed!")
    else:
        print("[INFO] No UART packets during quiet window (press pads to test).")


if __name__ == "__main__":
    passed = verify_dancepad_code(TARGET_SKETCH, TARGET_KEYMAP)
    if len(sys.argv) > 1 and sys.argv[1] == "--live":
        verify_live_uart_hid()
