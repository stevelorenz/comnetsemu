#!/usr/bin/env python3

from comnetsemu.net import VERSION
"Setuptools params"

from setuptools import setup, find_packages
from os.path import join

# Get version number from source tree
import sys
sys.path.append('.')

modname = distname = 'comnetsemu'

setup(
    name=distname,
    version=VERSION,
    description='Docker-container based SDN/NFV emulator',
    author='The Deutsche Telekom Chair of Communication Networks, TU Dresden',
    author_email='rlantz@cs.stanford.edu',
    packages=find_packages(
        exclude=['app', 'examples', 'util', 'venv']),
    long_description="""
        ComNetsEmu is a network emulator based on Mininet and Containernet.
        """,
    classifiers=[
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python:: 3.6",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: System :: Emulators",
        'Natural Language :: English'
    ],
    keywords='networking emulator SDN NFV Docker',
    license='BSD',
    install_requires=[
        'setuptools'
    ],
)
