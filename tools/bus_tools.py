"""
AI-Deck Bus Tools & Co-Processor Bridge
Interfaces with the RP2040 / RP2350 (Pico 2) co-processor over USB-CDC serial
to control hardware sniffing, peripheral verification, and pin diagnostics.
"""

import time
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None


class PicoBusBridge:
    def __init__(self, port: Optional[str] = None, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.conn = None

    def auto_detect_pico_port(self) -> Optional[str]:
        try:
            from port_detect import detect_ports
            _, pico = detect_ports()
            return pico
        except Exception:
            pass

        if not serial:
            return None
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            hwid = (p.hwid or "").upper()
            desc = (p.description or "").upper()
            # Raspberry Pi Pico / RP2350 USB VID is 2E8A
            if (getattr(p, "vid", None) == 0x2E8A) or "2E8A" in hwid or "MICROPYTHON" in desc or "PICO" in desc:
                return p.device
        
        # Fallback: find any non-ESP32 port
        candidates = [p.device for p in ports if getattr(p, "vid", None) != 0x303A and "303A" not in (p.hwid or "")]
        if candidates:
            return candidates[0]
        return None

    def connect(self, port: Optional[str] = None):
        if not serial:
            raise RuntimeError("pyserial is not installed.")
        target_port = port or self.port or self.auto_detect_pico_port()
        if not target_port:
            raise RuntimeError("Pico 2 co-processor COM port not found.")
        self.port = target_port
        self.conn = serial.Serial(self.port, baudrate=self.baudrate, timeout=1.0)
        time.sleep(0.1)

    def close(self):
        if self.conn and self.conn.is_open:
            self.conn.close()
            self.conn = None

    def send_cmd(self, cmd_dict: Dict[str, Any], timeout_sec: float = 2.0) -> Dict[str, Any]:
        if not self.conn or not self.conn.is_open:
            self.connect()

        line_out = json.dumps(cmd_dict) + "\n"
        self.conn.reset_input_buffer()
        self.conn.write(line_out.encode("utf-8"))

        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            if self.conn.in_waiting > 0:
                raw_line = self.conn.readline().decode("utf-8", errors="ignore").strip()
                if raw_line.startswith("{") and raw_line.endswith("}"):
                    try:
                        return json.loads(raw_line)
                    except json.JSONDecodeError:
                        pass
            time.sleep(0.01)

        return {"error": "Timeout waiting for Pico response", "port": self.port}

    def get_bus_health(self) -> Dict[str, Any]:
        """Query voltage/pull-up health on I2C (GP16/17) and SPI (GP0-3) pins."""
        return self.send_cmd({"cmd": "HEALTH"})

    def ping(self) -> Dict[str, Any]:
        """Ping the Pico 2 co-processor."""
        return self.send_cmd({"cmd": "PING"})

    def capture_packets(self, duration_sec: float = 3.0, max_packets: int = 20) -> List[Dict[str, Any]]:
        """Collect captured I2C and SPI packets from the Pico co-processor."""
        if not self.conn or not self.conn.is_open:
            self.connect()

        packets = []
        start_time = time.time()
        while time.time() - start_time < duration_sec and len(packets) < max_packets:
            if self.conn.in_waiting > 0:
                raw_line = self.conn.readline().decode("utf-8", errors="ignore").strip()
                if raw_line.startswith("{") and raw_line.endswith("}"):
                    try:
                        parsed = json.loads(raw_line)
                        if "event" in parsed:
                            packets.append(parsed)
                    except json.JSONDecodeError:
                        pass
            time.sleep(0.01)

        return packets


# Singleton instance
pico_bridge = PicoBusBridge()


# --- FastMCP Tool Functions ---

def bus_ping(port: Optional[str] = None) -> Dict[str, Any]:
    """Ping the Pico 2 (RP2350) bus co-processor to verify USB-CDC connectivity."""
    try:
        bridge = PicoBusBridge(port=port)
        bridge.connect()
        res = bridge.ping()
        bridge.close()
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


def bus_check_health(port: Optional[str] = None) -> Dict[str, Any]:
    """
    Check the electrical state of I2C and SPI lines.
    Verifies if pull-up resistors are active on SDA (GP16) & SCL (GP17)
    and checks idle levels for SPI SCK (GP2), CS (GP1), MOSI (GP0).
    """
    try:
        bridge = PicoBusBridge(port=port)
        bridge.connect()
        res = bridge.get_bus_health()
        bridge.close()
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


def bus_sniff_packets(port: Optional[str] = None, duration_sec: float = 3.0, max_packets: int = 20) -> Dict[str, Any]:
    """
    Passively sniff I2C frames and SPI bursts transmitted by the target microcontroller (ESP32-S3).
    Decodes slave addresses, read/write flags, and SPI hex payloads.
    """
    try:
        bridge = PicoBusBridge(port=port)
        bridge.connect()
        packets = bridge.capture_packets(duration_sec=duration_sec, max_packets=max_packets)
        bridge.close()
        return {
            "success": True,
            "packets_captured": len(packets),
            "packets": packets
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
