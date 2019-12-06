#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
"""
About: On the Fly NC Decoder.
"""

import argparse
import kodo
import socket
import struct
import time

import common
import log
import rawsock_helpers as rsh
from common import (
    BUFFER_SIZE,
    CODER_LOG_LEVEL,
    FIELD,
    IO_SLEEP,
    MD_TYPE_UDP,
    META_DATA_LEN,
    MTU,
    SYMBOL_SIZE,
    SYMBOLS,
)

log.conf_logger(CODER_LOG_LEVEL)
logger = log.logger


def run_decoder(ifce):
    """Main IO loop"""

    buf = bytearray(BUFFER_SIZE)
    generation = 0
    udp_cnt = 0

    try:
        logger.info("Create the raw packet socket.")
        sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
    except socket.error as error:
        raise error

    logger.info("Bind the socket to the interface: {}".format(ifce))
    sock.bind((ifce, 0))

    logger.info("Init kodo decoder.")
    # Create an encoder factory that are used to build the actual encoders
    decoder_factory = kodo.RLNCDecoderFactory(FIELD, SYMBOLS, SYMBOL_SIZE)
    decoder = decoder_factory.build()
    # Mutable bytearray to store decoded symbols from decoder.
    decode_buf = bytearray(decoder.block_size())
    decoder.set_mutable_symbols(decode_buf)
    not_decoded_indces = list(range(decoder.symbols()))

    logger.info("Entering IO loop.")

    while True:
        time.sleep(IO_SLEEP)
        ret = rsh.recv_ipv4(sock, buf, MTU)
        if not ret:
            logger.debug("Recv a non-IPv4 frame, frame is ignored.")
            continue
        frame_len, ip_hd_offset, ip_hd_len, proto = ret

        if proto == rsh.IP_PROTO_UDP:
            udp_cnt += 1
            logger.debug(
                "Recv a UDP segment, total received UDP segments: %d " "frame len: %d",
                udp_cnt,
                frame_len,
            )
        else:
            logger.debug("Recv a non-UDP segment. Ignore it.")
            continue

        # Only handle UDP segments
        udp_hd_offset, _, udp_pl_offset, udp_pl_len = rsh.parse_udp(
            buf, ip_hd_offset, ip_hd_len
        )

        _type, cur_gen, md_pl_len = common.pull_metadata(buf, udp_pl_offset)
        logger.debug(
            "Generation number in payload: %d, current decode generation: %d, md_pl_len: %d",
            cur_gen,
            generation,
            md_pl_len,
        )

        if cur_gen > generation:
            logger.debug("Cleanup decoder for a new generation.")
            decoder = decoder_factory.build()
            decode_buf = bytearray(decoder.block_size())
            decoder.set_mutable_symbols(decode_buf)
            not_decoded_indces = list(range(decoder.symbols()))
            generation = cur_gen

        elif cur_gen == 0 and generation == 255:
            logger.debug("Cleanup decoder for a new interation.")
            decoder = decoder_factory.build()
            decode_buf = bytearray(decoder.block_size())
            decoder.set_mutable_symbols(decode_buf)
            not_decoded_indces = list(range(decoder.symbols()))
            generation = 0

        head = udp_pl_offset + META_DATA_LEN
        tail = udp_pl_offset + META_DATA_LEN + udp_pl_len
        decoder.read_payload(buf[head:tail])
        logger.debug(
            "Decode rank: %d/%d, coded symbol len: %d",
            decoder.rank(),
            decoder.symbols(),
            udp_pl_offset,
        )

        # Loop over un-decoded symbols
        for i in not_decoded_indces:
            if decoder.is_symbol_uncoded(i):
                del not_decoded_indces[not_decoded_indces.index(i)]
                logger.debug(
                    "Decoder symbol: %d, not_decoded_symbols_indces: %s",
                    i,
                    ",".join(map(str, not_decoded_indces)),
                )

                if _type == MD_TYPE_UDP:
                    buf[udp_pl_offset : udp_pl_offset + md_pl_len] = decode_buf[
                        i * SYMBOL_SIZE : i * SYMBOL_SIZE + md_pl_len
                    ]
                    udp_total_len = rsh.UDP_HDL + md_pl_len
                    ip_total_len = udp_total_len + ip_hd_len
                    frame_len = ip_total_len + rsh.ETH_HDL
                    logger.debug(
                        "[Decoder TX] UDP total len: %d, ip_total_len: %d",
                        udp_total_len,
                        ip_total_len,
                    )
                    rsh.update_ip_udp_len(
                        buf, ip_hd_offset, udp_hd_offset, ip_total_len, udp_total_len
                    )
                    struct.pack_into(">H", buf, udp_hd_offset + 6, 0)
                    rsh.update_cksum_ipv4(buf, ip_hd_offset, ip_hd_len)
                    sock.send(buf[:frame_len])


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "ifce", help="The name of interface for recv and send frames.", type=str
    )
    args = parser.parse_args()

    run_decoder(args.ifce)
