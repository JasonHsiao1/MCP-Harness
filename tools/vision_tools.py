import os
import base64
import json
from pathlib import Path
from typing import Dict, Any, Optional
import requests
from PIL import Image


from config import get_gemini_api_key


def analyze_circuit_wiring(
    image_path: str,
    target_description: str,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze a photo of a breadboard/circuit (e.g., from Ray-Ban Meta glasses)
    to detect wiring errors, pin alignments, component polarities, and shorts.

    Args:
        image_path: Path to the JPG/PNG image file.
        target_description: What the circuit is supposed to be (e.g.,
          'ESP32-S3 DevKit with LED anode to GPIO 4 through 330 ohm resistor, cathode to GND').
        api_key: Optional Gemini API key. Defaults to GEMINI_API_KEY env var.
    """
    img_file = Path(image_path).resolve()
    if not img_file.exists():
        return {"success": False, "error": f"Image file not found: {img_file}"}

    key = api_key or get_gemini_api_key()
    if not key:
        return {
            "success": False,
            "error": "GEMINI_API_KEY is not set. Please export GEMINI_API_KEY to enable multimodal vision analysis.",
        }

    # Verify and encode image
    try:
        with Image.open(img_file) as img:
            format_name = img.format.lower() if img.format else "jpeg"
            mime_type = f"image/{format_name}"
        with open(img_file, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        return {"success": False, "error": f"Failed to read image file: {e}"}

    prompt = f"""
You are an expert embedded systems and electrical engineering lab assistant.
Inspect this photo of a circuit/breadboard setup captured from smart glasses.

Target Specification:
{target_description}

Please analyze the photo for:
1. IC / Board Orientation and Pin Alignment: Are jumpers plugged into the exact specified pins?
2. Breadboard Row Continuity: Are the component leads sharing the same terminal row as intended?
3. Component Polarity: Check LED cathode/anode orientation, diode cathode bands, polarized capacitors, or IC pin 1 dot/notch.
4. Resistor Values: If visible, decode resistor bands (e.g., brown-black-red = 1k, orange-orange-brown = 330).
5. Wiring Hazards: Check for loose wires, short circuits between 3V3/5V and GND, or bent pins.

Format your response as a structured analysis:
- STATUS: [PASSED | ISSUES_DETECTED | INCONCLUSIVE]
- SUMMARY: (1-2 sentence voice-friendly summary suitable for reading out loud over Ray-Ban Meta speakers)
- DETAILED_OBSERVATIONS: (Bullet points detailing what is visible)
- CORRECTIONS_NEEDED: (Specific step-by-step physical corrections for the user)
"""

    candidate_models = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.5-flash"]
    headers = {
        "x-goog-api-key": key,
        "Content-Type": "application/json",
    }
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_data,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
        },
    }

    last_err = None
    for model in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                text_response = data["candidates"][0]["content"]["parts"][0]["text"]
                return {
                    "success": True,
                    "image": str(img_file),
                    "model_used": model,
                    "analysis": text_response,
                }
            else:
                last_err = f"HTTP {response.status_code}"
        except Exception as e:
            last_err = str(e)

    return {"success": False, "error": f"Gemini Vision analysis unavailable: {last_err}"}
