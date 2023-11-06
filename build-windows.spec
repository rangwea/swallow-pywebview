# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

py_files = [
    'main.py',
    'src\\api.py',
    'src\\cossync.py',
    'src\\globals.py',
    'src\\initsql.py',
]

added_files = [
    ('lib', 'lib'),
    ('static', 'static'),
]

a = Analysis(
    ['main.py'],
    pathex=['dist'],
    binaries=[],
    datas=added_files,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='swallow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon='logo.ico',
)
