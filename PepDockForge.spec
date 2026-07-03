# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_dynamic_libs
from PyInstaller.utils.hooks import collect_all

ROOT = Path.cwd()

datas = []
binaries = []
hiddenimports = ['rdkit', 'rdkit.Chem', 'rdkit.Chem.AllChem', 'openmm', 'openmm.app', 'openmm.unit']
datas += [
    (str(ROOT / 'assets' / 'pepdock_logo_lockup.png'), 'assets'),
    (str(ROOT / 'assets' / 'pepdock_app_icon.png'), 'assets'),
    (str(ROOT / 'assets' / 'pepdock_logo_mono.png'), 'assets'),
]
datas += collect_data_files('rdkit')
datas += collect_data_files('openmm')
binaries += collect_dynamic_libs('rdkit')
binaries += collect_dynamic_libs('openmm')
tmp_ret = collect_all('openpyxl')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('meeko')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('gemmi')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

conflicting_dlls = {
    'icudt75.dll',
    'icuin.dll',
    'icuin75.dll',
    'icuuc.dll',
    'icuuc75.dll',
}

def without_conflicting_dlls(entries):
    filtered = []
    for entry in entries:
        source_name = entry[0].split('\\')[-1].split('/')[-1].lower()
        target_name = entry[1].split('\\')[-1].split('/')[-1].lower() if len(entry) > 1 else ''
        if source_name in conflicting_dlls or target_name in conflicting_dlls:
            continue
        filtered.append(entry)
    return filtered

binaries = without_conflicting_dlls(binaries)
datas = without_conflicting_dlls(datas)


a = Analysis(
    ['pepdock_forge.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'matplotlib', 'pandas', 'pytest'],
    noarchive=False,
    optimize=0,
)
a.binaries = without_conflicting_dlls(a.binaries)
a.datas = without_conflicting_dlls(a.datas)
pyz = PYZ(a.pure)

exe_kwargs = {}
if sys.platform.startswith('win'):
    exe_kwargs['icon'] = [str(ROOT / 'assets' / 'pepdock_forge.ico')]

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PepDockForge',
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
    **exe_kwargs,
)
