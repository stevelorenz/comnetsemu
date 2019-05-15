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

ETH_PROTO_IPV4 = int("0x0800", 16)

IP_PROTO_UDP = 17
IP_PROTO_TCP = 6


def update_cksum_ipv4(rx_tx_buf, ip_hd_offset, ip_hd_len):
    """Update the IPv4 header checksum"""
    struct.pack_into(">H", rx_tx_buf, ip_hd_offset+10, 0)

    s = 0
    for i in range(0, ip_hd_len, 2):
        a, b = struct.unpack_from(
            '>2B', rx_tx_buf[ip_hd_offset:ip_hd_offset+ip_hd_len], i
        )
        w = a + (b << 8)
        s = ((s + w) & 0xffff + (s + w >> 16))

    struct.pack_into("<H", rx_tx_buf, ip_hd_offset+10, (~s & 0xffff))


def recv_ipv4(sock, rx_tx_buf, buf_size):
    """Receive a IPv4 packet into rx/tx buffer

    :return: (frame_len, ip_hd_offset, ip_hd_len) for IPv4 packet, None for other
    frame types.
    """
    frame_len = sock.recv_into(rx_tx_buf, buf_size)
    hd_offset = 0
    eth_typ = struct.unpack(">H", rx_tx_buf[12:14])[0]
    # IPv4 packets 0x800
    if eth_typ != ETH_PROTO_IPV4:
        return None

    # Parse IPv4 header
    hd_offset += ETH_HDL
    # Calculate IP header length
    ver_ihl = struct.unpack(">B", rx_tx_buf[hd_offset:hd_offset + 1])[0]
    ip_hd_len = 4 * int(hex(ver_ihl)[-1])
    ip_tlen = struct.unpack(">H", rx_tx_buf[hd_offset + 2:hd_offset + 4])[0]
    proto = struct.unpack(">B", rx_tx_buf[hd_offset + 9:hd_offset + 10])[0]
    logger.debug(
        "Recv a IPv4 packet, header len: {}, total len: {}, proto: {}".format(
            ip_hd_len, ip_tlen, proto))
    ip_hd_offset = hd_offset
    return (frame_len, ip_hd_offset, ip_hd_len, proto)


def parse_udp(rx_tx_buf, ip_hd_offset, ip_hd_len):
    """"""
    udp_hd_offset = ip_hd_offset + ip_hd_len
    udp_pl_offset = udp_hd_offset + UDP_HDL
    # UDP payload length
    udp_pl_len = struct.unpack(
        '>H', rx_tx_buf[udp_hd_offset + 4:udp_hd_offset + 6])[0] - UDP_HDL

    return (udp_hd_offset, udp_pl_offset, udp_pl_len)
