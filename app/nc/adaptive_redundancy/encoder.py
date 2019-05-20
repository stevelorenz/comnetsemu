#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
"""
About: Full vector NC encoder
"""

import argparse
import kodo
import socket
import struct
import time
from multiprocessing import Process, active_children

import common
import rawsock_helpers as rsh
import log
from common import (BUFFER_SIZE, FIELD, IO_SLEEP, META_DATA_LEN, MTU,
                    SYMBOL_SIZE, SYMBOLS)

log.conf_logger("info")
logger = log.logger


def io_loop(sock):
    """Main IO loop"""

    rx_tx_buf = bytearray(BUFFER_SIZE)
    rank = 0
    generation = 0
    redundancy = 1  # Should be tuned by SDN controller
    udp_cnt = 0

    logger.info("Init kodo encoder...\n")
    # Create an encoder factory that are used to build the actual encoders
    encoder_factory = kodo.RLNCEncoderFactory(FIELD, SYMBOLS, SYMBOL_SIZE)
    encoder = encoder_factory.build()
    encode_buf = bytearray(encoder.block_size())
    # Use systematic encoding
    encoder.set_systematic_on()

    logger.info("Entering IO loop.")

    while True:
        time.sleep(IO_SLEEP)
        rx_tx_buf = bytearray(BUFFER_SIZE)
        ret = rsh.recv_ipv4(sock, rx_tx_buf, MTU)
        if not ret:
            logger.debug("Recv a non-IPv4 frame, frame is ignored.")
            continue
        frame_len, ip_hd_offset, ip_hd_len, proto = ret

        if proto == rsh.IP_PROTO_TCP:
            logger.info("Recv a TCP segment")
            rsh.encap_tcp_udp(rx_tx_buf, ip_hd_offset, ip_hd_len)
            frame_len += rsh.UDP_HDL  # Encap UDP header
        elif proto == rsh.IP_PROTO_UDP:
            udp_cnt += 1
            logger.info(
                "Recv a UDP segment, total received UDP segments: %d "
                "frame len: %d",
                udp_cnt, frame_len)
        else:
            logger.debug("Recv a non-UDP and non-TCP segment.")
            continue

        # RX/TX buf only contains UDP segments
        udp_hd_offset, udp_pl_offset, udp_pl_len = rsh.parse_udp(rx_tx_buf,
                                                                 ip_hd_offset,
                                                                 ip_hd_len)
        logger.debug("UDP header offset:%d, pl_offset:%d, pl_len:%d", udp_hd_offset,
                     udp_pl_offset, udp_pl_len)

        rank = encoder.rank()
        # Copy UDP payload into encoder's encode buffer
        encode_buf[rank*SYMBOL_SIZE:(rank+1)*SYMBOL_SIZE] = rx_tx_buf[
            udp_pl_offset:udp_pl_offset+udp_pl_len]

        # WARN: The set_const_symbol REQUIRES a COPY of the mutable bytearray
        # Feed a slice of the mutable rx_tx_buf leads to WRONG encoder output
        tmp_copy = encode_buf[rank*SYMBOL_SIZE:(rank+1)*SYMBOL_SIZE]
        encoder.set_const_symbol(rank, tmp_copy)

        # Update rank of the encoder
        rank = encoder.rank()

        if rank < SYMBOLS:
            send_num = 1
        else:
            # Encoder has already full rank
            # Send redundant packet(s) and increase generation number
            logger.debug("Send %d redundant coded packet", send_num)
            send_num = 1 + redundancy

        logger.debug("Generation number %d, rank: %d, send_num:%d",
                     generation, rank, send_num)

        for _ in range(send_num):
            enc_out = encoder.write_payload()
            # Reserve space for metadata
            rx_tx_buf[udp_pl_offset+META_DATA_LEN:] = enc_out[:]
            logger.debug("[ENC OUT] length: %d, frame_len:%d, udp_pl_len:%d",
                         len(enc_out), frame_len, udp_pl_len)
            frame_len = frame_len + (len(enc_out) - udp_pl_len) + META_DATA_LEN
            common.push_metadata(rx_tx_buf, udp_pl_offset, (common.MD_TYPE_DATA,
                                                            generation))
            # Update IP/UDP header total length domain
            udp_total_len = rsh.UDP_HDL + META_DATA_LEN + len(enc_out)
            ip_total_len = udp_total_len + ip_hd_len
            rsh.update_ip_udp_len(rx_tx_buf, ip_hd_offset, udp_hd_offset,
                                  ip_total_len, udp_total_len)

            # Disable UDP checksum
            struct.pack_into(">H", rx_tx_buf, udp_hd_offset+6, 0)
            rsh.update_cksum_ipv4(rx_tx_buf, ip_hd_offset, ip_hd_len)
            sock.send(rx_tx_buf[:frame_len])

        # Cleanup old encoder and go to next generation
        if rank == SYMBOLS:
            logger.debug("Encoder has full rank, coded packets already sent,"
                         "cleanup encoder and increase generation")
            encoder = encoder_factory.build()
            assert(encoder.rank() == 0)
            encode_buf = bytearray(encoder.block_size())
            encoder.set_systematic_on()
            generation += 1


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("ifce",
                        help="The name of interface for recv and send frames",
                        type=str)
    args = parser.parse_args()

    ifce = args.ifce

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

    io_proc = Process(target=io_loop, args=(sock,))
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
