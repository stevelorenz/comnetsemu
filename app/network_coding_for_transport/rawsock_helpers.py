#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Packet Socket (with SOCK_RAW) helper functions.
"""

import copy
import socket
import struct

import log
from common import UDP_PORT_DATA

logger = log.logger

ETH_HDL = 14
IP_HDL_MIN = 20
UDP_HDL = 8

ETH_PROTO_IPV4 = int("0x0800", 16)

IP_PROTO_UDP = 17
IP_PROTO_TCP = 6


def print_hex(arr):
    """Print a bytearray in hex format."""
    print("".join("x{:02x}".format(x) for x in arr))


def update_cksum_ipv4(buf, ip_hd_offset, ip_hd_len):
    """Update the IPv4 header checksum.
    MARK: This function is relative slow with Python...
    http://en.wikipedia.org/wiki/IPv4_header_checksum
    """
    s = 0

    struct.pack_into(">H", buf, ip_hd_offset + 10, 0)
    for i in range(0, ip_hd_len, 2):
        a, b = struct.unpack_from(
            ">2B", buf[ip_hd_offset : ip_hd_offset + ip_hd_len], i
        )
        w = a + (b << 8)
        s = s + w
    s = (s >> 16) + (s & 0xFFFF)
    s = s + (s >> 16)
    # complement and mask to 4 byte short
    s = ~s & 0xFFFF

    logger.debug("[IP_CKSUM] New IP checksum: 0x{:02x}".format(s))
    struct.pack_into("<H", buf, ip_hd_offset + 10, (s))


def update_ip_udp_len(buf, ip_hd_offset, udp_hd_offset, ip_total_len, udp_total_len):
    struct.pack_into(">H", buf, ip_hd_offset + 2, ip_total_len)
    struct.pack_into(">H", buf, udp_hd_offset + 4, udp_total_len)


def recv_ipv4(sock, buf: bytearray, buf_size: int):
    """Receive a IPv4 packet into the buffer buf."""
    frame_len = sock.recv_into(buf, buf_size)
    hd_offset = 0
    eth_typ = struct.unpack_from(">H", buf, 12)[0]
    if eth_typ != ETH_PROTO_IPV4:
        logger.debug("None-IPv4 Packet, its ethernet type: %s\n", hex(eth_typ))
        return None

    hd_offset += ETH_HDL
    # Calculate the IP header length based on ihl field.
    ver_ihl = struct.unpack_from(">B", buf, hd_offset)[0]
    ip_hd_len = 4 * int(hex(ver_ihl)[-1])
    ip_proto = struct.unpack_from(">B", buf, hd_offset + 9)[0]
    ip_hd_offset = hd_offset

    return (frame_len, ip_hd_offset, ip_hd_len, ip_proto)


def parse_udp(buf, ip_hd_offset, ip_hd_len):
    """Parse UDP header."""
    udp_hd_offset = ip_hd_offset + ip_hd_len
    udp_pl_offset = udp_hd_offset + UDP_HDL
    udp_dst_port = struct.unpack_from(">H", buf, udp_hd_offset + 2)[0]
    udp_pl_len = struct.unpack_from(">H", buf, udp_hd_offset + 4)[0] - UDP_HDL

    return (udp_hd_offset, udp_dst_port, udp_pl_offset, udp_pl_len)


# MARK:  <Zuo> Replace the vanilla packet socket in coders with this wrapper #
class PacketSocket(object):
    """A wrapper for Packet socket.

    The purpose of this wrapper is to hide the boilerplate code for packet
    socket processing, en- and decapsulation etc.

    - Blocking IO is used for simplicity.
    """

    def __init__(self, buf: bytearray, interface: str, proto: int = 3):

        self._sock = socket.socket(
            socket.AF_PACKET, socket.SOCK_RAW, socket.htons(proto)
        )
        self._buf = buf
        self._buf_size = len(buf)
        self._filters = list()
        self._interface = interface

        self._ip_hd_offset = ETH_HDL
        self._ip_hd_len = IP_HDL_MIN

    def bind(self):
        logger.info("Bind packet socket to interface {}\n".format(self._interface))
        self._sock.bind((self._interface, 0))

    def recv_with_filters(self, size: int = 2048):
        frame_len = self._sock.recv_into(self._buf, size)
        print(frame_len)
        for f in self._filters:
            if not f(self._buf):
                logger.debug(f"Filter: {f.__name__} returns False.")
                return -1
        else:
            return frame_len

    def send(self, size: int):
        self._sock.send(self._buf[:size])

    def get_buf(self, deep_copy: bool = False):
        """Get the buffer (bytearray) of the packet socket

        :param deep_copy:
        :type deep_copy: bool
        """
        if deep_copy:
            return copy.deepcopy(self._buf)
        return self._buf

    def close(self):
        self._sock.close()

    def _calc_cksum(self):
        """Calculate the new IP checksum and disable UDP checksum."""
        struct.pack_into(">H", self._buf, self._ip_hd_offset + 10, 0)
        s = 0
        for i in range(0, IP_HDL_MIN, 2):
            a, b = struct.unpack_from(
                ">2B",
                self._buf[self._ip_hd_offset : self._ip_hd_offset + self._ip_hd_len],
                i,
            )
            w = a + (b << 8)
            s = s + w

        s = (s >> 16) + (s & 0xFFFF)
        s = s + (s >> 16)
        # Complement and mask to 4 byte short
        s = ~s & 0xFFFF

        logger.debug("[IP_CKSUM] New IP checksum:0x{:02x}".format(s))
        struct.pack_into("<H", self._buf, self._ip_hd_offset + 10, (s))

    def encap_ip_udp(self):
        """Encapsulate the WHOLE IPv4 packet in buffer with a new IPv4 packet
        with the same IP info"""
        pass

    def decap_ip_udp(self):
        pass

    def add_filter(self, filter_func):
        """Add a filter function to filter out uninterested frame.

        :param filter_func: The name of the filter function. This function must
        has only one argument with type: bytearray. It must return either True
        of False to indicate if the packet should be filtered out. False ->
        Filter out.
        """
        self._filters.append(filter_func)
        logger.info(
            f"Add filter {filter_func}, number of added filters: {len(self._filters)}"
        )

    def _check_filter(self):
        for f in self._filters:
            if not f(self._buf):
                return False
        else:
            return True

    # An example of a filter function
    @staticmethod
    def filter_non_ipv4(buf):
        eth_typ = struct.unpack_from(">H", buf, 12)[0]
        if eth_typ != ETH_PROTO_IPV4:
            return False
        return True


if __name__ == "__main__":
    import timeit

    log.conf_logger("DEBUG")
    logger.info("* Run tests.")
    buf = bytearray(4096)  # CPU cache slot size
    sock = PacketSocket(buf, "lo")
    sock.bind()
    buf_shallow = sock.get_buf()
    assert id(buf_shallow) == id(buf)
    buf_copy = sock.get_buf(deep_copy=True)
    assert id(buf_copy) != id(buf)

    sock._buf[:10] = b"a" * 10

    def dummpy_filter(buf):
        if buf[:10] != b"a" * 10:
            return False
        return True

    sock.add_filter(dummpy_filter)
    assert sock._check_filter()

    def dummpy_filter_plus(buf):
        if buf[-10:] != b"a" * 10:
            return False
        return True

    sock.add_filter(dummpy_filter_plus)
    assert not sock._check_filter()
    buf[-10:] = b"a" * 10

    sock.add_filter(sock.filter_non_ipv4)
    struct.pack_into(">H", buf, 12, ETH_PROTO_IPV4)
    assert sock._check_filter()

    dur = timeit.repeat(setup=sock._check_filter, repeat=17)
    logger.debug(f"Maximal duration for filtering: {max(dur) * 1000.0} ms")

    dur = timeit.repeat(setup=sock._calc_cksum, repeat=17)
    logger.debug(
        f"Maximal duration for IP checksum calculation: {max(dur) * 1000.0} ms"
    )

    sock.close()
    logger.info("* Tests finish successfully.")
