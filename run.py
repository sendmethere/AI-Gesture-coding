#!/usr/bin/env python3
"""Entry point for the AI Gesture Coding desktop app.

Starts the FastAPI backend on a local port, then opens it in a native
pywebview window. If pywebview is unavailable, it falls back to your browser.

    python run.py                 # native window (or browser fallback)
    python run.py --browser       # force the browser
    python run.py --no-window     # just run the server (headless)
"""
import sys
import threading
import time

import uvicorn

HOST = "127.0.0.1"
PORT = 8765
URL = f"http://{HOST}:{PORT}"


def _serve():
    uvicorn.run("backend.app:app", host=HOST, port=PORT, log_level="warning")


def _wait_for_server(timeout=15.0):
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(URL, timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False


def _open_dialog(webview):
    """Open-file dialog constant. Prefer the modern FileDialog.OPEN enum
    (pywebview >= 5); fall back to the deprecated OPEN_DIALOG on older versions."""
    fd = getattr(webview, "FileDialog", None)
    return fd.OPEN if fd is not None else webview.OPEN_DIALOG


class WebviewApi:
    """Exposed to the frontend as window.pywebview.api for native dialogs."""

    def __init__(self):
        self._window = None

    def set_window(self, window):
        self._window = window

    def pick_video(self):
        import webview

        types = ("Video files (*.mp4;*.mov;*.avi;*.mkv)", "All files (*.*)")
        res = self._window.create_file_dialog(
            _open_dialog(webview), allow_multiple=False, file_types=types
        )
        return res[0] if res else None

    def pick_json(self):
        import webview

        types = ("JSON files (*.json)", "All files (*.*)")
        res = self._window.create_file_dialog(
            _open_dialog(webview), allow_multiple=False, file_types=types
        )
        return res[0] if res else None


def main():
    args = set(sys.argv[1:])
    threading.Thread(target=_serve, daemon=True).start()

    if not _wait_for_server():
        print("Server failed to start.", file=sys.stderr)
        sys.exit(1)
    print(f"Server running at {URL}")

    if "--no-window" in args:
        print("Headless mode. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return

    if "--browser" not in args:
        try:
            import webview

            api = WebviewApi()
            window = webview.create_window(
                "AI Gesture Coding for Microteaching",
                URL,
                width=1400,
                height=900,
                min_size=(1100, 720),
                js_api=api,
            )
            api.set_window(window)
            webview.start()
            return
        except Exception as e:
            print(f"pywebview unavailable ({e}); opening browser instead.")

    import webbrowser

    webbrowser.open(URL)
    print("Opened in browser. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
