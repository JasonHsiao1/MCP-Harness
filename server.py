#!/usr/bin/env python3
"""
Embedded Hardware Debugger MCP Server
Provides LLM agents with tools to compile, flash, debug (OpenOCD/GDB-MI),
monitor telemetry, and inspect circuits multimodally for the AI-Deck workstation.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add harness directory to python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp.server.mcpserver import MCPServer
from config import DEFAULT_PROJECT_DIR
from tools.pio_tools import list_serial_devices, build_firmware, flash_firmware, clean_firmware
from tools.serial_tools import read_serial_logs
from tools.openocd_tools import openocd_manager
from tools.gdb_tools import session_manager
from tools.vision_tools import analyze_circuit_wiring

# Initialize MCP Server
server = MCPServer(
    name="embedded-debugger-mcp",
    version="1.0.0",
    description="Embedded Hardware & Firmware Debugger Harness for PlatformIO, GDB, OpenOCD, and Multimodal Vision",
)


# --- PlatformIO Build & Flash Tools ---

@server.tool()
def pio_list_devices() -> List[Dict[str, Any]]:
    """List all connected serial ports, USB JTAG interfaces, and microcontrollers."""
    return list_serial_devices()


@server.tool()
def pio_build_firmware(
    project_dir: str = str(DEFAULT_PROJECT_DIR),
    environment: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compile embedded firmware using PlatformIO CLI.
    
    Args:
        project_dir: Path to project directory containing platformio.ini.
        environment: Optional environment name (e.g., 'esp32-s3-devkitc-1').
    """
    return build_firmware(project_dir=project_dir, environment=environment)


@server.tool()
def pio_flash_firmware(
    project_dir: str = str(DEFAULT_PROJECT_DIR),
    environment: Optional[str] = None,
    upload_port: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Flash/upload compiled firmware to the target microcontroller.
    
    Args:
        project_dir: Path to project directory containing platformio.ini.
        environment: Optional environment name.
        upload_port: Optional serial port (e.g. 'COM4' or '/dev/ttyACM0').
    """
    return flash_firmware(
        project_dir=project_dir,
        environment=environment,
        upload_port=upload_port,
    )


@server.tool()
def pio_clean_firmware(project_dir: str = str(DEFAULT_PROJECT_DIR)) -> Dict[str, Any]:
    """Clean compilation artifacts for the given project."""
    return clean_firmware(project_dir=project_dir)


# --- Serial & Telemetry Tools ---

@server.tool()
def serial_read_logs(
    port: str,
    baudrate: int = 115200,
    timeout_sec: float = 3.0,
    max_lines: int = 50,
) -> Dict[str, Any]:
    """
    Read real-time UART / serial monitor output from target MCU.
    
    Args:
        port: COM port or device path (e.g., 'COM3').
        baudrate: Baud rate (default 115200).
        timeout_sec: Maximum time to listen (seconds).
        max_lines: Maximum number of log lines to return.
    """
    return read_serial_logs(
        port=port,
        baudrate=baudrate,
        timeout_sec=timeout_sec,
        max_lines=max_lines,
    )


# --- OpenOCD Server Controls ---

@server.tool()
def openocd_start_server(target_board: str = "esp32s3-builtin") -> Dict[str, Any]:
    """
    Start the OpenOCD JTAG/SWD server process.
    
    Args:
        target_board: Preset identifier ('esp32s3-builtin', 'esp32c6-builtin', or 'picoprobe-rp2040').
    """
    return openocd_manager.start_openocd(target_board=target_board)


@server.tool()
def openocd_stop_server() -> Dict[str, Any]:
    """Stop the background OpenOCD server process."""
    return openocd_manager.stop_openocd()


@server.tool()
def openocd_get_status() -> Dict[str, Any]:
    """Check if OpenOCD process is currently alive and listening."""
    return openocd_manager.get_status()


# --- GDB Machine Interface (GDB-MI) Tools ---

@server.tool()
def gdb_start_session(
    elf_path: str,
    target_arch: str = "esp32s3",
    remote_host: str = "localhost",
    remote_port: int = 3333,
) -> Dict[str, Any]:
    """
    Launch GDB, load ELF debug symbols, and connect to remote OpenOCD server.
    
    Args:
        elf_path: Absolute or relative path to firmware .elf file.
        target_arch: MCU architecture ('esp32s3', 'esp32c6', or 'arm').
        remote_host: GDB server host (default 'localhost').
        remote_port: GDB port (default 3333).
    """
    return session_manager.start_session(
        elf_path=elf_path,
        target_arch=target_arch,
        remote_host=remote_host,
        remote_port=remote_port,
    )


@server.tool()
def gdb_send_raw_command(mi_command: str) -> Dict[str, Any]:
    """
    Send a custom GDB Machine Interface (MI) or CLI command to the active GDB session.
    
    Args:
        mi_command: Command string (e.g. '-break-list', 'info registers', '-target-detach').
    """
    return session_manager.send_command(mi_command)


@server.tool()
def gdb_step_line() -> Dict[str, Any]:
    """Step one source line in the target firmware (step over / next)."""
    return session_manager.step_line()


@server.tool()
def gdb_step_into() -> Dict[str, Any]:
    """Step into the current function call."""
    return session_manager.step_into()


@server.tool()
def gdb_continue_execution() -> Dict[str, Any]:
    """Resume execution of the target MCU."""
    return session_manager.resume()


@server.tool()
def gdb_halt_execution() -> Dict[str, Any]:
    """Halt/interrupt running MCU target."""
    return session_manager.halt()


@server.tool()
def gdb_set_breakpoint(location: str) -> Dict[str, Any]:
    """
    Set a hardware breakpoint.
    
    Args:
        location: Function name (e.g. 'app_main', 'setup') or file:line (e.g. 'main.cpp:25').
    """
    return session_manager.set_breakpoint(location)


@server.tool()
def gdb_get_backtrace() -> Dict[str, Any]:
    """
    Retrieve current stack trace frames. Essential for analyzing HardFaults, Panics, and crashes.
    """
    return session_manager.get_backtrace()


@server.tool()
def gdb_read_registers() -> Dict[str, Any]:
    """Read CPU register values (PC, SP, A0-A15, etc.)."""
    return session_manager.read_registers()


@server.tool()
def gdb_read_mmio_memory(address: str, num_bytes: int = 16) -> Dict[str, Any]:
    """
    Read peripheral MMIO register or RAM bytes at the specified hexadecimal address.
    
    Args:
        address: Hex memory address (e.g. '0x60004000' for ESP32-S3 GPIO_OUT_REG).
        num_bytes: Number of bytes to read (default 16).
    """
    return session_manager.read_memory(address=address, num_bytes=num_bytes)


@server.tool()
def gdb_stop_session() -> Dict[str, Any]:
    """Close and terminate the current GDB debugging session."""
    return session_manager.stop_session()


# --- Multimodal Vision Circuit Inspection Tools ---

@server.tool()
def inspect_circuit_image(
    image_path: str,
    target_description: str,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Inspect a photo of breadboard or PCB circuit wiring (e.g. captured by Ray-Ban Meta glasses)
    using multimodal AI to detect miswiring, polarity errors, resistor values, and pin alignment.
    
    Args:
        image_path: Path to JPG/PNG photo.
        target_description: Expected wiring schematic / netlist description.
        api_key: Optional Gemini API Key (falls back to GEMINI_API_KEY env var).
    """
    return analyze_circuit_wiring(
        image_path=image_path,
        target_description=target_description,
        api_key=api_key,
    )


# --- MCP Resources & Context ---

@server.resource("resource://hardware/esp32s3-pinout")
def get_esp32s3_pinout() -> str:
    """Provides key pinout and MMIO register map for the ESP32-S3 DevKit."""
    return """
ESP32-S3 Pinout & MMIO Reference:
- Native USB-JTAG:
  * GPIO 19: USB D-
  * GPIO 20: USB D+
- Default UART0:
  * GPIO 43: TXD0
  * GPIO 44: RXD0
- Key MMIO Registers:
  * GPIO_OUT_REG: 0x60004004 (GPIO 0-31 output state)
  * GPIO_OUT_W1TS_REG: 0x60004008 (Atomic bit set)
  * GPIO_OUT_W1TC_REG: 0x6000400C (Atomic bit clear)
  * GPIO_ENABLE_REG: 0x60004020 (GPIO 0-31 direction / enable)
"""


@server.resource("resource://hardware/rp2040-pinout")
def get_rp2040_pinout() -> str:
    """Provides key pinout and MMIO register map for Raspberry Pi Pico (RP2040)."""
    return """
Raspberry Pi Pico (RP2040) SWD & MMIO Reference:
- SWD Header:
  * Pin 1: SWCLK (Clock)
  * Pin 2: GND
  * Pin 3: SWDIO (Data)
- Single-cycle IO (SIO) MMIO:
  * SIO_GPIO_OUT: 0xD0000010 (GPIO output value)
  * SIO_GPIO_OUT_SET: 0xD0000014 (Atomic bit set)
  * SIO_GPIO_OUT_CLR: 0xD0000018 (Atomic bit clear)
  * SIO_GPIO_OE: 0xD0000020 (Output enable)
"""


if __name__ == "__main__":
    # Run over standard input/output (stdio transport) for MCP clients
    server.run(transport="stdio")
