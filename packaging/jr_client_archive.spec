# PyInstaller spec for JR Client Archive (Fase 9 - packaging).
#
# Build (from the repo root, with the dev venv active):
#   pyinstaller packaging/jr_client_archive.spec
#
# Produces a one-folder build under dist/jr-client-archive/ - the app is
# fully offline, so a folder the user can copy/run from a USB stick or
# install path is preferable to a single compressed onefile exe.

from pathlib import Path

# PyInstaller injects SPECPATH (directory containing this .spec file) into
# the exec namespace - __file__ is not available here.
REPO_ROOT = Path(SPECPATH).resolve().parent
SRC_ROOT = REPO_ROOT / "src"

block_cipher = None

a = Analysis(
    [str(SRC_ROOT / "jr_client_archive" / "app.py")],
    pathex=[str(SRC_ROOT)],
    binaries=[],
    datas=[
        (str(SRC_ROOT / "jr_client_archive" / "resources"), "jr_client_archive/resources"),
    ],
    hiddenimports=[
        "jr_client_archive.db.models",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="jr-client-archive",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="jr-client-archive",
)
