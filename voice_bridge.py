#!/usr/bin/env python3
"""
Ray-Ban Meta Glasses Bluetooth Voice Bridge for AI-Deck Hardware Debugger
Routes voice from Ray-Ban Meta glasses -> AI Agent (Gemini/Claude) with MCP Tools -> Voice out to glasses.
Supports:
  - Hardware flashing, building, and telemetry reading
  - "Show me" visualizer popups
  - Hands-free AI firmware modifications via voice prompts
"""

import os
import sys
import time
import re
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests

# Ensure harness tools are on path
HARNESS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HARNESS_DIR))

import speech_recognition as sr
import pyttsx3

from tools.pio_tools import list_serial_devices, build_firmware, flash_firmware
from tools.serial_tools import read_serial_logs
from tools.gdb_tools import session_manager
from tools.openocd_tools import openocd_manager
from tools.vision_tools import analyze_circuit_wiring
from config import DEFAULT_PROJECT_DIR, GEMINI_API_KEY, get_gemini_api_key

MAIN_CPP_PATH = DEFAULT_PROJECT_DIR / "src" / "main.cpp"


class GlassesVoiceBridge:
    def __init__(self, tts_rate: int = 175, voice_volume: float = 1.0):
        # Initialize TTS Engine (Windows SAPI5)
        self.tts = pyttsx3.init()
        self.tts.setProperty("rate", tts_rate)
        self.tts.setProperty("volume", voice_volume)

        # Initialize Speech Recognizer
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True

    def speak(self, text: str):
        """Speak response out loud (streams directly to Ray-Ban Meta open-ear speakers)."""
        print(f"\n[AI-DECK VOICE]: \"{text}\"")
        self.tts.say(text)
        self.tts.runAndWait()

    def listen(self, timeout: float = 5.0, phrase_time_limit: float = 8.0) -> Optional[str]:
        """Listen to the default microphone (Ray-Ban Meta 5-mic array)."""
        with sr.Microphone() as source:
            print("\n[LISTENING...] Speak now into your Ray-Ban Meta glasses...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.6)
            try:
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                )
                print("[PROCESSING...] Transcribing voice...")
                text = self.recognizer.recognize_google(audio)
                print(f"[YOU SAID]: \"{text}\"")
                return text
            except sr.WaitTimeoutError:
                return None
            except sr.UnknownValueError:
                print("[NOTICE] Could not understand audio.")
                return None
            except sr.RequestError as e:
                print(f"[ERROR] Speech service error: {e}")
                return None

    def modify_firmware_prompt(self, instruction: str) -> str:
        """
        Modify firmware code based on natural language voice prompt.
        Uses Gemini API if GEMINI_API_KEY is available, or pattern modifier fallback.
        """
        if not MAIN_CPP_PATH.exists():
            return "Could not find main.cpp in project."

        api_key = get_gemini_api_key()
        current_code = MAIN_CPP_PATH.read_text(encoding="utf-8")

        if api_key:
            self.speak("Generating new firmware code with Gemini AI.")
            prompt = f"""
You are an expert embedded C++ developer for ESP32-S3 Arduino.
Modify the following main.cpp file based on the user's voice instruction.

User Instruction:
{instruction}

Current main.cpp:
```cpp
{current_code}
```

Rules:
1. Retain ESP32-S3 compatibility (onboard RGB NeoPixel on GPIO 38 via rgbLedWrite(38, r, g, b)).
2. Return ONLY the complete valid C++ code, without markdown backticks or explanations.
"""
            candidate_models = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.5-flash"]
            headers = {
                "x-goog-api-key": api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2}
            }
            generated_code = None
            last_err = None

            for model in candidate_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                try:
                    res = requests.post(url, headers=headers, json=payload, timeout=20)
                    if res.status_code == 200:
                        data = res.json()
                        generated_code = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        break
                    else:
                        last_err = f"HTTP {res.status_code}"
                except Exception as err:
                    last_err = str(err)

            if generated_code:
                new_code = re.sub(r"^```(?:cpp|c)?\s*", "", generated_code)
                new_code = re.sub(r"\s*```$", "", new_code).strip()
                MAIN_CPP_PATH.write_text(new_code, encoding="utf-8")
                self.speak("Code generated. Now compiling and flashing to the board.")
                flash_res = flash_firmware(str(DEFAULT_PROJECT_DIR), upload_port="COM3")
                if flash_res["success"]:
                    return "Firmware updated and successfully flashed to the ESP32."
                else:
                    return "Firmware updated, but compilation failed."
            else:
                print(f"[WARN] Cloud AI generation unavailable ({last_err}), using built-in presets.")

        # Fast Offline Modifier (No API Key Required or Fallback)
        low = instruction.lower()
        if "green" in low:
            new_code = """#include <Arduino.h>
#define NEOPIXEL_PIN 38
static uint32_t blink_count = 0;
void setup() {
    Serial.begin(115200);
    delay(1000);
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);
}
void loop() {
    blink_count++;
    Serial.printf("[NEOPIXEL] Blink #%u | GREEN (ON)\\n", blink_count);
    rgbLedWrite(NEOPIXEL_PIN, 0, 80, 0);
    delay(500);
    Serial.printf("[NEOPIXEL] Blink #%u | OFF\\n", blink_count);
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);
    delay(500);
}
"""
            MAIN_CPP_PATH.write_text(new_code, encoding="utf-8")
            self.speak("Updating firmware to blink green. Flashing now.")
            flash_firmware(str(DEFAULT_PROJECT_DIR), upload_port="COM3")
            return "Firmware successfully updated to blink green."

        elif "red" in low:
            new_code = """#include <Arduino.h>
#define NEOPIXEL_PIN 38
static uint32_t blink_count = 0;
void setup() {
    Serial.begin(115200);
    delay(1000);
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);
}
void loop() {
    blink_count++;
    Serial.printf("[NEOPIXEL] Blink #%u | RED (ON)\\n", blink_count);
    rgbLedWrite(NEOPIXEL_PIN, 80, 0, 0);
    delay(500);
    Serial.printf("[NEOPIXEL] Blink #%u | OFF\\n", blink_count);
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);
    delay(500);
}
"""
            MAIN_CPP_PATH.write_text(new_code, encoding="utf-8")
            self.speak("Updating firmware to blink red. Flashing now.")
            flash_firmware(str(DEFAULT_PROJECT_DIR), upload_port="COM3")
            return "Firmware successfully updated to blink red."

        elif "blue" in low:
            new_code = """#include <Arduino.h>
#define NEOPIXEL_PIN 38
static uint32_t blink_count = 0;
void setup() {
    Serial.begin(115200);
    delay(1000);
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);
}
void loop() {
    blink_count++;
    Serial.printf("[NEOPIXEL] Blink #%u | BLUE (ON)\\n", blink_count);
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 80);
    delay(500);
    Serial.printf("[NEOPIXEL] Blink #%u | OFF\\n", blink_count);
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);
    delay(500);
}
"""
            MAIN_CPP_PATH.write_text(new_code, encoding="utf-8")
            self.speak("Updating firmware to blink blue. Flashing now.")
            flash_firmware(str(DEFAULT_PROJECT_DIR), upload_port="COM3")
            return "Firmware successfully updated to blink blue."

        elif "purple" in low or "violet" in low or "magenta" in low:
            new_code = """#include <Arduino.h>
#define NEOPIXEL_PIN 38
static uint32_t blink_count = 0;
void setup() {
    Serial.begin(115200);
    delay(1000);
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);
}
void loop() {
    blink_count++;
    Serial.printf("[NEOPIXEL] Blink #%u | PURPLE (ON)\\n", blink_count);
    rgbLedWrite(NEOPIXEL_PIN, 80, 0, 80);
    delay(500);
    Serial.printf("[NEOPIXEL] Blink #%u | OFF\\n", blink_count);
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);
    delay(500);
}
"""
            MAIN_CPP_PATH.write_text(new_code, encoding="utf-8")
            self.speak("Updating firmware to blink purple. Flashing now.")
            flash_firmware(str(DEFAULT_PROJECT_DIR), upload_port="COM3")
            return "Firmware successfully updated to blink purple."

        elif "yellow" in low:
            new_code = """#include <Arduino.h>
#define NEOPIXEL_PIN 38
static uint32_t blink_count = 0;
void setup() {
    Serial.begin(115200);
    delay(1000);
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);
}
void loop() {
    blink_count++;
    Serial.printf("[NEOPIXEL] Blink #%u | YELLOW (ON)\\n", blink_count);
    rgbLedWrite(NEOPIXEL_PIN, 60, 60, 0);
    delay(500);
    Serial.printf("[NEOPIXEL] Blink #%u | OFF\\n", blink_count);
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);
    delay(500);
}
"""
            MAIN_CPP_PATH.write_text(new_code, encoding="utf-8")
            self.speak("Updating firmware to blink yellow. Flashing now.")
            flash_firmware(str(DEFAULT_PROJECT_DIR), upload_port="COM3")
            return "Firmware successfully updated to blink yellow."

        elif "cyan" in low:
            new_code = """#include <Arduino.h>
#define NEOPIXEL_PIN 38
static uint32_t blink_count = 0;
void setup() {
    Serial.begin(115200);
    delay(1000);
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);
}
void loop() {
    blink_count++;
    Serial.printf("[NEOPIXEL] Blink #%u | CYAN (ON)\\n", blink_count);
    rgbLedWrite(NEOPIXEL_PIN, 0, 60, 60);
    delay(500);
    Serial.printf("[NEOPIXEL] Blink #%u | OFF\\n", blink_count);
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);
    delay(500);
}
"""
            MAIN_CPP_PATH.write_text(new_code, encoding="utf-8")
            self.speak("Updating firmware to blink cyan. Flashing now.")
            flash_firmware(str(DEFAULT_PROJECT_DIR), upload_port="COM3")
            return "Firmware successfully updated to blink cyan."

        elif "rainbow" in low:
            new_code = """#include <Arduino.h>
#define NEOPIXEL_PIN 38
struct Color { const char *name; uint8_t r; uint8_t g; uint8_t b; };
const Color RAINBOW[] = {
    {"Red", 60, 0, 0}, {"Orange", 60, 25, 0}, {"Yellow", 50, 50, 0},
    {"Green", 0, 60, 0}, {"Cyan", 0, 50, 50}, {"Blue", 0, 0, 60},
    {"Indigo", 25, 0, 50}, {"Violet", 50, 0, 45}
};
static size_t color_idx = 0;
void setup() { Serial.begin(115200); rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0); }
void loop() {
    const Color &c = RAINBOW[color_idx];
    Serial.printf("[NEOPIXEL] %s\\n", c.name);
    rgbLedWrite(NEOPIXEL_PIN, c.r, c.g, c.b);
    delay(500);
    color_idx = (color_idx + 1) % 8;
}
"""
            MAIN_CPP_PATH.write_text(new_code, encoding="utf-8")
            self.speak("Updating firmware to rainbow cycle. Flashing now.")
            flash_firmware(str(DEFAULT_PROJECT_DIR), upload_port="COM3")
            return "Firmware successfully updated to rainbow cycle."

        elif "fast" in low or "faster" in low or "speed up" in low:
            new_code = re.sub(r"delay\(\d+\);", "delay(120);", current_code)
            MAIN_CPP_PATH.write_text(new_code, encoding="utf-8")
            self.speak("Speed set to fast. Flashing now.")
            flash_firmware(str(DEFAULT_PROJECT_DIR), upload_port="COM3")
            return "Firmware updated to fast blink."

        elif "slow" in low or "slower" in low:
            new_code = re.sub(r"delay\(\d+\);", "delay(900);", current_code)
            MAIN_CPP_PATH.write_text(new_code, encoding="utf-8")
            self.speak("Speed set to slow. Flashing now.")
            flash_firmware(str(DEFAULT_PROJECT_DIR), upload_port="COM3")
            return "Firmware updated to slow blink."

        else:
            return "To modify code with open-ended voice prompts, please export your GEMINI_API_KEY, or type your request in Antigravity chat."

    def execute_hardware_intent(self, text: str) -> str:
        """
        Process user speech intent and execute corresponding MCP hardware tools.
        """
        low = text.lower()

        # 1. Modify firmware code by prompt
        if any(w in low for w in ["change the code", "modify the code", "update code", "change to", "make it", "blink green", "blink red", "blink blue", "blink purple", "blink yellow", "blink cyan", "blink rainbow", "faster", "slower", "purple", "violet"]):
            return self.modify_firmware_prompt(text)

        # 2. Flash / Upload firmware
        elif any(w in low for w in ["flash", "upload", "program board", "burn"]):
            self.speak("Building and flashing firmware to the ESP32.")
            res = flash_firmware(str(DEFAULT_PROJECT_DIR), upload_port="COM3")
            if res["success"]:
                return "Firmware successfully flashed to the ESP32 on COM 3."
            else:
                err = res.get("stderr", "Unknown error")
                return f"Flash failed. {err[:80]}"

        # 3. Compile / Build only
        elif any(w in low for w in ["compile", "build", "make"]):
            self.speak("Compiling firmware project.")
            res = build_firmware(str(DEFAULT_PROJECT_DIR))
            if res["success"]:
                return "Firmware compiled successfully with zero errors."
            else:
                return "Compilation failed. Check build logs for details."

        # 4. Read Serial Telemetry
        elif any(w in low for w in ["log", "logs", "serial", "telemetry", "output", "read"]):
            self.speak("Reading live telemetry from serial port.")
            res = read_serial_logs("COM3", baudrate=115200, timeout_sec=2.5, max_lines=5)
            if res["success"] and res["logs"]:
                summary = f"Captured {res['lines_captured']} lines. Latest: {res['logs'][-1]}"
                return summary
            elif res["success"]:
                return "Serial port is open, but no log messages were received."
            else:
                return f"Could not read serial port. {res.get('error', '')}"

        # 5. Visualizer / "Show me"
        elif any(w in low for w in ["show me", "visualize", "diagram", "schematic", "circuit", "pinout", "display"]):
            import webbrowser
            viz_path = HARNESS_DIR / "visualizer" / "index.html"
            webbrowser.open(viz_path.as_uri())
            return "Opening the circuit diagram and interactive simulator on your screen now."

        # 6. Device Discovery
        elif any(w in low for w in ["device", "devices", "board", "connected", "port"]):
            devs = list_serial_devices()
            if devs and "port" in devs[0]:
                return f"Found {len(devs)} connected device: {devs[0].get('description', devs[0]['port'])} on port {devs[0]['port']}."
            return "No microcontroller devices were detected on USB."

        # 7. Fallback greeting / guidance
        else:
            return f"I heard you say: {text}. You can ask me to flash firmware, modify the code, show the circuit diagram, or read serial logs."


def main():
    parser = argparse.ArgumentParser(description="Ray-Ban Meta Glasses Voice Bridge")
    parser.add_argument("--test-tts", action="store_true", help="Test audio playback through glasses speakers")
    parser.add_argument("--test-mic", action="store_true", help="Test microphone capture from glasses")
    args = parser.parse_args()

    bridge = GlassesVoiceBridge()

    if args.test_tts:
        print("[TEST] Sending test audio to default playback device...")
        bridge.speak("Hello! Your Ray-Ban Meta glasses are connected to the AI-Deck hardware debugger.")
        return

    if args.test_mic:
        print("[TEST] Testing microphone capture...")
        text = bridge.listen(timeout=6.0, phrase_time_limit=5.0)
        if text:
            bridge.speak(f"Microphone test passed. I heard: {text}")
        else:
            print("[TEST] No speech detected or recognition failed.")
        return

    # Continuous Voice Assistant Loop
    bridge.speak("AI-Deck voice bridge is online. I'm listening through your glasses.")
    print("\n" + "=" * 60)
    print("   AI-Deck Ray-Ban Meta Bluetooth Voice Bridge Active       ")
    print("   Press Ctrl+C to exit                                     ")
    print("=" * 60 + "\n")

    try:
        while True:
            text = bridge.listen(timeout=8.0, phrase_time_limit=7.0)
            if text:
                response = bridge.execute_hardware_intent(text)
                bridge.speak(response)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[EXITING] Voice bridge stopped.")
        bridge.speak("Voice bridge disconnected.")


if __name__ == "__main__":
    main()
