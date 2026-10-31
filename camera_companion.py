"""
AI-Deck Mobile Camera Companion & Circuit Inspector Server
-----------------------------------------------------------
A zero-dependency local web app designed for a phone resting in the
AI-Deck console's 160mm phone slot or for desktop testing.

Features:
- "Snap & Inspect": Take a photo directly or pick from Meta View photo roll.
- Instant Gemini Vision circuit inspection (analyzes IC pins, polarities, shorts).
- Hands-free voice response streamed directly to your Ray-Ban Meta glasses.
- Real-time diagnostic cards on the mobile screen.
"""

import os
import sys
import json
import time
import socket
import cgi
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

# Set paths
HARNESS_DIR = Path(__file__).resolve().parent
CAPTURES_DIR = HARNESS_DIR / "captures"
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(HARNESS_DIR))

from tools.vision_tools import analyze_circuit_wiring

PORT = 8080

def get_local_ip():
    """Retrieve host machine's primary local IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def speak_feedback(text: str):
    """Voice feedback over default audio device (Ray-Ban Meta glasses)."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 175)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"[VOICE] Could not speak: {e}")

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>AI-Deck Camera Companion</title>
    <style>
        :root {
            --bg-dark: #0f172a;
            --card-bg: #1e293b;
            --accent-cyan: #38bdf8;
            --accent-green: #22c55e;
            --accent-purple: #c084fc;
            --accent-red: #ef4444;
            --text-light: #f8fafc;
            --text-dim: #94a3b8;
            --border: #334155;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg-dark);
            color: var(--text-light);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 1.25rem;
        }
        .header {
            text-align: center;
            margin-bottom: 1.5rem;
            width: 100%;
            max-width: 500px;
        }
        .badge {
            display: inline-block;
            background: rgba(56, 189, 248, 0.15);
            color: var(--accent-cyan);
            border: 1px solid rgba(56, 189, 248, 0.4);
            border-radius: 9999px;
            padding: 0.25rem 0.75rem;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }
        h1 { font-size: 1.5rem; font-weight: 700; }
        p.subtitle { color: var(--text-dim); font-size: 0.85rem; margin-top: 0.25rem; }
        .card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 1rem;
            padding: 1.25rem;
            width: 100%;
            max-width: 500px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
            margin-bottom: 1.25rem;
        }
        .snap-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.6rem;
            width: 100%;
            background: linear-gradient(135deg, #0284c7, #2563eb);
            color: white;
            font-size: 1.1rem;
            font-weight: 600;
            padding: 1rem;
            border-radius: 0.75rem;
            border: none;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(37, 99, 235, 0.4);
            transition: transform 0.1s ease, filter 0.2s ease;
        }
        .snap-btn:active { transform: scale(0.98); filter: brightness(0.9); }
        input[type="file"] { display: none; }
        .preview-box {
            margin-top: 1rem;
            width: 100%;
            min-height: 180px;
            max-height: 280px;
            border: 2px dashed var(--border);
            border-radius: 0.75rem;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            background: #090d16;
            position: relative;
        }
        .preview-box img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: none;
        }
        .preview-placeholder {
            color: var(--text-dim);
            font-size: 0.85rem;
            text-align: center;
            padding: 1rem;
        }
        .spinner {
            display: none;
            width: 2.5rem;
            height: 2.5rem;
            border: 4px solid rgba(56, 189, 248, 0.2);
            border-top-color: var(--accent-cyan);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .result-box {
            display: none;
            margin-top: 1rem;
            background: rgba(15, 23, 42, 0.6);
            border-radius: 0.75rem;
            padding: 1rem;
            border-left: 4px solid var(--accent-cyan);
        }
        .status-pill {
            display: inline-block;
            font-size: 0.75rem;
            font-weight: 700;
            padding: 0.2rem 0.6rem;
            border-radius: 0.35rem;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }
        .status-passed { background: rgba(34, 197, 94, 0.2); color: var(--accent-green); border: 1px solid var(--accent-green); }
        .status-issues { background: rgba(239, 68, 68, 0.2); color: var(--accent-red); border: 1px solid var(--accent-red); }
        .status-inconclusive { background: rgba(192, 132, 252, 0.2); color: var(--accent-purple); border: 1px solid var(--accent-purple); }
        .result-summary { font-size: 0.95rem; font-weight: 600; line-height: 1.4; margin-bottom: 0.6rem; }
        .result-text { font-size: 0.82rem; color: var(--text-dim); white-space: pre-wrap; line-height: 1.5; }
        .footer-note { text-align: center; color: var(--text-dim); font-size: 0.75rem; margin-top: auto; padding: 1rem 0; }
    </style>
</head>
<body>
    <div class="header">
        <div class="badge">AI-Deck Multimodal Vision</div>
        <h1>Circuit Inspector</h1>
        <p class="subtitle">Capture breadboard from Ray-Ban Meta or Phone</p>
    </div>

    <div class="card">
        <label for="cameraInput" class="snap-btn">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3"/></svg>
            Snap or Select Photo
        </label>
        <input type="file" id="cameraInput" accept="image/*" capture="environment">

        <div class="preview-box" id="previewBox">
            <div class="spinner" id="loadingSpinner"></div>
            <div class="preview-placeholder" id="previewPlaceholder">
                📷 Ready for circuit photo<br><span style="font-size:0.75rem; color:#64748b;">Tap button to snap directly or upload from Meta View</span>
            </div>
            <img id="previewImg" alt="Circuit photo">
        </div>

        <div class="result-box" id="resultBox">
            <div id="statusPill" class="status-pill">PASSED</div>
            <div id="resultSummary" class="result-summary">Inspection complete.</div>
            <div id="resultDetails" class="result-text"></div>
        </div>
    </div>

    <div class="footer-note">
        Ray-Ban Meta Audio Connected • Voice Diagnostics Active
    </div>

    <script>
        const input = document.getElementById('cameraInput');
        const previewImg = document.getElementById('previewImg');
        const previewPlaceholder = document.getElementById('previewPlaceholder');
        const spinner = document.getElementById('loadingSpinner');
        const resultBox = document.getElementById('resultBox');
        const statusPill = document.getElementById('statusPill');
        const resultSummary = document.getElementById('resultSummary');
        const resultDetails = document.getElementById('resultDetails');

        input.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            // Show preview
            const reader = new FileReader();
            reader.onload = (event) => {
                previewImg.src = event.target.result;
                previewImg.style.display = 'block';
                previewPlaceholder.style.display = 'none';
            };
            reader.readAsDataURL(file);

            // Upload and inspect
            spinner.style.display = 'block';
            resultBox.style.display = 'none';

            const formData = new FormData();
            formData.append('circuit_image', file);
            formData.append('target_description', 'ESP32-S3 DevKit on breadboard. Push button on GPIO 4 with pull-down resistor to GND. Onboard NeoPixel WS2812 on GPIO 38.');

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                spinner.style.display = 'none';
                resultBox.style.display = 'block';

                if (data.success) {
                    const text = data.analysis;
                    let status = 'PASSED';
                    if (text.includes('ISSUES_DETECTED') || text.includes('ISSUE')) status = 'ISSUES_DETECTED';
                    else if (text.includes('INCONCLUSIVE')) status = 'INCONCLUSIVE';

                    statusPill.textContent = status;
                    statusPill.className = 'status-pill ' + (status === 'PASSED' ? 'status-passed' : (status === 'ISSUES_DETECTED' ? 'status-issues' : 'status-inconclusive'));

                    let summary = 'Circuit analyzed by Gemini Vision.';
                    const match = text.match(/SUMMARY:\s*([^\n]+)/);
                    if (match && match[1]) summary = match[1].replace(/[*\-_]/g, '').trim();

                    resultSummary.textContent = summary;
                    resultDetails.textContent = text;
                } else {
                    statusPill.textContent = 'ERROR';
                    statusPill.className = 'status-pill status-issues';
                    resultSummary.textContent = 'Analysis could not be completed';
                    resultDetails.textContent = data.error || 'Unknown error occurred.';
                }
            } catch (err) {
                spinner.style.display = 'none';
                resultBox.style.display = 'block';
                statusPill.textContent = 'NETWORK ERROR';
                statusPill.className = 'status-pill status-issues';
                resultSummary.textContent = 'Failed to reach server';
                resultDetails.textContent = err.toString();
            }
        });
    </script>
</body>
</html>
"""

class CompanionHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Clean logging
        print(f"[HTTP] {self.command} {self.path} - {args[0]}")

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif self.path == "/latest.jpg":
            latest = CAPTURES_DIR / "latest.jpg"
            if latest.exists():
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.end_headers()
                self.wfile.write(latest.read_bytes())
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/upload":
            content_type = self.headers.get('Content-Type')
            if not content_type or 'multipart/form-data' not in content_type:
                self.send_response(400)
                self.end_headers()
                return

            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    'REQUEST_METHOD': 'POST',
                    'CONTENT_TYPE': self.headers['Content-Type'],
                }
            )

            file_item = form['circuit_image'] if 'circuit_image' in form else None
            desc = form.getvalue('target_description', 'ESP32-S3 circuit with push button on GPIO 4')

            if file_item and file_item.file:
                timestamp = int(time.time())
                save_path = CAPTURES_DIR / f"capture_{timestamp}.jpg"
                latest_path = CAPTURES_DIR / "latest.jpg"

                data = file_item.file.read()
                save_path.write_bytes(data)
                latest_path.write_bytes(data)

                print(f"[COMPANION] Received circuit photo ({len(data)} bytes). Running Gemini Vision...")
                analysis_res = analyze_circuit_wiring(str(latest_path), desc)

                # Voice feedback to glasses
                if analysis_res.get("success"):
                    analysis_text = analysis_res.get("analysis", "")
                    summary = ""
                    for l in analysis_text.splitlines():
                        if "SUMMARY:" in l:
                            summary = l.split("SUMMARY:", 1)[1].strip().lstrip("*- ")
                            break
                    if not summary:
                        summary = analysis_text[:200]
                    speak_feedback(f"Circuit photo received. {summary}")

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(analysis_res).encode("utf-8"))
            else:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "No image uploaded"}).encode("utf-8"))


def run_server():
    ip = get_local_ip()
    server = HTTPServer(('0.0.0.0', PORT), CompanionHandler)
    print("\n" + "=" * 62)
    print("   AI-DECK CAMERA COMPANION & CIRCUIT INSPECTOR SERVER        ")
    print("=" * 62)
    print(f"   Local Workstation URL : http://localhost:{PORT}")
    print(f"   Mobile / Phone URL    : http://{ip}:{PORT}")
    print("=" * 62)
    print("   Place your phone in the AI-Deck's 160mm phone slot or open")
    print("   the URL to snap photos or upload from Meta View.")
    print("   Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[COMPANION] Server stopped.")


if __name__ == "__main__":
    run_server()
