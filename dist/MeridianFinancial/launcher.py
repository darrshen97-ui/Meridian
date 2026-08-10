"""Meridian launcher — double-click entry point (brief §15).

Standard library only: this file must run on a bare Python install, before any
of Meridian's dependencies exist. The OS launchers (Start Meridian.bat,
Start Meridian.command, start.sh) do nothing but find Python and run this.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
MIN_PYTHON = (3, 11)
PORTS = range(8787, 8800)
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct")
OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")


def say(message: str = "") -> None:
    print(message, flush=True)


def fail(message: str) -> None:
    say()
    say(message)
    say()
    try:
        input("Press Enter to close this window.")
    except EOFError:
        pass
    sys.exit(1)


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def ensure_python_version() -> None:
    if sys.version_info < MIN_PYTHON:
        fail(
            f"Meridian needs Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer; this "
            f"machine is running Python {sys.version.split()[0]}.\n"
            "Download the current version from https://www.python.org/downloads/ ,\n"
            "install it with the default options, then double-click the launcher again."
        )


def ensure_environment() -> None:
    """Create the venv and install pinned dependencies on first run; reuse after."""
    requirements = ROOT / "requirements.txt"
    stamp = VENV / ".requirements.sha256"
    wanted = hashlib.sha256(requirements.read_bytes()).hexdigest()
    if venv_python().exists() and stamp.exists() and stamp.read_text() == wanted:
        return

    say("First run: setting up Meridian's own Python environment.")
    say("This can take a minute or two — progress below.")
    say()
    if not venv_python().exists():
        venv.create(VENV, with_pip=True)
    result = subprocess.run(
        [str(venv_python()), "-m", "pip", "install", "--disable-pip-version-check",
         "-r", str(requirements)],
        cwd=ROOT,
    )
    if result.returncode != 0:
        fail("Installing Meridian's components failed (details above).\n"
             "Check your internet connection and run the launcher again.")
    stamp.write_text(wanted)
    say()


def prepare_database() -> None:
    say("Preparing the database…")
    result = subprocess.run([str(venv_python()), "-m", "alembic", "upgrade", "head"],
                            cwd=ROOT)
    if result.returncode != 0:
        fail("The database migration failed (details above).\n"
             "If this database came from an older Meridian, move the data/ folder "
             "aside and launch again.")
    result = subprocess.run([str(venv_python()), str(ROOT / "scripts" / "seed_demo.py")],
                            cwd=ROOT)
    if result.returncode != 0:
        fail("Seeding the demo profiles failed (details above).")


def check_ollama() -> None:
    """The model is optional at launch; the app must never fail to start over it."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=2) as resp:
            import json

            models = [m["name"] for m in json.load(resp).get("models", [])]
    except (urllib.error.URLError, OSError, ValueError):
        say()
        say("Note: Ollama isn't running, so AI features are off for now.")
        say("Everything else works. To enable AI later:")
        say("  1. Install Ollama from https://ollama.com/download")
        say(f"  2. Run:  ollama pull {DEFAULT_MODEL}")
        say()
        return
    if DEFAULT_MODEL in models:
        say(f"Local AI model found: {DEFAULT_MODEL}. AI features are on.")
    else:
        say()
        say(f"Note: Ollama is running but the model {DEFAULT_MODEL} isn't pulled,")
        say("so AI features are off for now. To enable them:")
        say(f"  Run:  ollama pull {DEFAULT_MODEL}")
        say("(Meridian never downloads multi-gigabyte models without you asking.)")
        say()


def pick_port() -> int:
    for port in PORTS:
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    fail(f"Ports {PORTS.start}-{PORTS.stop - 1} are all in use. "
         "Close whatever is using them and launch again.")
    raise SystemExit  # unreachable; keeps type-checkers content


def start_server(port: int) -> subprocess.Popen:
    env = dict(os.environ, PORT=str(port))
    return subprocess.Popen(
        [str(venv_python()), "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=ROOT, env=env,
    )


def wait_for_health(port: int, server: subprocess.Popen) -> bool:
    url = f"http://127.0.0.1:{port}/health"
    for _ in range(120):
        if server.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.5)
    return False


def open_browser(url: str) -> None:
    """App mode (a clean window without browser chrome) when Chrome/Edge exists."""
    if os.environ.get("MERIDIAN_NO_BROWSER"):
        say(f"Browser launch skipped (MERIDIAN_NO_BROWSER). Open {url} yourself.")
        return
    candidates: list[str] = []
    if sys.platform == "win32":
        for base in (os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                     os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
                     os.environ.get("LOCALAPPDATA", "")):
            candidates += [
                os.path.join(base, r"Google\Chrome\Application\chrome.exe"),
                os.path.join(base, r"Microsoft\Edge\Application\msedge.exe"),
            ]
    elif sys.platform == "darwin":
        candidates += [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]
    else:
        candidates += [shutil.which(name) or ""
                       for name in ("google-chrome", "chromium", "chromium-browser",
                                    "microsoft-edge")]
    for exe in candidates:
        if exe and Path(exe).exists():
            try:
                subprocess.Popen([exe, f"--app={url}"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except OSError:
                continue
    import webbrowser

    if not webbrowser.open(url):
        say(f"Couldn't open a browser automatically — open {url} yourself.")


def main() -> None:
    os.chdir(ROOT)
    say("Meridian Financial")
    say("------------------")
    ensure_python_version()
    ensure_environment()
    prepare_database()
    check_ollama()

    port = pick_port()
    url = f"http://127.0.0.1:{port}"
    server = start_server(port)
    say(f"Starting the server on {url} …")
    if not wait_for_health(port, server):
        server.terminate()
        fail("The server didn't come up (details above, if any). "
             "Run the launcher again; if it keeps failing, delete the .venv folder "
             "and launch once more.")

    open_browser(url)
    say()
    say(f"Meridian is running at {url}")
    say("Close this window (or press Ctrl-C) to quit Meridian.")
    try:
        server.wait()
    except KeyboardInterrupt:
        say("\nShutting down…")
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
    say("Meridian stopped.")


if __name__ == "__main__":
    main()
