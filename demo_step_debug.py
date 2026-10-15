#!/usr/bin/env python3
"""
Step-by-step GDB Debugging Demonstration via MCP Harness.
Demonstrates:
  1. OpenOCD server launch (USB-JTAG)
  2. GDB-MI session initialization & symbol loading
  3. Setting a hardware breakpoint on setup()
  4. Line-by-line stepping through source code
  5. Reading CPU registers (PC, SP) and GPIO MMIO memory
"""

import sys
import time
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HARNESS_DIR))

from tools.openocd_tools import openocd_manager
from tools.gdb_tools import session_manager
from config import DEFAULT_PROJECT_DIR

def run_step_debugging():
    elf_path = DEFAULT_PROJECT_DIR / ".pio" / "build" / "esp32-s3-devkitc-1" / "firmware.elf"
    
    if not elf_path.exists():
        print(f"[ERROR] Firmware ELF not found at {elf_path}. Please build first.")
        return False

    print("========================================================")
    print("   AI-Deck ESP32-S3 Step-by-Step GDB Hardware Debugger   ")
    print("========================================================")
    
    # Step 1: Start OpenOCD
    print("\n[STEP 1] Starting OpenOCD server...")
    openocd_res = openocd_manager.start_openocd(target_board="esp32s3-builtin")
    if not openocd_res.get("success"):
        print(f"[ERROR] Could not start OpenOCD: {openocd_res.get('error')}")
        print("Tip: If libusb returned NOT_FOUND, plug the ESP32-S3 into a different USB port.")
        return False
    print(f"-> OpenOCD running (PID {openocd_res['pid']}) on GDB port {openocd_res['gdb_port']}")

    try:
        # Step 2: Connect GDB
        print("\n[STEP 2] Launching GDB and connecting to OpenOCD...")
        gdb_res = session_manager.start_session(
            elf_path=str(elf_path),
            target_arch="esp32s3",
            remote_host="localhost",
            remote_port=3333
        )
        if not gdb_res.get("success"):
            print(f"[ERROR] GDB connection failed: {gdb_res.get('error')}")
            return False
        print("-> GDB connected and ELF symbols loaded.")

        # Step 3: Halt target and set breakpoint
        print("\n[STEP 3] Halting target and setting breakpoint at 'setup'...")
        session_manager.halt()
        time.sleep(0.5)
        bp_res = session_manager.set_breakpoint("setup")
        print("-> Breakpoint set:", bp_res)

        # Step 4: Resume execution to hit breakpoint
        print("\n[STEP 4] Resuming execution towards breakpoint...")
        session_manager.resume()
        time.sleep(1.0)

        # Step 5: Read CPU Registers
        print("\n[STEP 5] Inspecting CPU registers...")
        regs = session_manager.read_registers()
        print("-> Registers captured:", str(regs)[:300], "...")

        # Step 6: Step line-by-line
        print("\n[STEP 6] Stepping through code line-by-line...")
        for i in range(3):
            step_res = session_manager.step_line()
            print(f"-> Step {i+1} executed: {step_res.get('command')}")
            time.sleep(0.5)

        # Step 7: Read MMIO Register (GPIO_OUT_REG = 0x60004004)
        print("\n[STEP 7] Reading ESP32-S3 GPIO_OUT_REG (0x60004004)...")
        mmio_res = session_manager.read_memory("0x60004004", 16)
        print("-> MMIO Read result:", mmio_res)

        # Step 8: Resume execution
        print("\n[STEP 8] Resuming normal execution...")
        session_manager.resume()
        print("\n[COMPLETE] Step-by-step debugging verification finished!")
        return True

    finally:
        session_manager.stop_session()
        openocd_manager.stop_openocd()
        print("[CLEANUP] OpenOCD and GDB sessions closed.")

if __name__ == "__main__":
    run_step_debugging()
