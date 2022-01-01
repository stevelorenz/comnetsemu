#!/usr/bin/env python3

"""Setuptools Configuration"""

from comnetsemu.net import VERSION
from setuptools import setup, find_packages
from os.path import join

# Get version number from source tree
import sys

sys.path.append(".")

scripts = [join("bin", filename) for filename in ["ce"]]
modname = distname = "comnetsemu"

setup(
    name=distname,
    version=VERSION,
    description="Emulator for Computing in Communication Networks.",
    author="The Deutsche Telekom Chair of Communication Networks, TU Dresden",
    author_email="zuo.xiang@tu-dresden.de",
    packages=find_packages(exclude=["app", "examples", "util", "venv"]),
    long_description="""
        A holistic testbed/emulator for the book: Computing in Communication Networks: From Theory to Practice
        """,
    classifiers=[
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Programming Language :: Python:: 3.6",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: System :: Emulators",
        "Natural Language :: English",
        "License :: MIT License",
    ],
    keywords="networking emulator SDN NFV Docker",
    # license="BSD",
    # MARK: MINIMAL requirements
    install_requires=[
        "docker>=4.1.0,<5.0.0",
        "pyroute2>=0.5.9,<0.6.0",
        "requests>=2.22.0,< 3.0.0",
        "ryu>=4.30,<5.0",
        "setuptools>=45.2.0,<46.0.0",
        # Mininet is installed FROM SOURCE CODE because:
        # - The version in Ubuntu's repo is too old
        # - It's not fully available on PyPi (The searchable package on PyPi
        #   does not work out-of-box yet. Check: https://github.com/mininet/mininet/pull/970)
        # - Mininet needs to be patched when some features of ComNetsEmu can
        #   not be implemented without modifying the source code of Mininet
        "mininet>=2.3.0d6",
    ],
    scripts=scripts,
)
