#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Full vector NC decoder
"""

import kodo
import os
import socket
import struct
import sys

from common import (BUFFER_SIZE, FIELD, IO_SLEEP, META_DATA_LEN, MTU,
                    SYMBOL_SIZE, SYMBOLS)
import common

# Number of generations
generation = 3


def main():

    if len(sys.argv) > 1:
        server_addr = sys.argv[1]
        server_ip, server_port = server_addr.split(":")[:2]
        server_port = int(server_port)
    else:
        server_ip = "127.0.0.1"
        server_port = 8888

    rx_tx_buf = bytearray(BUFFER_SIZE)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((server_ip, server_port))

    decoder_factory = kodo.RLNCDecoderFactory(FIELD, SYMBOLS, SYMBOL_SIZE)

    # Already decoded generation number
    packet_number = 0
    for g in range(generation):
        # Cleanup decoder
        decoder = decoder_factory.build()
        # Define the data_out bytearray where the symbols should be decoded
        data_out = bytearray(decoder.block_size())
        decoder.set_mutable_symbols(data_out)

        while not decoder.is_complete():
            payload_len = sock.recv_into(rx_tx_buf, 0)
            _, cur_gen = common.pull_metadata(rx_tx_buf, 0)
            if cur_gen != g:
                packet_number += 1
                # Drop redundant packets of already-decoded generation
                continue
            decoder.read_payload(rx_tx_buf[META_DATA_LEN:payload_len])
            print("Packet {} is feed into decoder.".format(packet_number))
            print("Current generation number: {}".format(cur_gen))
            print("Decoder rank: {}/{}".format(
                decoder.rank(), decoder.symbols()))
            packet_number += 1

    print("Decoder will exit.")

    sock.close()


if __name__ == "__main__":
    main()
