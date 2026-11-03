#!/usr/bin/env python3
"""
AI-Deck Unified Serial Port Detection Utility.
Auto-detects ESP32-S3 (Master DUT) and Raspberry Pi Pico 2 / RP2350 (Co-Processor)
across Windows and Linux (Raspberry Pi Buildroot / Debian).
"""

import os
import sys
import glob
from pathlib import Path
from typing import Tuple, Optional

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None


ESP32_VID = 0x303A
PICO_VID = 0x2E8A


def _read_sysfs_file(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return None


def _find_ports_linux_sysfs() -> Tuple[Optional[str], Optional[str]]:
    """Direct sysfs fallback for minimal Linux environments without full udev."""
    esp_port = None
    pico_port = None

    for tty_path in sorted(glob.glob("/sys/class/tty/ttyACM*") + glob.glob("/sys/class/tty/ttyUSB*")):
        dev_name = os.path.basename(tty_path)
        dev_node = f"/dev/{dev_name}"
        
        # Traverse up sysfs to find idVendor and idProduct
        cur = os.path.join(tty_path, "device")
        for _ in range(4):
            if not os.path.exists(cur):
                break
            vid_file = os.path.join(cur, "idVendor")
            if os.path.isfile(vid_file):
                vid_str = _read_sysfs_file(vid_file)
                if vid_str:
                    vid_val = int(vid_str, 16)
                    if vid_val == ESP32_VID:
                        esp_port = dev_node
                    elif vid_val == PICO_VID:
                        pico_port = dev_node
                break
            cur = os.path.dirname(cur)

    return esp_port, pico_port


def detect_ports(esp_override: Optional[str] = None, pico_override: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolves the ESP32-S3 and Pico 2 serial ports.
    
    Precedence:
      1. Explicit arguments (esp_override, pico_override)
      2. Environment variables (AI_DECK_ESP_PORT, AI_DECK_PICO_PORT)
      3. USB VID/PID matching via pyserial list_ports
      4. Linux sysfs inspection fallback
      5. Sensible defaults based on available devices
    """
    esp_port = esp_override or os.environ.get("AI_DECK_ESP_PORT")
    pico_port = pico_override or os.environ.get("AI_DECK_PICO_PORT")

    if esp_port and pico_port:
        return esp_port, pico_port

    detected_esp = None
    detected_pico = None
    all_devices = []

    if serial and hasattr(serial.tools, "list_ports"):
        for p in serial.tools.list_ports.comports():
            all_devices.append(p.device)
            hwid = (p.hwid or "").upper()
            desc = (p.description or "").upper()
            prod = (getattr(p, "product", "") or "").upper()

            # Check VID/PID
            is_esp = (p.vid == ESP32_VID) or ("303A:1001" in hwid) or ("ESP32" in desc) or ("ESP32" in prod)
            is_pico = (p.vid == PICO_VID) or ("2E8A" in hwid) or ("MICROPYTHON" in desc) or ("PICO" in desc) or ("MICROPYTHON" in prod)

            if is_esp and not detected_esp:
                detected_esp = p.device
            elif is_pico and not detected_pico:
                detected_pico = p.device

    # Linux sysfs fallback if pyserial didn't catch both
    if (not detected_esp or not detected_pico) and sys.platform.startswith("linux"):
        sysfs_esp, sysfs_pico = _find_ports_linux_sysfs()
        detected_esp = detected_esp or sysfs_esp
        detected_pico = detected_pico or sysfs_pico

    # Fallback heuristics if 2 serial ports exist but VIDs weren't matched
    if not detected_esp or not detected_pico:
        candidates = [d for d in all_devices if d not in (detected_esp, detected_pico)]
        if not detected_esp and candidates:
            # On Windows COM3 is traditional ESP port
            if "COM3" in candidates:
                detected_esp = "COM3"
                candidates.remove("COM3")
            elif "/dev/ttyACM1" in candidates:
                detected_esp = "/dev/ttyACM1"
                candidates.remove("/dev/ttyACM1")

        if not detected_pico and candidates:
            if "COM8" in candidates:
                detected_pico = "COM8"
                candidates.remove("COM8")
            elif "/dev/ttyACM0" in candidates:
                detected_pico = "/dev/ttyACM0"
                candidates.remove("/dev/ttyACM0")
            elif candidates:
                detected_pico = candidates[0]

    esp_port = esp_port or detected_esp
    pico_port = pico_port or detected_pico

    # Last resort defaults if devices haven't enumerated yet
    if not esp_port:
        esp_port = "COM3" if sys.platform == "win32" else "/dev/ttyACM1"
    if not pico_port:
        pico_port = "COM8" if sys.platform == "win32" else "/dev/ttyACM0"

    return esp_port, pico_port


if __name__ == "__main__":
    esp, pico = detect_ports()
    print("AI-Deck Port Discovery:")
    print(f"  ESP32-S3 Master Port : {esp}")
    print(f"  Pico 2 Co-Processor  : {pico}")
