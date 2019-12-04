#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
"""
About: On the Fly NC Encoder
"""

import argparse
import kodo
import socket
import struct
import time

import common
import log
import rawsock_helpers as rsh
from common import (BUFFER_SIZE, FIELD, IO_SLEEP, MD_TYPE_TCP_IN_UDP,
                    MD_TYPE_UDP, META_DATA_LEN, MTU, SYMBOL_SIZE, SYMBOLS,
                    UDP_PORT_DATA, UDP_PORT_OAM)

log.conf_logger("info")
logger = log.logger


def run_encoder():

    rx_tx_buf = bytearray(BUFFER_SIZE)
    udp_cnt = 0

    rank = 0
    generation = 0
    redundancy = int(SYMBOLS / 2)  # Should be tuned by SDN controller

    logger.info("Create a raw packet socket.\n")
    try:
        # The protocol number 3 means receive all types of Ethernet frames.
        sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW,
                             socket.htons(3))
    except socket.error as error:
        raise error

    logger.info("Bind the socket to the interface: {}".format(ifce))
    sock.bind((ifce, 0))

    logger.info("Init kodo encoder...\n")
    # Create an encoder factory that are used to build the actual encoders
    encoder_factory = kodo.RLNCEncoderFactory(
        FIELD, SYMBOLS, SYMBOL_SIZE)
    encoder = encoder_factory.build()
    symbol_storage = [b""] * SYMBOLS
    # Use systematic encoding
    encoder.set_systematic_on()

    logger.info("Entering IO loop.")
    while True:
        time.sleep(IO_SLEEP)

        ret = rsh.recv_ipv4(sock, rx_tx_buf, MTU)
        if not ret:
            logger.debug("Recv a non-IPv4 frame, frame is ignored.")
            continue

        frame_len, ip_hd_offset, ip_hd_len, proto = ret

        if proto == rsh.IP_PROTO_TCP:
            logger.info("Recv a TCP segment")
            md_type = MD_TYPE_TCP_IN_UDP
            md_pl_len = rsh.encap_tcp_udp(rx_tx_buf, ip_hd_offset, ip_hd_len)
            frame_len += rsh.UDP_HDL
            udp_hd_offset, udp_dst_port, udp_pl_offset, udp_pl_len = rsh.parse_udp(
                rx_tx_buf, ip_hd_offset, ip_hd_len)

        elif proto == rsh.IP_PROTO_UDP:
            udp_cnt += 1
            md_type = MD_TYPE_UDP
            logger.debug(
                "Recv a UDP segment, total received UDP segments: %d "
                "frame len: %d",
                udp_cnt, frame_len)

            udp_hd_offset, udp_dst_port, udp_pl_offset, udp_pl_len = rsh.parse_udp(
                rx_tx_buf, ip_hd_offset, ip_hd_len)
            md_pl_len = udp_pl_len
            assert(md_pl_len < SYMBOL_SIZE)

            if udp_dst_port == UDP_PORT_OAM:
                redundancy = struct.unpack_from(
                    ">i", rx_tx_buf, udp_pl_offset)[0]
                logger.info("Recv an OAM packet, update redundancy to %d",
                            redundancy)
                continue
            elif udp_dst_port == UDP_PORT_DATA:
                pass
            else:
                logger.error("Invalid UDP port, ignore the segment.")
                continue

        else:
            logger.debug("Recv a non-UDP and non-TCP segment.")
            continue

        logger.debug("UDP header offset:%d, pl_offset:%d, pl_len:%d", udp_hd_offset,
                     udp_pl_offset, udp_pl_len)

        rank = encoder.rank()
        symbol_storage[rank] = rx_tx_buf[
            udp_pl_offset:udp_pl_offset+udp_pl_len]

        # Padding zeros
        symbol_storage[rank].extend(b"0" * (SYMBOL_SIZE-udp_pl_len))
        encoder.set_const_symbol(rank, symbol_storage[rank])
        # Update rank of the encoder
        rank = encoder.rank()

        if rank < SYMBOLS:
            send_num = 1
        else:
            # Encoder has already full rank
            # Send redundant packet(s) and increase generation number
            logger.debug("Send %d redundant coded packet", send_num)
            send_num = 1 + redundancy

        logger.debug("Generation number %d, rank: %d/%d, send_num:%d",
                     generation, rank, SYMBOLS, send_num)

        for _ in range(send_num):
            enc_out = encoder.write_payload()
            rx_tx_buf[
                udp_pl_offset+META_DATA_LEN:udp_pl_offset + META_DATA_LEN+len(enc_out)
            ] = enc_out[:]
            frame_len = frame_len + (len(enc_out) - udp_pl_len) + META_DATA_LEN
            logger.debug(
                "Encoder output: output len: %d, UDP payload length:%d",
                len(enc_out), udp_pl_len
            )
            common.push_metadata(rx_tx_buf, udp_pl_offset,
                                 (md_type, generation, md_pl_len))
            # Update IP/UDP header total length domain
            udp_total_len = rsh.UDP_HDL + META_DATA_LEN + len(enc_out)
            ip_total_len = udp_total_len + ip_hd_len
            rsh.update_ip_udp_len(rx_tx_buf, ip_hd_offset, udp_hd_offset,
                                  ip_total_len, udp_total_len)

            # Update header checksum
            # UDP checksum is disabled to reduce computation
            struct.pack_into(">H", rx_tx_buf, udp_hd_offset+6, 0)
            rsh.update_cksum_ipv4(rx_tx_buf, ip_hd_offset, ip_hd_len)
            sock.send(rx_tx_buf[:frame_len])

        # Cleanup old encoder and go to next generation
        if rank == SYMBOLS:
            logger.debug("Encoder has full rank, coded packets already sent,"
                         "cleanup encoder and increase generation")
            encoder = encoder_factory.build()
            assert(encoder.rank() == 0)
            encoder.set_systematic_on()
            if generation < 255:
                generation += 1
            else:
                generation = 0


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Full vector NC encoder")
    parser.add_argument("ifce", type=str,
                        help="The name of interface for receive and send frames")
    args = parser.parse_args()
    ifce = args.ifce

    run_encoder()
