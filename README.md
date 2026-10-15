# AI-Deck Embedded Hardware Debugger MCP Server

A specialized **Model Context Protocol (MCP)** harness enabling multimodal AI agents to interact directly with physical embedded hardware, JTAG/SWD probes, GDB machine interfaces, and smart glass audio/camera streams.

---

## 1. Directory Structure

```
AI-Deck/
├── CAD/                           # OpenSCAD 3D console models, STLs, and component specs
│   ├── ai_deck.scad
│   ├── ai_deck_top_plate.stl
│   └── available-parts/
└── harness/                       # Hardware Debugger MCP Harness
    ├── config.py                  # Auto-detection of PlatformIO, GDB, and OpenOCD
    ├── server.py                  # FastMCP / MCPServer entry point (20 tools + resources)
    ├── requirements.txt           # Python dependencies
    ├── .venv/                     # Isolated virtual environment
    ├── tools/
    │   ├── pio_tools.py           # Build, flash, clean, and device discovery via PlatformIO
    │   ├── gdb_tools.py           # GDB-MI interactive debugging (breakpoints, stepping, MMIO, backtrace)
    │   ├── openocd_tools.py       # OpenOCD process management (esp_usb_jtag, cmsis-dap)
    │   ├── serial_tools.py        # Real-time UART telemetry capture
    │   └── vision_tools.py        # Multimodal circuit & breadboard inspection via Gemini Vision
    └── target_firmware/
        └── esp32s3_blink_fault/   # MVP target firmware with LED blink and intentional MMIO fault trap
```

---

## 2. Tools Exposed by the MCP Server

### A. PlatformIO Compilation & Flashing
- `pio_list_devices()`: Discover connected COM ports and USB-JTAG interfaces.
- `pio_build_firmware(project_dir, environment)`: Compiles firmware via PlatformIO CLI.
- `pio_flash_firmware(project_dir, environment, upload_port)`: Flashes binary to the target MCU.
- `pio_clean_firmware(project_dir)`: Cleans build artifacts.

### B. Serial / Telemetry
- `serial_read_logs(port, baudrate, timeout_sec, max_lines)`: Captures `printf` logs and runtime output.

### C. OpenOCD Server Controls
- `openocd_start_server(target_board)`: Starts OpenOCD daemon for `esp32s3-builtin`, `esp32c6-builtin`, or `picoprobe-rp2040`.
- `openocd_stop_server()`: Gracefully halts OpenOCD.
- `openocd_get_status()`: Queries PID and listening state.

### D. GDB-MI Interactive Debugging (`pygdbmi`)
- `gdb_start_session(elf_path, target_arch, remote_host, remote_port)`: Launches GDB, loads ELF symbols, and connects to OpenOCD (`localhost:3333`).
- `gdb_set_breakpoint(location)`: Sets hardware breakpoints at functions or `file:line`.
- `gdb_step_line()`: Steps over one line of source code (`-exec-next`).
- `gdb_step_into()`: Steps into function (`-exec-step`).
- `gdb_continue_execution()`: Resumes execution (`-exec-continue`).
- `gdb_halt_execution()`: Interrupts target (`-exec-interrupt`).
- `gdb_read_registers()`: Reads CPU register state (`PC`, `SP`, general purpose registers).
- `gdb_read_mmio_memory(address, num_bytes)`: Reads MMIO peripheral registers (e.g., `0x60004004` GPIO_OUT_REG).
- `gdb_get_backtrace()`: Inspects stack frames to pinpoint `HardFault`, `LoadProhibited`, or panic locations.
- `gdb_send_raw_command(mi_command)`: Passes custom GDB MI or CLI commands.
- `gdb_stop_session()`: Disconnects and terminates GDB.

### E. Multimodal Vision Inspection
- `inspect_circuit_image(image_path, target_description)`: Sends a photo captured from the Ray-Ban Meta glasses to Gemini Vision to verify IC orientation, breadboard row continuity, resistor bands, and LED polarity.

---

## 3. Configuring the MCP Client

To connect Antigravity, Claude Desktop, or VS Code to this MCP server:

### In Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "embedded-debugger": {
      "command": "c:\\jason\\GeorgiaTech\\Forces\\Designs\\AI-Deck\\harness\\.venv\\Scripts\\python.exe",
      "args": [
        "c:\\jason\\GeorgiaTech\\Forces\\Designs\\AI-Deck\\harness\\server.py"
      ],
      "env": {
        "GEMINI_API_KEY": "YOUR_GEMINI_API_KEY"
      }
    }
  }
}
```

---

## 4. Hardware Hookup Guide

### Option 1: ESP32-S3 Native USB (Self-Debugged)
- Connect the **USB** port (native USB, not UART) of the ESP32-S3 DevKit to your PC.
- OpenOCD connects directly to ESP32-S3's internal `esp_usb_jtag`. No external probe needed.

### Option 2: Raspberry Pi Pico Debug Probe (`debugprobe`)
- Flash `debugprobe.uf2` onto a Raspberry Pi Pico.
- Connect Pico SWD pins to the target board on the AI-Deck's 2x8 debug header:
  - `Pin 1 (SWCLK)` -> Target SWCLK
  - `Pin 2 (GND)`   -> Target GND
  - `Pin 3 (SWDIO)` -> Target SWDIO
  - `UART TX/RX`    -> Target RX/TX
