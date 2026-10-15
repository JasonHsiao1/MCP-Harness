import subprocess
import time
import os
import signal
from typing import Dict, Any, Optional
from pathlib import Path

from config import OPENOCD_EXE, OPENOCD_GDB_PORT, OPENOCD_TELNET_PORT


class OpenOCDProcessManager:
    _instance: Optional["OpenOCDProcessManager"] = None
    process: Optional[subprocess.Popen] = None
    config_desc: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "OpenOCDProcessManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start_openocd(
        self,
        target_board: str = "esp32s3-builtin",
        custom_args: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Start OpenOCD server in the background.
        
        target_board presets:
          - 'esp32s3-builtin': ESP32-S3 via native USB-JTAG
          - 'esp32c6-builtin': ESP32-C6 via native USB-JTAG
          - 'picoprobe-rp2040': Raspberry Pi Pico via CMSIS-DAP debugprobe
        """
        self.stop_openocd()

        if custom_args:
            args = custom_args
        elif target_board == "esp32s3-builtin":
            # Uses built-in esp_usb_jtag and esp32s3 target
            args = [
                str(OPENOCD_EXE),
                "-f", "interface/esp_usb_jtag.cfg",
                "-f", "target/esp32s3.cfg",
                "-c", f"gdb_port {OPENOCD_GDB_PORT}",
                "-c", f"telnet_port {OPENOCD_TELNET_PORT}",
            ]
        elif target_board == "esp32c6-builtin":
            args = [
                str(OPENOCD_EXE),
                "-f", "board/esp32c6-builtin.cfg",
                "-c", f"gdb_port {OPENOCD_GDB_PORT}",
                "-c", f"telnet_port {OPENOCD_TELNET_PORT}",
            ]
        elif target_board == "picoprobe-rp2040":
            args = [
                str(OPENOCD_EXE),
                "-f", "interface/cmsis-dap.cfg",
                "-f", "target/rp2040.cfg",
                "-c", f"gdb_port {OPENOCD_GDB_PORT}",
                "-c", f"telnet_port {OPENOCD_TELNET_PORT}",
            ]
        else:
            return {"success": False, "error": f"Unknown target board preset: {target_board}"}

        try:
            self.process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            # Give OpenOCD a brief moment to bind to socket
            time.sleep(1.0)
            if self.process.poll() is not None:
                # Process terminated prematurely
                stdout, stderr = self.process.communicate()
                return {
                    "success": False,
                    "error": "OpenOCD exited immediately",
                    "stdout": stdout,
                    "stderr": stderr,
                }

            self.config_desc = target_board
            return {
                "success": True,
                "pid": self.process.pid,
                "target": target_board,
                "gdb_port": OPENOCD_GDB_PORT,
                "telnet_port": OPENOCD_TELNET_PORT,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop_openocd(self) -> Dict[str, Any]:
        """Terminate the active OpenOCD process."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2.0)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None
            self.config_desc = None
            return {"success": True, "message": "OpenOCD terminated"}
        return {"success": True, "message": "No OpenOCD process running"}

    def get_status(self) -> Dict[str, Any]:
        """Check if OpenOCD process is currently alive."""
        if self.process:
            is_running = self.process.poll() is None
            return {
                "running": is_running,
                "pid": self.process.pid if is_running else None,
                "target": self.config_desc,
            }
        return {"running": False, "pid": None, "target": None}


openocd_manager = OpenOCDProcessManager.get_instance()
