# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
from typing import Dict, List, Tuple

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3, ether
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import udp, ipv4, arp


class Controller(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Controller, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.eth_to_ip = {}
        self.latency = ({}, {})  # first is direct, second application traffic
        self.time: Tuple[float, float] = (0.0, 0.0)  # first is direct, second application traffic
        self.msg_cnt = 0

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):  # avoid triggering this for server -> client
        self.msg_cnt += 1
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)

        eth = pkt.get_protocols(ethernet.ethernet)[0]
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst = eth.dst
        src = eth.src

        try:
            ip = pkt.protocols[1]
            ip_dst = ip.dst
            ip_src = ip.src
            self.eth_to_ip.update({dst: ip_dst})
            self.eth_to_ip.update({src: ip_src})
        except Exception:
            ip_dst = "none"
            ip_src = "none"

        # self.logger.info(f"\ndst {dst} {ip_dst} src {src} {ip_src} cnt {self.msg_cnt}")
        # self.logger.info(f"dict {self.eth_to_ip}")

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        flag = False
        from_client = False

        if ip_src == "10.0.0.10":  # udp out, arp out
            from_client = True
            # self.time = (self.time[0], time.time())
            # self.logger.info(f"time[1] updated : {self.time}")
            self.logger.critical(f"")  # optical padding
            # send arp probe to all servers
            for key, value in self.mac_to_port[dpid].items():
                if key != "00:00:00:00:00:01":
                    # self.logger.info(f"key : {key}, value : {value}, ip : {self.eth_to_ip.get(key)}")
                    probe_packet = packet.Packet()
                    probe_packet.add_protocol(ethernet.ethernet(dst='ff:ff:ff:ff:ff:ff',
                                                                src='00:00:00:00:00:01',
                                                                ethertype=ether.ETH_TYPE_ARP))
                    probe_packet.add_protocol(arp.arp(hwtype=1, proto=0x0800, hlen=6, plen=4, opcode=1,
                                                      src_mac='00:00:00:00:00:01', src_ip='10.0.0.10',
                                                      dst_mac='00:00:00:00:00:00', dst_ip=self.eth_to_ip.get(key)))
                    probe_packet.serialize()
                    # self.logger.debug(probe_packet.__repr__())
                    out = parser.OFPPacketOut(datapath=datapath,
                                              buffer_id=msg.buffer_id,
                                              in_port=in_port,
                                              actions=[parser.OFPActionOutput(value)],
                                              data=probe_packet.data)
                    datapath.send_msg(out)
                    self.time = (time.time(), self.time[1])
                    # self.logger.info(f"probe packet sent, time[0] updated : {self.time}")
                    self.logger.critical(f"ARP_OUT,{self.msg_cnt},{self.eth_to_ip.get(key)},{key},{value},{self.time[0]},0")
                    del out
                    del probe_packet

        if ip_dst == "10.0.0.10":  # udp in
            latency: float = (time.time() - self.time[1]) * 1e3
            self.latency[1].update({src: latency})
            # self.logger.info(f"updated entry[1] : {src} ; {latency} msec")
            self.logger.critical(f"UDP_IN,{self.msg_cnt},{ip_src},{src},0,0,{latency}")

        if ip_dst == "none" and dst == "00:00:00:00:00:01":  # arp in
            latency: float = (time.time() - self.time[0]) * 1e3
            self.latency[0].update({src: latency})
            # self.logger.info(f"updated entry[0] : {src} ; {latency} msec")
            if latency < 150.0:  # remove waste packets
                self.logger.critical(f"ARP_IN,{self.msg_cnt},0,{src},0,0,{latency}")
            if self.msg_cnt > 50:
                return  # pass probe packet

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port
        # self.logger.info(f"port in {in_port} {dpid} {src}")

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
            # self.logger.debug(f"out port {out_port}")
            if ip_dst != "10.0.0.10":  # flood servers, not client
                # self.logger.info("flood")
                out_port = ofproto.OFPP_FLOOD
        else:
            # self.logger.info("flood")
            out_port = ofproto.OFPP_FLOOD

        # out_port = ofproto.OFPP_FLOOD
        actions = [parser.OFPActionOutput(out_port)]

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        if flag:  # only for rewrite
            pkt.serialize()
            self.logger.info(f"new packet {pkt.__repr__()}")
            out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                      in_port=in_port, actions=actions, data=pkt.data)
            datapath.send_msg(out)
        elif not flag:
            # self.logger.debug(f"packet out\nport dict {self.mac_to_port}")
            out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                      in_port=in_port, actions=actions, data=data)
            datapath.send_msg(out)
            if from_client:
                self.time = (self.time[0], time.time())
                # self.logger.info(f"time[1] updated : {self.time}")
                self.logger.critical(f"UDP_OUT,{self.msg_cnt},{ip_src},{src},0,{self.time[1]},0")
