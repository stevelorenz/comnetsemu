#!/usr/bin/env python3

"""Setuptools Configuration"""

import codecs

from setuptools import setup, find_packages
from os.path import join

from comnetsemu.net import VERSION

scripts = [join("bin", filename) for filename in ["ce"]]
modname = distname = "comnetsemu"

long_description = ""
with codecs.open("./README.md", encoding="utf-8") as readme_md:
    long_description = readme_md.read()

setup(
    name=distname,
    version=VERSION,
    description="A virtual emulator/testbed designed for the book: Computing in Communication Networks: From Theory to Practice",
    author="The Deutsche Telekom Chair of Communication Networks, TU Dresden",
    author_email="zuo.xiang@tu-dresden.de",
    packages=find_packages(exclude=["app", "examples", "util", "venv"]),
    long_description=long_description,
    url="https://github.com/stevelorenz/comnetsemu",
    classifiers=[
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Programming Language :: Python:: 3.8",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: System :: Emulators",
        "Natural Language :: English",
        "License :: MIT License",
    ],
    keywords="networking emulator SDN NFV Docker",
    python_requires=">=3.8",
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
