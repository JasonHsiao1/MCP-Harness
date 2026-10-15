#!/usr/bin/env python3
"""
Quick JTAG connectivity test for ESP32-S3 via OpenOCD.
Tests whether OpenOCD can bind to the ESP32-S3 built-in USB-JTAG interface.
"""

import sys
import subprocess
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HARNESS_DIR))

from config import OPENOCD_EXE

def test_jtag():
    print(f"[TEST] Using OpenOCD: {OPENOCD_EXE}")
    scripts_dir = OPENOCD_EXE.parent.parent / "share" / "openocd" / "scripts"
    
    cmd = [
        str(OPENOCD_EXE),
        "-s", str(scripts_dir),
        "-f", "board/esp32s3-builtin.cfg",
        "-c", "init; targets; exit"
    ]
    
    print("[TEST] Running OpenOCD probe check...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    if res.returncode == 0:
        print("\n===========================================")
        print("  SUCCESS! OpenOCD connected to ESP32-S3!  ")
        print("===========================================")
        print(res.stdout)
        return True
    else:
        print("\n===========================================")
        print("  OpenOCD connection attempt: FAILED       ")
        print("===========================================")
        print("Output:", res.stdout)
        print("Error:", res.stderr)
        return False

if __name__ == "__main__":
    test_jtag()
