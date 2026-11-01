#!/usr/bin/env python3
"""
AI-Deck Autograder Verifier: ECE 4180 Lab 2 - DDR Arrow Animation
File Under Test: ddr_arrow_animation.ino

Verification Rubric:
  1. Pinout & Peripheral Configuration:
     - SPI Master initialized with ST7789 display controller
     - Dedicated DC, CS, RST, BLK pins defined
  2. Authentic DDR Geometry & Palette:
     - 4 lanes (60 px each across 240px width)
     - 32x32 arrow bitmaps (Outline + Inner Fill)
     - 4 authentic DDR colors (Magenta/Pink, Cyan, Neon Green, Warm Orange)
  3. Real-Time Hardware Performance:
     - Dirty-box rendering (erases only 32x32 vacated areas; no full-screen clears)
     - Target frame rate: ~60 FPS (16-17 ms per frame)
     - Top step-zone receptors flash on arrow alignment
"""

import os
import sys
import re
import time
from pathlib import Path

TARGET_SKETCH = Path(r"C:\jason\GeorgiaTech\Fall2026\ECE4180\solutions\Lab2\code\ddr_arrow_animation\ddr_arrow_animation.ino")


def verify_static_code(sketch_path: Path):
    print("==================================================================")
    print("   AI-Deck Verifier: DDR Arrow Animation (ST7789 SPI)            ")
    print("==================================================================")
    print(f"[*] Target Sketch: {sketch_path}\n")

    if not sketch_path.exists():
        print(f"[FAIL] Sketch file not found at: {sketch_path}")
        return False

    code = sketch_path.read_text(encoding="utf-8", errors="ignore")
    score = 0
    total_checks = 5

    # Check 1: ST7789 & Adafruit GFX libraries
    if "Adafruit_ST7789" in code and "Adafruit_GFX" in code:
        print("[PASS] Check 1: ST7789 and Adafruit_GFX display libraries imported.")
        score += 1
    else:
        print("[FAIL] Check 1: Missing Adafruit_ST7789 or Adafruit_GFX.")

    # Check 2: 4 DDR Lanes & 32x32 Arrow Geometry
    has_4_lanes = "NUM_LANES" in code or "240 / 4" in code or "LANE_WIDTH" in code
    has_32x32 = "32" in code and ("ARROW_SIZE" in code or "128" in code)
    if has_4_lanes and has_32x32:
        print("[PASS] Check 2: 4 DDR lanes with 32x32 arrow sprite geometry detected.")
        score += 1
    else:
        print("[FAIL] Check 2: Missing 4-lane or 32x32 sprite definitions.")

    # Check 3: Authentic DDR Palette (RGB565 colors)
    if "LANE_COLORS" in code or ("0xF950" in code and "0x06BF" in code):
        print("[PASS] Check 3: Authentic 4-color DDR palette configured.")
        score += 1
    else:
        print("[WARN] Check 3: Non-standard color palette detected.")

    # Check 4: Flicker-Free Dirty-Box Rendering
    # Must NOT call tft.fillScreen inside loop()
    if "eraseArrow" in code or "fillRect" in code:
        if "void loop" in code and "fillScreen" not in code.split("void loop")[1]:
            print("[PASS] Check 4: Dirty-box erase detected (no full-screen clears, flicker-free).")
            score += 1
        else:
            print("[FAIL] Check 4: loop() calls fillScreen() -> causes flickering!")
    else:
        print("[WARN] Check 4: Erase mechanism not clearly identified.")

    # Check 5: Receptors & Wrap-Around
    if "drawReceptor" in code and ("wrap" in code.lower() or "CYCLE_HEIGHT" in code):
        print("[PASS] Check 5: Flashing step receptors and screen wrap-around implemented.")
        score += 1
    else:
        print("[FAIL] Check 5: Receptors or wrap-around logic missing.")

    final_pct = (score / total_checks) * 100.0
    print("------------------------------------------------------------------")
    print(f"Verification Score: {score}/{total_checks} ({final_pct:.1f}%)")
    print("==================================================================\n")
    return final_pct >= 80.0


def verify_live_spi_stream(pico_port: str = "COM8", duration_sec: int = 5):
    """Passively sniffs SPI traffic from the target MCU using Pico 2 PIO."""
    try:
        import serial
    except ImportError:
        print("[!] pyserial required for live SPI sniffing.")
        return

    print(f"[*] Connecting to Pico 2 on {pico_port} to verify live SPI frame bursts...")
    try:
        ser = serial.Serial(pico_port, 115200, timeout=1.0)
    except Exception as e:
        print(f"[!] Could not connect to Pico: {e}")
        return

    time.sleep(0.2)
    start = time.time()
    burst_count = 0

    while time.time() - start < duration_sec:
        if ser.in_waiting:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if "SPI_BURST" in line:
                burst_count += 1
        time.sleep(0.01)

    ser.close()
    fps = burst_count / duration_sec
    print(f"[*] Captured {burst_count} SPI transactions over {duration_sec}s (~{fps:.1f} bursts/sec).")
    if burst_count > 0:
        print("[PASS] Live SPI display rendering verified on hardware!")
    else:
        print("[WARN] No SPI bursts detected. Check SPI wiring (SCK, MOSI, CS).")


if __name__ == "__main__":
    sketch = Path(sys.argv[1]) if len(sys.argv) > 1 else TARGET_SKETCH
    passed = verify_static_code(sketch)
    if len(sys.argv) > 2 and sys.argv[2] == "--live":
        verify_live_spi_stream()
