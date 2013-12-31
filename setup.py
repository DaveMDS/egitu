#!/usr/bin/env python

from distutils.core import setup


setup(
    name = 'egitu',
    version = '0.1',
    description = 'Git GUI',
    long_description = 'Efl GIT gUi written in python',
    license = "GNU GPL",
    author = 'Dave Andreoli',
    author_email = 'dave@gurumeditation.it',
    packages = ['egitu'],
    requires = ['efl', 'xdg'],
    provides = ['egitu'],
    package_data = {
        'egitu': ['themes/*/*'],
    },
    data_files = [
        ('bin', ['bin/egitu']),
        ('share/applications', ['data/egitu.desktop']),
        ('share/icons', ['data/icons/256x256/egitu.png']),
        ('share/icons/hicolor/256x256/apps', ['data/icons/256x256/egitu.png']),
    ]
)

