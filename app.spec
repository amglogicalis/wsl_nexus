# -*- mode: python ; coding: utf-8 -*-

import os, importlib.util
_winpty_dir = os.path.dirname(importlib.util.find_spec('winpty').origin)
_winpty_bins = [
    (os.path.join(_winpty_dir, 'winpty-agent.exe'), 'winpty'),
    (os.path.join(_winpty_dir, 'winpty.dll'),       'winpty'),
    (os.path.join(_winpty_dir, 'conpty.dll'),        'winpty'),
    (os.path.join(_winpty_dir, 'OpenConsole.exe'),   'winpty'),
]


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=_winpty_bins,
    datas=[('index.html', '.'), ('app.css', '.'), ('app.js', '.'), ('app.ico', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app.ico'],
)
