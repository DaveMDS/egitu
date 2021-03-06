#!/usr/bin/env python

from distutils.core import setup
from efl.utils.setup import build_extra, build_edc, uninstall
from egitu import __version__


setup(
    name = 'egitu',
    version = __version__,
    description = 'Git GUI',
    long_description = 'Efl GIT gUi written in python',
    license = "GNU GPL",
    author = 'Dave Andreoli',
    author_email = 'dave@gurumeditation.it',
    packages = ['egitu'],
    requires = ['efl (>=1.13)', 'xdg'],
    provides = ['egitu'],
    scripts = ['bin/egitu'],
    data_files = [
        ('share/egitu/themes/default', ['data/themes/default/images/avatar.png']),
        ('share/applications', ['data/egitu.desktop']),
        ('share/icons', ['data/icons/256x256/egitu.png']),
        ('share/icons/hicolor/256x256/apps', ['data/icons/256x256/egitu.png']),
    ],
    cmdclass={
        'build': build_extra,
        'build_edc': build_edc,
        'uninstall': uninstall,
    },
    command_options={
        'install': {'record': ('setup.py', 'installed_files.txt')}
    },
)

