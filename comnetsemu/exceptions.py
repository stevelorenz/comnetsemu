#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ComNetsEmu exceptions

This module contains the set of ComNetsEmu's exceptions.
"""

__all__ = ["InvalidDockerArgs"]


class InvalidDockerArgs(ValueError):
    """The Docker arguments provided was somehow invalid."""
