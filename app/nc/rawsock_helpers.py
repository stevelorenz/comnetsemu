#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
"""
About: Raw Socket IO helper functions
"""

import struct
import logging

logger = logging.getLogger("nc_coder")

ETH_HDL = 14
UDP_HDL = 8


def calc_ih_cksum(hd_b_arr):
    """Calculate IP header checksum
    MARK: To generate a new checksum, the checksum field itself is set to zero

    :para hd_b_arr: Bytes array of IP header
    :retype: int
    """
    s = 0
    for i in range(0, len(hd_b_arr), 2):
        a, b = struct.unpack_from('>2B', hd_b_arr, i)
        w = a + (b << 8)
        s = ((s + w) & 0xffff + (s + w >> 16))
    return ~s & 0xffff


def update_cksum_udp(rx_tx_buf, ip_hd_offset, ip_hd_len):
    """Update the IP/UDP header checksum of a UDP segment"""
    struct.pack_into(">H", rx_tx_buf, ip_hd_offset+10, 0)
    cksum = calc_ih_cksum(rx_tx_buf[ip_hd_offset:ip_hd_offset +
                                    ip_hd_len])
    struct.pack_into("<H", rx_tx_buf, ip_hd_len+10, cksum)


def rx_buf_udp(sock, rx_tx_buf, buf_size):
    """Receive a UDP segment into rx/tx buffer"""
    frame_len = sock.recv_into(rx_tx_buf, buf_size)
    hd_offset = 0
    eth_typ = struct.unpack(">H", rx_tx_buf[12:14])[0]
    # IPv4 packets 0x800
    if eth_typ != int("0x800", 16):
        return None

    # Parse IPv4 header
    hd_offset += ETH_HDL
    # Calculate IP header length
    ver_ihl = struct.unpack(">B", rx_tx_buf[hd_offset:hd_offset + 1])[0]
    ip_hd_len = 4 * int(hex(ver_ihl)[-1])
    ip_tlen = struct.unpack(">H", rx_tx_buf[hd_offset + 2:hd_offset + 4])[0]
    proto = struct.unpack(">B", rx_tx_buf[hd_offset + 9:hd_offset + 10])[0]
    logger.info(
        "Recv a IPv4 packet, header len: {}, total len: {}, proto: {}".format(
            ip_hd_len, ip_tlen, proto))
    # UDP protocol 17
    if proto != 17:
        return None

    # Parse UDP header
    hd_offset += ip_hd_len
    # Make it simple, disable UDP checksum
    struct.pack_into(">H", rx_tx_buf, hd_offset+6, 0)
    udp_pl_offset = hd_offset + UDP_HDL
    # UDP payload length
    udp_pl_len = struct.unpack(
        '>H', rx_tx_buf[hd_offset + 4:hd_offset + 6])[0] - UDP_HDL
    ip_hd_offset = hd_offset - ip_hd_len

    return (frame_len, ip_hd_offset, ip_hd_len, udp_pl_offset, udp_pl_len)
