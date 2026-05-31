# Frontend-related spec copy (kept for reference)
from PyInstaller.utils.hooks import collect_all

datas = [('frontend\\dist', 'frontend\\dist')]
binaries = []
hiddenimports = []

a = Analysis(
    [],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
