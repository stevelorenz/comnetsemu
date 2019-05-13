#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Shared by all coders
"""

import kodo
import struct

MTU = 1500
BUFFER_SIZE = 2048
IO_SLEEP = 0.001  # second

# KODO parameters
FIELD = kodo.field.binary8
SYMBOLS = 8
SYMBOL_SIZE = 1000


"""
Meta data header format:

Offsets Octet 0               1                   2                   3
Octet
0             |   Type        |   Generation sequence number          |

- Type: 0x00 -> OAM UDP segment, 0x01 -> data UDP segment
- Generation sequence number: Starts from 0

Payload format:

- OAM segment: 1 byte -> redundancy

"""

META_DATA_LEN = 3  # bytes
MD_TYPE_OAM = 0x00
MD_TYPE_DATA = 0x01


def pull_metadata(rx_tx_buf, offset):
    """Parse and return meta data"""
    _type = struct.unpack_from(">B", rx_tx_buf, offset)[0]
    generation = struct.unpack_from(">H", rx_tx_buf, offset+1)[0]
    return (_type, generation)


def push_metadata(rx_tx_buf, offset, metadata):
    _type, generation = metadata
    struct.pack_into(">B", rx_tx_buf, offset, _type)
    struct.pack_into(">H", rx_tx_buf, offset+1, generation)
