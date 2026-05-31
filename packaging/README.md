Packaging helpers for MW Pre-planning Lite

This folder contains helper scripts and spec files used to produce a standalone Windows executable with PyInstaller. These files are helpers only — do not modify application logic here.

Files
- `build_exe.ps1` — PowerShell wrapper that builds frontend (if needed) and runs PyInstaller. Use from repo root or directly from this folder.
- `pyinstaller_build.py` — Python helper that invokes `PyInstaller.__main__.run` with preconfigured arguments.

Usage

From repository root (recommended):

```powershell
# Powershell: invoke the root build_exe.ps1 (which forwards to packaging/build_exe.ps1)
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

Or run the Python helper directly (requires `pyinstaller` installed):

```powershell
python packaging\pyinstaller_build.py
```

Notes
- The root `build_exe.ps1` and `backend/pyinstaller_build.py` have been replaced by small shims that forward to the scripts in this folder to keep historical compatibility.
- Packaging relies on the `frontend/dist` folder being present; the PowerShell helper will build the frontend when necessary.
