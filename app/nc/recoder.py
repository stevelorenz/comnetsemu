#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
"""
About: Full vector NC recoder
"""

import argparse
import binascii
import kodo
import logging
import socket
import struct
import time
from multiprocessing import Process, active_children

import rawsock_helpers
import common
from common import (BUFFER_SIZE, IO_SLEEP, META_DATA_LEN, MTU,
                    FIELD, SYMBOLS, SYMBOL_SIZE)

# Configure logger
logger = logging.getLogger("nc_coder")
fmt_str = "%(asctime)s %(levelname)-8s %(processName)s %(message)s"
level = {"INFO": logging.INFO, "DEBUG": logging.DEBUG, "ERROR": logging.ERROR}

handler = logging.StreamHandler()
formatter = logging.Formatter(fmt_str)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(level["INFO"])


def io_loop(sock, action, dst_mac):
    """Main IO loop"""

    rx_tx_buf = bytearray(BUFFER_SIZE)
    udp_cnt = 0
    generation = 0

    if action == "recode":
        logger.info("Init kodo recoder...\n")
        decoder_factory = kodo.RLNCDecoderFactory(FIELD, SYMBOLS, SYMBOL_SIZE)
        recoder = decoder_factory.build()
        decode_buf = bytearray(recoder.block_size())
        recoder.set_mutable_symbols(decode_buf)
        recode_buf = bytearray(BUFFER_SIZE)
        redundancy = 1  # Should be tuned by SDN controller

    logger.info("Entering IO loop.")

    while True:
        time.sleep(IO_SLEEP)

        ret = rawsock_helpers.rx_buf_udp(sock, rx_tx_buf, MTU)
        if not ret:
            logger.debug("Recv a non-UDP frame, frame is dropped.")
            continue
        else:
            udp_cnt += 1
            logger.info(
                "Recv a UDP segment! Total UDP count: {}".format(udp_cnt))
        frame_len, ip_hd_offset, ip_hd_len, udp_pl_offset, udp_pl_len = ret

        # Handle OAM packet
        _type, cur_gen = common.pull_metadata(rx_tx_buf, udp_pl_offset)

        if _type == common.MD_TYPE_OAM:
            redundancy = struct.unpack_from(">B", rx_tx_buf, udp_pl_offset)[0]
            logger.info(
                "Recv a OAM packet, update redundancy number to %d", redundancy)
            continue

        # Update the dst MAC address if is required
        if dst_mac != "":
            logger.debug("Update the destination MAC to: {}".format(dst_mac))
            dst_mac_b = binascii.unhexlify(dst_mac.replace(":", ""))
            rx_tx_buf[0:len(dst_mac_b)] = dst_mac_b

        if action == "recode":
            # recode and forward
            sock.send(rx_tx_buf[:frame_len])

            logger.info(
                "Generation number in packet {}, last generation number {}.".
                format(cur_gen, generation))
            if cur_gen > generation:
                generation = cur_gen
                # Cleanup the old recoder
                recoder = decoder_factory.build()
                decode_buf = bytearray(recoder.block_size())
                recoder.set_mutable_symbols(decode_buf)

            head = udp_pl_offset + META_DATA_LEN
            tail = udp_pl_offset + META_DATA_LEN + udp_pl_len
            # Only feed payload into recoder
            recoder.read_payload(rx_tx_buf[head:tail])
            # Generate recoded packets
            for _ in range(redundancy):
                recode_buf = recoder.write_payload()
                rx_tx_buf[head:tail] = recode_buf[:udp_pl_len]
                # Update IP/UDP checksum
                rawsock_helpers.update_cksum_udp(rx_tx_buf, ip_hd_offset,
                                                 ip_hd_len)
                sock.send(rx_tx_buf[:frame_len])

        elif action == "forward":
            # store and forward
            sock.send(rx_tx_buf[:frame_len])


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("ifce",
                        help="The name of interface for recv and send frames",
                        type=str)
    parser.add_argument("--dst_mac",
                        help="The destination MAC address of the output frame",
                        type=str, default=" ")
    parser.add_argument("--action",
                        help="The action of the recoder",
                        choices=["forward", "recode"],
                        type=str,
                        default="forward")
    args = parser.parse_args()

    ifce = args.ifce
    dst_mac = args.dst_mac.strip()
    action = args.action

    try:
        logger.info("Create a raw socket\n")
        # Create a raw socket to recv and send packets, the protocol number 3
        # means receive all types of Ethernet frames.
        sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW,
                             socket.htons(3))
    except socket.error as error:
        raise error

    logger.info("Bind the socket to the interface: {}".format(ifce))
    sock.bind((ifce, 0))

    io_proc = Process(target=io_loop, args=(sock, action, dst_mac))
    io_proc.start()

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt detected, exit.")
        logger.info("Kill all sub-processes.")
        for proc in active_children():
            proc.terminate()
    finally:
        logger.info("Free resources")
        sock.close()
