"""
Local HTTP server that catches Paystack's payment callback redirect.

Usage (from payments.py screen):
    from utils.callback_server import start_callback_server, stop_callback_server
    start_callback_server(on_reference=self._on_callback_reference)

Paystack redirects to http://localhost:8765/payment/callback?reference=ATTEND-...
The server extracts the reference, calls your on_reference callback on the
Kivy main thread, then shuts itself down.
"""
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from kivy.clock import Clock

PORT = 8765
_server: HTTPServer | None = None
_thread: threading.Thread | None = None


def start_callback_server(on_reference):
    """
    Start the local server. on_reference(ref: str) will be called on the
    Kivy main thread when Paystack redirects back with a reference.
    """
    global _server, _thread

    stop_callback_server()   # kill any previous instance

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass   # silence request logs

        def do_GET(self):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            reference = (
                params.get("reference", params.get("trxref", [None]))[0]
            )

            if reference:
                # Send a nice HTML response so the browser doesn't show a blank page
                html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Payment Received</title>
  <style>
    body {{ font-family: sans-serif; display: flex; align-items: center;
            justify-content: center; height: 100vh; margin: 0;
            background: #f0faf4; }}
    .card {{ text-align: center; padding: 48px; border-radius: 16px;
             background: white; box-shadow: 0 4px 24px rgba(0,0,0,.08); }}
    h1 {{ color: #21b34b; margin-bottom: 8px; }}
    p  {{ color: #666; }}
    code {{ background: #f4f4f4; padding: 4px 10px; border-radius: 6px;
             font-size: 13px; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>&#10003; Payment Received</h1>
    <p>Reference: <code>{reference}</code></p>
    <p>You can close this tab. The app is verifying your payment…</p>
  </div>
</body>
</html>"""
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(html.encode())

                # Fire callback on Kivy main thread, then shut down
                Clock.schedule_once(lambda dt: on_reference(reference), 0.1)
                Clock.schedule_once(lambda dt: stop_callback_server(), 0.5)
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing reference")

    _server = HTTPServer(("localhost", PORT), Handler)
    _thread = threading.Thread(target=_server.serve_forever, daemon=True)
    _thread.start()


def stop_callback_server():
    global _server, _thread
    if _server:
        threading.Thread(target=_server.shutdown, daemon=True).start()
        _server = None
        _thread = None
