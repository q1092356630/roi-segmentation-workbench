from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path


HOST = "127.0.0.1"
PORT = 8877
URL = f"http://{HOST}:{PORT}/"
ROOT = Path(__file__).resolve().parent
STARTUP_TIMEOUT_SECONDS = 120.0


def roi_service_is_healthy() -> bool:
    try:
        with urllib.request.urlopen(f"{URL}health", timeout=1.5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload.get("service") == "roi-web" and payload.get("status") == "ok"
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def port_is_open() -> bool:
    try:
        with socket.create_connection((HOST, PORT), timeout=0.5):
            return True
    except OSError:
        return False


def show_error(message: str) -> None:
    try:
        from tkinter import messagebox

        messagebox.showerror("ROI 分割工作台", message)
    except Exception:
        pass


def start_service() -> subprocess.Popen[bytes]:
    python = Path(sys.executable)
    pythonw = python.with_name("pythonw.exe")
    executable = pythonw if pythonw.is_file() else python
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(
        [str(executable), "-m", "roi_web", "--host", HOST, "--port", str(PORT), "--no-browser"],
        cwd=str(ROOT),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
        close_fds=True,
    )


def main() -> None:
    if roi_service_is_healthy():
        webbrowser.open(URL)
        return
    if port_is_open():
        show_error(f"端口 {PORT} 已被其他程序占用，ROI 工作台未启动。")
        return

    process = start_service()
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if roi_service_is_healthy():
            webbrowser.open(URL)
            return
        if process.poll() is not None:
            break
        time.sleep(0.25)
    show_error("ROI 工作台启动失败。请检查项目目录和 Python 环境。")


if __name__ == "__main__":
    main()
