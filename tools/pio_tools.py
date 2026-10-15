import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys

from config import PIO_EXE


def list_serial_devices() -> List[Dict[str, Any]]:
    """List all connected serial/USB devices via PlatformIO."""
    cmd = [str(PIO_EXE), "device", "list", "--json-output"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
    except Exception as e:
        # Fallback to standard CLI output if JSON parsing fails
        try:
            res = subprocess.run([str(PIO_EXE), "device", "list"], capture_output=True, text=True)
            return [{"raw_output": res.stdout, "error": str(e)}]
        except Exception as inner_e:
            return [{"error": f"Failed to execute pio device list: {inner_e}"}]


def build_firmware(project_dir: str, environment: Optional[str] = None) -> Dict[str, Any]:
    """
    Compile firmware for the specified PlatformIO project.
    
    Args:
        project_dir: Path to directory containing platformio.ini
        environment: Optional specific environment name (e.g., 'esp32-s3-devkitc-1')
    """
    p_path = Path(project_dir).resolve()
    if not (p_path / "platformio.ini").exists():
        return {"success": False, "error": f"platformio.ini not found in {p_path}"}

    cmd = [str(PIO_EXE), "run", "-d", str(p_path)]
    if environment:
        cmd.extend(["-e", environment])

    res = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "success": res.returncode == 0,
        "returncode": res.returncode,
        "stdout": res.stdout,
        "stderr": res.stderr,
    }


def flash_firmware(project_dir: str, environment: Optional[str] = None, upload_port: Optional[str] = None) -> Dict[str, Any]:
    """
    Upload compiled firmware to target MCU.
    
    Args:
        project_dir: Path to directory containing platformio.ini
        environment: Optional specific environment name
        upload_port: Optional explicit serial port (e.g. 'COM4' or '/dev/ttyACM0')
    """
    p_path = Path(project_dir).resolve()
    if not (p_path / "platformio.ini").exists():
        return {"success": False, "error": f"platformio.ini not found in {p_path}"}

    cmd = [str(PIO_EXE), "run", "-d", str(p_path), "-t", "upload"]
    if environment:
        cmd.extend(["-e", environment])
    if upload_port:
        cmd.extend(["--upload-port", upload_port])

    res = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "success": res.returncode == 0,
        "returncode": res.returncode,
        "stdout": res.stdout,
        "stderr": res.stderr,
    }


def clean_firmware(project_dir: str) -> Dict[str, Any]:
    """Clean PlatformIO build artifacts."""
    p_path = Path(project_dir).resolve()
    cmd = [str(PIO_EXE), "run", "-d", str(p_path), "-t", "clean"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "success": res.returncode == 0,
        "stdout": res.stdout,
        "stderr": res.stderr,
    }
