#!/usr/bin/env python3
"""
AI-Deck MiniMCP: Lightweight, Zero-Dependency Model Context Protocol (MCP) Server.
Designed for embedded appliances, Buildroot Linux, and resource-constrained environments.
Supports:
  - JSON-RPC 2.0 stdio transport (default)
  - HTTP / Server-Sent Events (SSE) transport for background systemd daemon operation
"""

import sys
import json
import inspect
from typing import Dict, Any, List, Optional, Callable


class MiniMCPServer:
    def __init__(
        self,
        name: str = "embedded-debugger-mcp",
        version: str = "1.0.0",
        description: str = "Embedded Hardware Debugger MCP Server",
    ):
        self.name = name
        self.version = version
        self.description = description
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.resources: Dict[str, Dict[str, Any]] = {}

    def tool(self, name: Optional[str] = None, description: Optional[str] = None):
        """Decorator to register a tool with the MCP server."""
        def decorator(fn: Callable):
            tool_name = name or fn.__name__
            tool_desc = description or (fn.__doc__ or "").strip()

            # Generate JSON Schema from type annotations and default values
            sig = inspect.signature(fn)
            properties: Dict[str, Any] = {}
            required: List[str] = []

            for param_name, param in sig.parameters.items():
                if param_name in ("self", "cls"):
                    continue
                param_type = "string"
                ann = param.annotation
                if ann is int:
                    param_type = "integer"
                elif ann is float:
                    param_type = "number"
                elif ann is bool:
                    param_type = "boolean"
                elif ann in (list, List) or getattr(ann, "__origin__", None) in (list, List):
                    param_type = "array"
                elif ann in (dict, Dict) or getattr(ann, "__origin__", None) in (dict, Dict):
                    param_type = "object"

                prop_doc = {"type": param_type}
                if param.default is not inspect.Parameter.empty and param.default is not None:
                    prop_doc["default"] = param.default

                properties[param_name] = prop_doc
                if param.default is inspect.Parameter.empty:
                    required.append(param_name)

            schema = {
                "type": "object",
                "properties": properties,
                "required": required,
            }

            self.tools[tool_name] = {
                "name": tool_name,
                "description": tool_desc,
                "inputSchema": schema,
                "handler": fn,
            }
            return fn
        return decorator

    def resource(
        self,
        uri: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        mime_type: str = "text/plain",
    ):
        """Decorator to register a resource with the MCP server."""
        def decorator(fn: Callable):
            res_name = name or fn.__name__
            res_desc = description or (fn.__doc__ or "").strip()
            self.resources[uri] = {
                "uri": uri,
                "name": res_name,
                "description": res_desc,
                "mimeType": mime_type,
                "handler": fn,
            }
            return fn
        return decorator

    def handle_request(self, req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Processes a JSON-RPC 2.0 request and returns the response dictionary."""
        method = req.get("method")
        msg_id = req.get("id")
        params = req.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                    },
                    "serverInfo": {
                        "name": self.name,
                        "version": self.version,
                    },
                },
            }

        elif method == "notifications/initialized":
            return None

        elif method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

        elif method == "tools/list":
            tools_list = [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "inputSchema": t["inputSchema"],
                }
                for t in self.tools.values()
            ]
            return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools_list}}

        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})
            if tool_name not in self.tools:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Tool '{tool_name}' not found"},
                }

            try:
                fn = self.tools[tool_name]["handler"]
                res = fn(**args)
                text_content = json.dumps(res, indent=2) if isinstance(res, (dict, list)) else str(res)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": text_content}],
                        "isError": False,
                    },
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Error: {e}"}],
                        "isError": True,
                    },
                }

        elif method == "resources/list":
            res_list = [
                {
                    "uri": r["uri"],
                    "name": r["name"],
                    "description": r["description"],
                    "mimeType": r["mimeType"],
                }
                for r in self.resources.values()
            ]
            return {"jsonrpc": "2.0", "id": msg_id, "result": {"resources": res_list}}

        elif method == "resources/read":
            uri = params.get("uri")
            if uri not in self.resources:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32602, "message": f"Resource '{uri}' not found"},
                }
            try:
                fn = self.resources[uri]["handler"]
                content = fn()
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": self.resources[uri]["mimeType"],
                                "text": str(content),
                            }
                        ]
                    },
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32603, "message": f"Resource read failed: {e}"},
                }

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method '{method}' not implemented"},
        }

    def run_stdio(self):
        """Reads JSON-RPC from sys.stdin, writes response to sys.stdout."""
        # Use line buffering
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                req = json.loads(line)
                resp = self.handle_request(req)
                if resp is not None:
                    sys.stdout.write(json.dumps(resp) + "\n")
                    sys.stdout.flush()
            except (KeyboardInterrupt, SystemExit):
                break
            except Exception as e:
                err = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {e}"},
                }
                sys.stdout.write(json.dumps(err) + "\n")
                sys.stdout.flush()

    def run_sse(self, host: str = "0.0.0.0", port: int = 8000):
        """Runs a lightweight HTTP / SSE server for background daemon mode."""
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import urllib.parse
        server_ref = self

        class MCPHTTPHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress default noisy console logs

            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path in ("/sse", "/"):
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "keep-alive")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(b"event: endpoint\ndata: /messages\n\n")
                    self.wfile.flush()
                else:
                    self.send_error(404, "Endpoint not found")

            def do_POST(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path == "/messages":
                    length = int(self.headers.get("Content-Length", 0))
                    raw_body = self.rfile.read(length).decode("utf-8")
                    try:
                        req = json.loads(raw_body)
                        resp = server_ref.handle_request(req)
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        if resp:
                            self.wfile.write(json.dumps(resp).encode("utf-8"))
                        else:
                            self.wfile.write(b"{}")
                    except Exception as e:
                        self.send_error(400, f"Malformed JSON: {e}")
                else:
                    self.send_error(404, "Endpoint not found")

            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()

        httpd = HTTPServer((host, port), MCPHTTPHandler)
        print(f"[*] AI-Deck MiniMCP Daemon listening on http://{host}:{port}/sse")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            httpd.server_close()

    def run(self, transport: str = "stdio", host: str = "0.0.0.0", port: int = 8000):
        if transport in ("sse", "http"):
            self.run_sse(host=host, port=port)
        else:
            self.run_stdio()
