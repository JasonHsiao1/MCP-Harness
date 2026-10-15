import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from pygdbmi.gdbcontroller import GdbController

from config import GDB_ESP32S3, GDB_ESP32C6


class GDBSessionManager:
    _instance: Optional["GDBSessionManager"] = None
    controller: Optional[GdbController] = None
    current_elf: Optional[str] = None
    is_connected: bool = False

    @classmethod
    def get_instance(cls) -> "GDBSessionManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start_session(
        self,
        elf_path: str,
        target_arch: str = "esp32s3",
        remote_host: str = "localhost",
        remote_port: int = 3333,
    ) -> Dict[str, Any]:
        """Start a GDB session, load ELF symbols, and connect to remote OpenOCD."""
        self.stop_session()

        elf_file = Path(elf_path).resolve()
        if not elf_file.exists():
            return {"success": False, "error": f"ELF file not found: {elf_file}"}

        # Select GDB binary
        if target_arch.lower() in ["esp32s3", "xtensa"]:
            gdb_path = str(GDB_ESP32S3)
        elif target_arch.lower() in ["esp32c6", "riscv", "riscv32"]:
            gdb_path = str(GDB_ESP32C6)
        else:
            gdb_path = "arm-none-eabi-gdb"

        try:
            self.controller = GdbController(gdb_path=gdb_path)
            # Load symbols
            load_resp = self.controller.write(f'-file-exec-and-symbols "{elf_file.as_posix()}"')
            # Connect to GDB server
            connect_resp = self.controller.write(f"target remote {remote_host}:{remote_port}")
            self.current_elf = str(elf_file)
            self.is_connected = True
            return {
                "success": True,
                "gdb_path": gdb_path,
                "elf": str(elf_file),
                "remote": f"{remote_host}:{remote_port}",
                "load_response": load_resp,
                "connect_response": connect_resp,
            }
        except Exception as e:
            self.stop_session()
            return {"success": False, "error": str(e)}

    def send_command(self, mi_command: str) -> Dict[str, Any]:
        """Send a raw GDB MI command or CLI command."""
        if not self.controller:
            return {"success": False, "error": "No active GDB session. Call gdb_start first."}
        try:
            responses = self.controller.write(mi_command)
            return {"success": True, "command": mi_command, "responses": responses}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def halt(self) -> Dict[str, Any]:
        """Interrupt/halt target execution."""
        return self.send_command("-exec-interrupt")

    def resume(self) -> Dict[str, Any]:
        """Resume target execution."""
        return self.send_command("-exec-continue")

    def step_line(self) -> Dict[str, Any]:
        """Step one line of source code (step over / next)."""
        return self.send_command("-exec-next")

    def step_into(self) -> Dict[str, Any]:
        """Step into a function call."""
        return self.send_command("-exec-step")

    def set_breakpoint(self, location: str) -> Dict[str, Any]:
        """Set a breakpoint at function name, symbol, or file:line."""
        return self.send_command(f"-break-insert {location}")

    def get_backtrace(self) -> Dict[str, Any]:
        """Get the current stack frame backtrace (vital for analyzing HardFault / Panic)."""
        return self.send_command("-stack-list-frames")

    def read_registers(self) -> Dict[str, Any]:
        """Read current register values."""
        # Query register names and values
        vals = self.send_command("-data-list-register-values x")
        return vals

    def read_memory(self, address: str, num_bytes: int = 16) -> Dict[str, Any]:
        """
        Read raw memory / MMIO registers.
        
        Args:
            address: Memory address in hex (e.g. '0x60004000') or symbol
            num_bytes: Number of bytes to read
        """
        # Form MI command: -data-read-memory-bytes <address> <count>
        return self.send_command(f"-data-read-memory-bytes {address} {num_bytes}")

    def stop_session(self) -> Dict[str, Any]:
        """Terminate active GDB session."""
        if self.controller:
            try:
                self.controller.exit()
            except Exception:
                pass
            self.controller = None
            self.is_connected = False
            self.current_elf = None
            return {"success": True, "message": "GDB session closed"}
        return {"success": True, "message": "No active session"}


# Singleton instance helper
session_manager = GDBSessionManager.get_instance()
