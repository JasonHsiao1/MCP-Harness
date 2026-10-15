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

## 5. Ray-Ban Meta Bluetooth Voice Bridge (Hands-Free)

No Xcode, Mac, or iOS app required! You can pair your Ray-Ban Meta Gen 2 glasses directly to Windows as a Bluetooth audio headset:

1. **Pairing Mode**: Place glasses in the case, leave the lid open, hold the back button for 5 seconds until the LED pulses blue.
2. **Windows Bluetooth**: Open **Settings > Bluetooth & devices > Add device > Bluetooth** and select **Ray-Ban Meta**.
3. **Run Voice Bridge**:
   ```powershell
   cd harness
   .\.venv\Scripts\python.exe voice_bridge.py
   ```
   * `--test-tts`: Verify audio playback through your glasses speakers.
   * `--test-mic`: Verify voice capture from the glasses 5-mic array.
   * Once running, simply talk into your glasses: *"Flash the firmware"*, *"Read serial logs"*, or *"Compile project"*, and listen to the spoken responses in your ears!
