#!/usr/bin/env python2
# -*- coding: utf-8 -*-
##################################################
# GNU Radio Python Flow Graph
# Title: Rx Ofdm
# GNU Radio version: 3.7.13.5
##################################################

from gnuradio import blocks
from gnuradio import digital
from gnuradio import eng_notation
from gnuradio import filter
from gnuradio import gr
from gnuradio import uhd
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from optparse import OptionParser
import time


class rx_ofdm(gr.top_block):
    def __init__(self):
        gr.top_block.__init__(self, "Rx Ofdm")

        ##################################################
        # Variables
        ##################################################
        self.tx_gain = tx_gain = 60
        self.samp_rate = samp_rate = 500e3
        self.packet_len = packet_len = 60
        self.len_tag_key = len_tag_key = "packet_len"
        self.freq = freq = 2.4e9
        self.fft_len = fft_len = 120

        ##################################################
        # Blocks
        ##################################################
        self.uhd_usrp_source_0 = uhd.usrp_source(
            ",".join(("addr=192.168.10.2", "")),
            uhd.stream_args(cpu_format="fc32", channels=range(1)),
        )
        self.uhd_usrp_source_0.set_samp_rate(samp_rate)
        self.uhd_usrp_source_0.set_center_freq(2.4e9, 0)
        self.uhd_usrp_source_0.set_gain(0, 0)
        self.uhd_usrp_source_0.set_antenna("RX2", 0)
        self.uhd_usrp_source_0.set_auto_dc_offset(True, 0)
        self.uhd_usrp_source_0.set_auto_iq_balance(True, 0)
        self.rational_resampler_xxx_0_0 = filter.rational_resampler_ccc(
            interpolation=1, decimation=2, taps=None, fractional_bw=None
        )
        self.digital_ofdm_rx_0 = digital.ofdm_rx(
            fft_len=fft_len,
            cp_len=32,
            frame_length_tag_key="frame_" + len_tag_key,
            packet_length_tag_key=len_tag_key,
            bps_header=1,
            bps_payload=2,
            debug_log=False,
            scramble_bits=False,
        )
        self.blocks_tag_debug_0_0 = blocks.tag_debug(gr.sizeof_char * 1, "", "")
        self.blocks_tag_debug_0_0.set_display(True)
        self.blocks_file_sink_0 = blocks.file_sink(
            gr.sizeof_char * 1, "/home/GNURadio-Files/file_rx.txt", True
        )
        self.blocks_file_sink_0.set_unbuffered(True)

        ##################################################
        # Connections
        ##################################################
        self.connect((self.digital_ofdm_rx_0, 0), (self.blocks_file_sink_0, 0))
        self.connect((self.digital_ofdm_rx_0, 0), (self.blocks_tag_debug_0_0, 0))
        self.connect((self.rational_resampler_xxx_0_0, 0), (self.digital_ofdm_rx_0, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.rational_resampler_xxx_0_0, 0))

    def get_tx_gain(self):
        return self.tx_gain

    def set_tx_gain(self, tx_gain):
        self.tx_gain = tx_gain

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.uhd_usrp_source_0.set_samp_rate(self.samp_rate)

    def get_packet_len(self):
        return self.packet_len

    def set_packet_len(self, packet_len):
        self.packet_len = packet_len

    def get_len_tag_key(self):
        return self.len_tag_key

    def set_len_tag_key(self, len_tag_key):
        self.len_tag_key = len_tag_key

    def get_freq(self):
        return self.freq

    def set_freq(self, freq):
        self.freq = freq

    def get_fft_len(self):
        return self.fft_len

    def set_fft_len(self, fft_len):
        self.fft_len = fft_len


def main(top_block_cls=rx_ofdm, options=None):

    tb = top_block_cls()
    tb.start()
    try:
        raw_input("Press Enter to quit: ")
    except EOFError:
        pass
    tb.stop()
    tb.wait()


if __name__ == "__main__":
    main()
