import time
from typing import Dict, Any, List
import serial


def read_serial_logs(port: str, baudrate: int = 115200, timeout_sec: float = 3.0, max_lines: int = 50) -> Dict[str, Any]:
    """
    Read serial/UART output from the target MCU.
    
    Args:
        port: COM port (e.g., 'COM3') or device path
        baudrate: UART baud rate (default 115200)
        timeout_sec: Duration to listen for logs (seconds)
        max_lines: Maximum number of lines to collect
    """
    lines: List[str] = []
    start_time = time.time()
    try:
        with serial.Serial(port=port, baudrate=baudrate, timeout=0.2) as ser:
            while (time.time() - start_time) < timeout_sec and len(lines) < max_lines:
                raw_line = ser.readline()
                if raw_line:
                    line_str = raw_line.decode("utf-8", errors="replace").strip()
                    if line_str:
                        lines.append(line_str)
                else:
                    time.sleep(0.05)
        return {
            "success": True,
            "port": port,
            "baudrate": baudrate,
            "lines_captured": len(lines),
            "logs": lines,
        }
    except Exception as e:
        return {
            "success": False,
            "port": port,
            "error": str(e),
            "logs": lines,
        }
