#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
"""
About: Raw Packet Socket IO helper functions
"""

import struct

import log

logger = log.logger

ETH_HDL = 14
UDP_HDL = 8

ETH_PROTO_IPV4 = int("0x0800", 16)

IP_PROTO_UDP = 17
IP_PROTO_TCP = 6

TCP_HD_LEN_MAX = 60


def print_hex(arr):
    """Print a bytearray in xNN format"""
    print("".join("x{:02x}".format(x) for x in arr))


def update_cksum_ipv4(rx_tx_buf, ip_hd_offset, ip_hd_len):
    """Update the IPv4 header checksum

    http://en.wikipedia.org/wiki/IPv4_header_checksum
    """
    struct.pack_into(">H", rx_tx_buf, ip_hd_offset+10, 0)

    s = 0
    for i in range(0, ip_hd_len, 2):
        a, b = struct.unpack_from(
            '>2B', rx_tx_buf[ip_hd_offset:ip_hd_offset+ip_hd_len], i
        )
        w = a + (b << 8)
        s = s + w

    s = (s >> 16) + (s & 0xffff)
    s = s + (s >> 16)
    # complement and mask to 4 byte short
    s = ~s & 0xffff

    logger.debug("[IP_CKSUM] New IP checksum:0x{:02x}".format(s))
    struct.pack_into("<H", rx_tx_buf, ip_hd_offset+10, (s))


def update_ip_udp_len(
        rx_tx_buf, ip_hd_offset, udp_hd_offset, ip_total_len, udp_total_len):
    struct.pack_into(">H", rx_tx_buf, ip_hd_offset+2, ip_total_len)
    struct.pack_into(">H", rx_tx_buf, udp_hd_offset+4, udp_total_len)


def recv_ipv4(sock, rx_tx_buf, buf_size):
    """Receive a IPv4 packet into rx/tx buffer"""
    frame_len = sock.recv_into(rx_tx_buf, buf_size)
    hd_offset = 0
    eth_typ = struct.unpack_from(">H", rx_tx_buf, 12)[0]

    # IPv4 packets 0x800
    if eth_typ != ETH_PROTO_IPV4:
        logger.debug("None-IPv4 Packet, ethernet type: %s", hex(eth_typ))
        return None

    # Parse IPv4 header
    hd_offset += ETH_HDL
    # Calculate IP header length
    ver_ihl = struct.unpack_from(">B", rx_tx_buf, hd_offset)[0]
    ip_hd_len = 4 * int(hex(ver_ihl)[-1])
    ip_proto = struct.unpack_from(">B", rx_tx_buf, hd_offset + 9)[0]
    ip_hd_offset = hd_offset

    return (frame_len, ip_hd_offset, ip_hd_len, ip_proto)


def parse_tcp(rx_tx_buf, ip_hd_offset, ip_hd_len):
    """Parse TCP header"""
    ip_total_len = struct.unpack_from(">H", rx_tx_buf, ip_hd_offset+2)[0]
    tcp_hd_offset = ip_hd_offset + ip_hd_len
    tmp = struct.unpack_from(">B", rx_tx_buf, tcp_hd_offset+12)[0]
    src_port, dst_port = struct.unpack_from(">HH", rx_tx_buf, tcp_hd_offset)
    tcp_hd_len = (tmp >> 4) * 4
    tcp_pl_len = ip_total_len - ip_hd_len - tcp_hd_len
    flags = struct.unpack_from(">B", rx_tx_buf, tcp_hd_offset+13)[0]
    # Convert integer into bits array
    flags_arr = [1 if digit == "1" else 0 for digit in "{0:08b}".format(flags)]
    return (src_port, dst_port,
            tcp_hd_offset, tcp_hd_len, tcp_pl_len,
            flags_arr)


def parse_udp(rx_tx_buf, ip_hd_offset, ip_hd_len):
    """Parse UDP header"""
    udp_hd_offset = ip_hd_offset + ip_hd_len
    udp_pl_offset = udp_hd_offset + UDP_HDL
    udp_dst_port = struct.unpack_from(">H", rx_tx_buf, udp_hd_offset+2)[0]
    udp_pl_len = struct.unpack_from(
        ">H", rx_tx_buf, udp_hd_offset + 4)[0] - UDP_HDL

    return (udp_hd_offset, udp_dst_port, udp_pl_offset, udp_pl_len)


def encap_tcp_udp(rx_tx_buf, ip_hd_offset, ip_hd_len):
    """Encapsulate the TCP segment into a UDP segment"""
    src_port, dst_port, tcp_hd_offset, tcp_hd_len, tcp_pl_len, flags_arr = parse_tcp(
        rx_tx_buf, ip_hd_offset, ip_hd_len)

    logger.debug("TCP header len: %d, Payload Len: %d, flags: FIN:%d, SYN:%d, RSH:%d, PSH:%d, ACK: %d",
                 tcp_hd_len, tcp_pl_len,
                 flags_arr[-1], flags_arr[-2], flags_arr[-3], flags_arr[-4],
                 flags_arr[-5])

    # Append a UDP header
    _len = UDP_HDL + tcp_hd_len + tcp_pl_len
    st = tcp_hd_offset
    ed = tcp_hd_offset+tcp_hd_len+tcp_pl_len
    rx_tx_buf[st+UDP_HDL:ed+UDP_HDL] = rx_tx_buf[st:ed]
    struct.pack_into(">HHH", rx_tx_buf, st, src_port, dst_port, _len)
    return (tcp_hd_len + tcp_pl_len)
