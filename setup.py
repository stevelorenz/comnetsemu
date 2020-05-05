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
        "setuptools>=39.0.1,<40.0.0",
        "docker>=3.7.2,<4.0.0",
        "pyroute2>=0.5.7,<0.6.0",
        "requests>=2.22.0,< 3.0.0",
        # Not available on PyPi, installed from source code.
        "mininet>=2.3.0d6",
        "ryu>=4.34,<5.0",
    ],
    scripts=scripts,
)
