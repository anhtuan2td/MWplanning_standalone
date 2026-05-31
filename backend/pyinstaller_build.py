import runpy
from pathlib import Path

# Shim: forward to packaging/pyinstaller_build.py to keep packaging helpers in one folder.
pkg_script = Path(__file__).resolve().parents[1] / 'packaging' / 'pyinstaller_build.py'
if not pkg_script.exists():
    raise FileNotFoundError(f"packaging helper not found: {pkg_script}")

runpy.run_path(str(pkg_script), run_name='__main__')
