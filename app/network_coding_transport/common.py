#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Shared by all coders
"""

import kodo
import struct

MTU = 1500
BUFFER_SIZE = 4096
IO_SLEEP = 0.001  # second

# KODO parameters
FIELD = kodo.field.binary8
SYMBOLS = 4
SYMBOL_SIZE = 100


"""
Meta data header format:

Offsets Octet 0               1                            2                   3         4
Octet
0             | Type          | Generation sequence number | Payload length              |

- Type: 0x00 -> UDP segment, 0x01 -> In UDP encapsulated TCP segment

- Generation sequence number: Starts from 0

- Payload length: The length of the original payload
    - For UDP segment: The length in bytes of the UDP payload
    - For in UDP encapsulated TCP segment: The length in bytes of the TCP header
      and payload

The OAM packet uses UDP, the UDP payload format:

Offsets Octet 0                   1
Octet
0             | Redundancy number |

"""

META_DATA_LEN = 1 + 1 + 2  # bytes

MD_TYPE_UDP = 0x00
MD_TYPE_TCP_IN_UDP = 0x01

UDP_PORT_OAM = 8888
UDP_PORT_DATA = 9999


def pull_metadata(rx_tx_buf, offset):
    """Parse and return meta data"""
    md_type, generation, md_pl_len = struct.unpack_from(
        ">BBH", rx_tx_buf, offset)
    return (md_type, generation, md_pl_len)


def push_metadata(rx_tx_buf, offset, metadata):
    md_type, generation, md_pl_len = metadata
    struct.pack_into(">BBH", rx_tx_buf, offset, md_type, generation, md_pl_len)
