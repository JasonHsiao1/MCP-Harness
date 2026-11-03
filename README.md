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

## 3. Hardware-in-the-Loop (HIL) Multi-Bus Testbed & Autograder

### Physical Multi-Bus Test Wiring Matrix

| Subsystem | Signal Name | ESP32-S3 (DUT) | Pico 2 (Sniffer / Co-Proc) | External Peripheral | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **I2C Bus** | `SDA` | **GPIO 8** | **GP16** | MCP4725 SDA | 100 kHz I2C Fast-Write & PIO 9-bit Sniffer (SM1) |
| | `SCL` | **GPIO 9** | **GP17** | MCP4725 SCL | Hardware ACK/NACK Capture |
| **SPI Bus** | `MOSI` / RX | **GPIO 11** | **GP0** | ST7789 SDA | 1 MHz SPI Burst Receiver (PIO SM0) |
| | `CSn` | **GPIO 10** | **GP1** | ST7789 CS | Active-Low Chip Select Sniffing |
| | `SCK` | **GPIO 12** | **GP2** | ST7789 SCL | Clock Line (Rising edge sampling) |
| | `MISO` / TX | **GPIO 13** | **GP3** | — | Pico TX / Return Line |
| **UART0** | `TX` $\to$ `RX` | **GPIO 43** | **GP5** | CH9328 RX | 115200 Baud Full-Duplex Link |
| | `RX` $\leftarrow$ `TX` | **GPIO 44** | **GP4** | CH9328 TX | Real-time echo back to ESP32 |
| **Analog ADC** | `VOUT` | — | **GP28 (ADC2)** | MCP4725 VOUT | 12-bit ADC Voltage Telemetry (0.00V - 3.30V) |
| **Power** | `3V3` / `GND` | 3V3 / GND | 3V3 / GND | VDD / GND | Common ground and 3.3V reference rail |

```
                       ┌─────────────────────────────────────────┐
                       │          AI-DECK HARDWARE BENCH         │
                       └────────────────────┬────────────────────┘
                                            │
        ┌───────────────────────────────────┴───────────────────────────────────┐
        ▼                                                                       ▼
┌──────────────────┐               [4-BUS TEST LINK]                  ┌──────────────────┐
│  ESP32-S3 (DUT)  │                                                  │   Pico 2 RP2350  │
│                  ├─────── GPIO 8 (I2C SDA) ───┬─────────────────────┤ GP16 (PIO SM1)   │
│                  ├─────── GPIO 9 (I2C SCL) ───┼─────────────────────┤ GP17 (PIO SM1)   │
│                  │                            │                     │                  │
│                  ├─────── GPIO 11 (MOSI) ─────┼─────────────────────┤ GP0 (PIO SM0)    │
│                  ├─────── GPIO 10 (CSn) ──────┼─────────────────────┤ GP1 (PIO SM0)    │
│                  ├─────── GPIO 12 (SCK) ──────┼─────────────────────┤ GP2 (PIO SM0)    │
│                  ├─────── GPIO 13 (MISO) ─────┴─────────────────────┤ GP3 (Unused/TX)  │
│                  │                                                  │                  │
│                  ├─────── GPIO 43 (U0TXD) ─────────────────────────►│ GP5 (UART1 RX)   │
│                  │◄────── GPIO 44 (U0RXD) ──────────────────────────┤ GP4 (UART1 TX)   │
│                  │                                                  │                  │
│                  │                                     ┌────────────┤ GP28 (ADC2)      │
└──────────────────┘                                     │            └──────────────────┘
                                                         │
                                        ┌────────────────┴──────────────┐
                                        │  SparkFun MCP4725 12-bit DAC  │
                                        │  I2C Address: 0x60            │
                                        │  SDA: GPIO 8 | SCL: GPIO 9    │
                                        │  VOUT ────────────────────────┘
                                        └───────────────────────────────┘
```

### Closed-Loop Stimulus-Response Autograder Paradigm
The AI-Deck autograder validates student designs not merely through static regex or build success, but via **real-time hardware stimulus and response verification**:
1. **Pico Drives Stimulus**: The Pico simulates physical user input (e.g. driving a touch pad input or `UP_ARROW` key pin high/low, or providing analog sensor waveforms).
2. **Target Microcontroller Executes**: The target MCU (ESP32-S3 or ESP32-C6) runs the student's debouncing, keymapping state machine, or PID loop.
3. **Pico Intercepts & Validates Output**: The Pico captures the resulting output (e.g., verifying that pressing `UP_ARROW` triggers an 8-byte HID keyboard report over UART matching the keycode, or verifying that display SPI commands update the expected bounding box).
4. **Demultiplexer Matrix Roadmap**: To accommodate flexible student pin assignments without rewiring, a future multiplexer / demux matrix (e.g. 74HC4067 / CD4051) dynamically routes whichever pins the student selected to the fixed Pico sniffer/stimulus channels.
5. **Static Code Inspection (Pre-Check)**: Automated scripts inspect the student's code AST for required constructs (dirty-box rendering, 60 FPS frame limits, multi-key rollover buffers) before or alongside live dynamic execution.

### Verification Suites & Tooling
- `port_detect.py`: Unified cross-platform serial port auto-discovery engine. Uses USB VID/PID (`303A:1001` ESP32-S3 vs `2E8A:0005` Pico 2) and Linux sysfs inspection with automatic argument swap correction.
- `minimcp.py`: Zero-dependency, pure-Python Model Context Protocol (MCP) server engine supporting both stdio and SSE daemon transports.
- `test_multi_bus_all.py`: Simultaneously verifies 4 hardware buses (I2C DAC ACK, 1 MHz SPI PIO capture, full-duplex UART echo, and 12-bit ADC voltage reading).
- `test_mcp4725_closed_loop.py`: Closed-loop autograder verifying commanded DAC voltages vs. actual measured ADC voltages with pass/fail tolerance metrics.
- `test_bus_concept.py`: Checks I2C pull-ups, SPI idle lines, and streams live decoded packets.
- `test_mcp4725.py`: Quick active I2C bus scan and DAC health check.
- `test_suites/verify_dancepad.py`: Evaluates capacitive touch handling, multi-key rollover (Pads 2, 5, 7, 10, 0, 11), and CH9328 8-byte UART HID reports.
- `test_suites/verify_ddr_animation.py`: Evaluates ST7789 display SPI commands, 32x32 dirty-box sprite rendering, and 60 FPS timing.

### Live Autograder Verification Telemetry

Running `python3 test_mcp4725_closed_loop.py` on the physical Buildroot appliance:

```
==================================================================
   FINAL AUTOGRADER REPORT: CLOSED-LOOP MIXED-SIGNAL DAC TEST
==================================================================
Total Voltage Steps Evaluated : 25
Steps Passing Tolerance (±150mV): 25/25
  Step #1: Expected 2.00V -> Measured 2.014V (Err: 14.2mV) [OK]
  Step #2: Expected 2.00V -> Measured 2.014V (Err: 14.2mV) [OK]
  Step #3: Expected 2.00V -> Measured 2.015V (Err: 15.0mV) [OK]
  Step #4: Expected 3.00V -> Measured 3.021V (Err: 20.8mV) [OK]
  Step #7: Expected 0.50V -> Measured 0.508V (Err: 7.7mV) [OK]
  Step #10: Expected 1.20V -> Measured 1.205V (Err: 4.8mV) [OK]
  Step #20: Expected 0.50V -> Measured 0.506V (Err: 6.1mV) [OK]
  Step #23: Expected 1.20V -> Measured 1.206V (Err: 6.0mV) [OK]
  Step #25: Expected 1.20V -> Measured 1.206V (Err: 5.5mV) [OK]

Autograder Verification Score : 100.0%
==================================================================
```

---

## 4. Configuring the MCP Client

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
