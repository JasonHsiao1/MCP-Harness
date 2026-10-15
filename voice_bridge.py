#!/usr/bin/env python3
"""
Ray-Ban Meta Glasses Bluetooth Voice Bridge for AI-Deck Hardware Debugger
Routes voice from Ray-Ban Meta glasses -> AI Agent (Gemini/Claude) with MCP Tools -> Voice out to glasses.
"""

import os
import sys
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

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
from config import DEFAULT_PROJECT_DIR


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

    def execute_hardware_intent(self, text: str) -> str:
        """
        Process user speech intent and execute corresponding MCP hardware tools.
        Supports both direct intent matching and LLM-assisted execution.
        """
        low = text.lower()

        # 1. Flash / Upload firmware
        if any(w in low for w in ["flash", "upload", "program board", "burn"]):
            self.speak("Building and flashing firmware to the ESP32.")
            res = flash_firmware(str(DEFAULT_PROJECT_DIR), upload_port="COM3")
            if res["success"]:
                return "Firmware successfully flashed to the ESP32 on COM 3."
            else:
                err = res.get("stderr", "Unknown error")
                return f"Flash failed. {err[:80]}"

        # 2. Compile / Build only
        elif any(w in low for w in ["compile", "build", "make"]):
            self.speak("Compiling firmware project.")
            res = build_firmware(str(DEFAULT_PROJECT_DIR))
            if res["success"]:
                return "Firmware compiled successfully with zero errors."
            else:
                return "Compilation failed. Check build logs for details."

        # 3. Read Serial Telemetry
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

        # 4. Visualizer / "Show me"
        elif any(w in low for w in ["show me", "visualize", "diagram", "schematic", "circuit", "pinout", "display"]):
            import webbrowser
            viz_path = HARNESS_DIR / "visualizer" / "index.html"
            webbrowser.open(viz_path.as_uri())
            return "Opening the circuit diagram and interactive simulator on your screen now."

        # 5. Device Discovery
        elif any(w in low for w in ["device", "devices", "board", "connected", "port"]):
            devs = list_serial_devices()
            if devs and "port" in devs[0]:
                return f"Found {len(devs)} connected device: {devs[0].get('description', devs[0]['port'])} on port {devs[0]['port']}."
            return "No microcontroller devices were detected on USB."

        # 5. Fallback greeting / prompt
        else:
            return f"I heard you say: {text}. You can ask me to flash the firmware, compile, or read serial telemetry."


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
