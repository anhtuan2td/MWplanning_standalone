import os
import socket
import sys
import webbrowser
import uvicorn

from app.core.config import get_settings

_INSTANCE_HANDLE = None


def _try_acquire_windows_mutex():
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.CreateMutexW(None, False, "Local\\MWPreplanningLiteSingleInstance")
    if not handle:
        return None
    if ctypes.get_last_error() == 183:
        kernel32.CloseHandle(handle)
        return None
    return handle


def _try_acquire_instance_lock():
    if sys.platform != "win32":
        return object()
    return _try_acquire_windows_mutex()


def _port_in_use(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def main() -> None:
    global _INSTANCE_HANDLE

    settings = get_settings()

    host = os.environ.get("HOST", getattr(settings, 'host', '127.0.0.1'))
    port = int(os.environ.get("PORT", getattr(settings, 'port', 8000)))
    open_browser = os.environ.get("OPEN_BROWSER", "1")

    url = f"http://{host}:{port}"
    _INSTANCE_HANDLE = _try_acquire_instance_lock()
    if _INSTANCE_HANDLE is None:
        if open_browser != "0":
            webbrowser.open(url, new=2, autoraise=True)
        return

    if _port_in_use(host, port):
        print(f"Port {port} is already in use. Close the other service or set PORT to a free port.")
        return

    if open_browser != "0":
        try:
            webbrowser.open(url, new=2, autoraise=True)
        except Exception:
            pass

    from app.main import app

    uvicorn.run(app, host=host, port=port, loop="asyncio")


if __name__ == "__main__":
    main()
