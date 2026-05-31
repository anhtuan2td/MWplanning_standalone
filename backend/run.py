"""Thin shim to keep packaging logic in packaging/ while leaving a stable entrypoint.

This file remains at `backend/run.py` for backward compatibility and during development.
It imports and calls the implementation from `packaging/run_impl.py` when present.
"""

from pathlib import Path
import runpy

pkg_impl = Path(__file__).resolve().parents[1] / 'packaging' / 'run_impl.py'
if pkg_impl.exists():
    runpy.run_path(str(pkg_impl), run_name='__main__')
else:
    # fallback: simple uvicorn starter to preserve previous behaviour
    import os
    import socket
    import sys
    import webbrowser
    import uvicorn

    def _port_in_use(host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            return False

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    open_browser = os.environ.get("OPEN_BROWSER", "1")

    url = f"http://{host}:{port}"
    if _port_in_use(host, port):
        print(f"Port {port} is already in use. Close the other service or set PORT to a free port.")
        sys.exit(1)

    if open_browser != "0":
        try:
            webbrowser.open(url, new=2, autoraise=True)
        except Exception:
            pass

    from app.main import app
    uvicorn.run(app, host=host, port=port, loop="asyncio")
