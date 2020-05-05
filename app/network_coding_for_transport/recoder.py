#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
"""
About: NC Recoder.
"""

import argparse
import binascii
import socket
import struct
import time

import common
import kodo
import log
import rawsock_helpers as rsh
from common import (
    BUFFER_SIZE,
    CODER_LOG_LEVEL,
    FIELD,
    INIT_REDUNDANCY,
    IO_SLEEP,
    META_DATA_LEN,
    MTU,
    SYMBOL_SIZE,
    SYMBOLS,
    UDP_PORT_DATA,
    UDP_PORT_OAM,
)

log.conf_logger(CODER_LOG_LEVEL)
logger = log.logger


def run_recoder(ifce, action, dst_mac):

    buf = bytearray(BUFFER_SIZE)
    udp_cnt = 0

    if dst_mac:
        logger.info(
            "The destination MAC address of all frames are changed to %s" % dst_mac
        )

    try:
        logger.info("Create the raw packet socket.")
        # Create a raw socket to recv and send packets, the protocol number 3
        # means receive all types of Ethernet frames.
        sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
    except socket.error as error:
        raise error

    logger.info("Bind the socket to the interface: {}".format(ifce))
    sock.bind((ifce, 0))

    if action == "recode":
        logger.info("Init kodo recoder.")
        recoder_factory = kodo.RLNCPureRecoderFactory(FIELD, SYMBOLS, SYMBOL_SIZE)
        recoder = recoder_factory.build()
        # decode_buf = bytearray(recoder.block_size())
        # recoder.set_mutable_symbols(decode_buf)
        recode_buf = bytearray(BUFFER_SIZE)
        generation = 0
        redundancy = INIT_REDUNDANCY

    logger.info("Entering IO loop.")

    while True:
        time.sleep(IO_SLEEP)
        ret = rsh.recv_ipv4(sock, buf, MTU)

        if not ret:
            logger.debug("Recv a non-IPv4 frame, frame is ignored.")
            continue
        frame_len, ip_hd_offset, ip_hd_len, ip_proto = ret

        if ip_proto != rsh.IP_PROTO_UDP:
            logger.debug("Recv a non-UDP segment, packet is ignored.")
            continue
        else:
            udp_cnt += 1
            logger.info("Recv a UDP segment! Total UDP count: {}".format(udp_cnt))

        ret = rsh.parse_udp(buf, ip_hd_offset, ip_hd_len)
        _, udp_dst_port, udp_pl_offset, udp_pl_len = ret

        if udp_dst_port == UDP_PORT_OAM:
            redundancy = struct.unpack_from(">B", buf, udp_pl_offset)[0]
            logger.info("Recv an OAM packet, update redundancy to %d", redundancy)
            continue
        elif udp_dst_port == UDP_PORT_DATA:
            pass
        else:
            logger.error("Invalid UDP port, ignore the segment.")
            continue

        # Update the dst MAC address if is required
        if dst_mac != "":
            logger.debug("Update the destination MAC to: {}".format(dst_mac))
            dst_mac_b = binascii.unhexlify(dst_mac.replace(":", ""))
            buf[0 : len(dst_mac_b)] = dst_mac_b

        # Store and forward
        if action == "forward":
            sock.send(buf[:frame_len])
            continue

        # Compute (recode) and forward
        _, cur_gen, md_pl_len = common.pull_metadata(buf, udp_pl_offset)
        # Disable UDP checksum
        udp_hd_offset = ip_hd_offset + ip_hd_len
        struct.pack_into(">H", buf, udp_hd_offset + 6, 0)

        sock.send(buf[:frame_len])
        logger.info(
            "Generation number in packet {}, last generation number {}.".format(
                cur_gen, generation
            )
        )
        if cur_gen > generation:
            generation = cur_gen
            # Cleanup the old recoder for a new generation.
            recoder = recoder_factory.build()
            # decode_buf = bytearray(recoder.block_size())
            # recoder.set_mutable_symbols(decode_buf)

        # Feed UDP payload into recoder
        head = udp_pl_offset + META_DATA_LEN
        tail = udp_pl_offset + META_DATA_LEN + udp_pl_len
        recoder.read_payload(buf[head:tail])

        # Generate recoded packets, plus one is for the original packet.
        for i in range(redundancy + 1):
            recode_buf = recoder.write_payload()
            buf[head:tail] = recode_buf[:udp_pl_len]
            # Update IP header checksum
            rsh.update_cksum_ipv4(buf, ip_hd_offset, ip_hd_len)
            sock.send(buf[:frame_len])


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "ifce", help="The name of interface for recv and send frames", type=str
    )
    parser.add_argument(
        "--dst_mac",
        help="The destination MAC address of the output frame",
        type=str,
        default=" ",
    )
    parser.add_argument(
        "--action",
        help="The action of the recoder",
        choices=["forward", "recode"],
        type=str,
        default="forward",
    )
    args = parser.parse_args()

    run_recoder(args.ifce, args.action, args.dst_mac.strip())
