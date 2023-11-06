"""
This is an example of py2app build-macos.py script for freezing your pywebview
application
Usage:
    python build-macos.py py2app
"""

import os
from setuptools import setup
import shutil


def tree(src):
    return [(root, map(lambda f: os.path.join(root, f), files))
            for (root, dirs, files) in os.walk(os.path.normpath(src))]


if os.path.exists('build'):
    shutil.rmtree('build')

if os.path.exists('dist/swallow.app'):
    shutil.rmtree('dist/swallow.app')

ENTRY_POINT = ['main.py']

DATA_FILES = tree('src') + tree('static') + tree('lib')
OPTIONS = {
    'argv_emulation': False,
    'strip': True,
    'includes': ['WebKit', 'Foundation', 'webview'],
    'iconfile': 'logo.ico'
}

setup(
    name='swallow',
    app=ENTRY_POINT,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
