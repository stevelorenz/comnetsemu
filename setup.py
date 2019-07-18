#!/usr/bin/env python3

"Setuptools Params"

from setuptools import setup, find_packages

# from os.path import join

# Get version number from source tree
import sys
sys.path.append('.')
from comnetsemu.net import VERSION

modname = distname = 'comnetsemu'

setup(
    name=distname,
    version=VERSION,
    description='A holistic testbed/emulator for the book: Computing in Communication Networks: From Theory to Practice',
    author='The Deutsche Telekom Chair of Communication Networks, TU Dresden',
    author_email='zuo.xiang@tu-dresden.de',
    packages=find_packages(
        exclude=['app', 'examples', 'util', 'venv']),
    long_description="""
        A holistic testbed/emulator for the book: Computing in Communication Networks: From Theory to Practice
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
