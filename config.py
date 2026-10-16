import os
import sys
from pathlib import Path

# Base directories
HARNESS_DIR = Path(__file__).resolve().parent
REPO_DIR = HARNESS_DIR.parent
PLATFORMIO_HOME = Path(os.environ.get("PLATFORMIO_HOME", Path.home() / ".platformio"))

# PlatformIO core and python binaries
PIO_EXE = PLATFORMIO_HOME / "penv" / "Scripts" / "pio.exe"
if not PIO_EXE.exists():
    PIO_EXE = Path("pio")  # Fallback to PATH

# GDB Toolchains (ESP32-S3 and ESP32-C6)
GDB_ESP32S3 = PLATFORMIO_HOME / "packages" / "tool-xtensa-esp-elf-gdb" / "bin" / "xtensa-esp32s3-elf-gdb.exe"
GDB_ESP32C6 = PLATFORMIO_HOME / "packages" / "tool-riscv32-esp-elf-gdb" / "bin" / "riscv32-esp-elf-gdb.exe"

# OpenOCD search path (if installed by PlatformIO tool-openocd-esp32 or system)
OPENOCD_CANDIDATES = list((PLATFORMIO_HOME / "packages").glob("tool-openocd*/**/openocd.exe"))
OPENOCD_EXE = OPENOCD_CANDIDATES[0] if OPENOCD_CANDIDATES else Path("openocd")

# Default OpenOCD port settings
OPENOCD_GDB_PORT = 3333
OPENOCD_TELNET_PORT = 4444

# Default target workspace
DEFAULT_PROJECT_DIR = HARNESS_DIR / "target_firmware" / "esp32s3_blink_fault"

def get_gemini_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key

    # Check .env files
    for env_path in [HARNESS_DIR / ".env", REPO_DIR / ".env"]:
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() == "GEMINI_API_KEY":
                            val = v.strip().strip('"').strip("'")
                            if val:
                                os.environ["GEMINI_API_KEY"] = val
                                return val
            except Exception:
                pass

    # Check Windows Registry (setx)
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as reg:
                val, _ = winreg.QueryValueEx(reg, "GEMINI_API_KEY")
                if val:
                    os.environ["GEMINI_API_KEY"] = val
                    return val
        except Exception:
            pass

    return ""

GEMINI_API_KEY = get_gemini_api_key()
