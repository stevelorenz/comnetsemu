import time
from typing import Tuple, Dict

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

    # def print_dict(self, dictonary: Dict = None):
    #     if dictonary is not None:
    #         for key, value in dictonary:
    #             self.logger.info(f"{key}, {value}")

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

        # get eth info
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return
        eth_dst = eth.dst
        eth_src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][eth_src] = in_port
        # self.logger.info(f"port in {in_port} {dpid} {eth_src}")

        # check packet type
        _udp = False
        _arp = False
        protocols = pkt.protocols
        for p in protocols:
            if isinstance(p, udp.udp):
                _udp = True
            elif isinstance(p, arp.arp):
                _arp = True

        # handle arp packet
        if _arp:
            # self.logger.info(f"\nARP : dst {eth_dst} src {eth_src} cnt {self.msg_cnt}")
            # self.logger.info(f"dict {self.eth_to_ip}")
            # update latency if from serv
            if eth_dst == "00:00:00:00:01:ff":
                latency: float = (time.time() - self.time[0]) * 1e3
                self.latency[0].update({eth_src: latency})
                # self.logger.info(f"updated entry[0] : {eth_src} ; {latency} msec")
                # self.logger.critical(f"ARP_IN,{self.msg_cnt},0,{eth_src},0,0,{latency}")

        # handle udp packet
        elif _udp:
            try:
                ip = pkt.protocols[1]
                ip_dst = ip.dst
                ip_src = ip.src
                self.eth_to_ip.update({eth_dst: ip_dst})
                self.eth_to_ip.update({eth_src: ip_src})
            except Exception:
                ip_dst = "none"
                ip_src = "none"
            # self.logger.info(f"\nUDP : dst {eth_dst} {ip_dst} src {eth_src} {ip_src} cnt {self.msg_cnt}")
            # self.logger.info(f"dict {self.eth_to_ip}")

            if ip_src == "10.0.0.40":
                for key, value in self.mac_to_port[dpid].items():  # send arp probe to all servers
                    if key != "00:00:00:00:00:01" and key != "ff:ff:ff:ff:ff:ff" and key != "00:00:00:00:01:ff":
                        try:
                            # self.logger.info(f"Crafting ARP Packet : key {key}, value {value}, ip {self.eth_to_ip.get(key)}")
                            probe_packet = packet.Packet()
                            addr = self.eth_to_ip.get(key)
                            if addr is None:
                                if key == "00:00:00:00:01:01":
                                    addr = "10.0.0.21"
                                elif key == "00:00:00:00:01:02":
                                    addr = "10.0.0.22"
                                else:
                                    raise
                            probe_packet.add_protocol(ethernet.ethernet(dst='ff:ff:ff:ff:ff:ff',
                                                                        src='00:00:00:00:01:ff',
                                                                        ethertype=ether.ETH_TYPE_ARP))
                            probe_packet.add_protocol(arp.arp(hwtype=1, proto=0x0800, hlen=6, plen=4, opcode=1,
                                                              src_mac='00:00:00:00:01:ff', src_ip='10.0.0.40',
                                                              dst_mac='00:00:00:00:00:00', dst_ip=addr))
                            probe_packet.serialize()
                            # self.logger.debug(probe_packet.__repr__())
                            out = parser.OFPPacketOut(datapath=datapath,
                                                      buffer_id=msg.buffer_id,
                                                      in_port=in_port,
                                                      actions=[parser.OFPActionOutput(value)],
                                                      data=probe_packet.data)
                            datapath.send_msg(out)
                            # self.logger.info(f"probe packet sent, time[0] updated : {self.time}")
                            del out
                            del probe_packet
                            self.time = (time.time(), self.time[1])
                            # self.logger.critical(f"ARP_OUT,{self.msg_cnt},{self.eth_to_ip.get(key)},{key},{value},{self.time[0]},0")
                        except Exception:
                            pass

                        data = None
                        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                            data = msg.data
                        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                                  in_port=in_port, actions=[parser.OFPActionOutput(value)], data=data)
                        datapath.send_msg(out)
                        del out
                        self.time = (self.time[0], time.time())
                        # self.logger.critical(f"UDP_OUT:Probe,{self.msg_cnt},{ip_src},{eth_src},0,{self.time[1]},0")
                return
            elif ip_src == "10.0.0.10":  # drop packet, no flow

                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data
                out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                          in_port=in_port, actions=[parser.OFPActionOutput(ofproto.OFPP_FLOOD)], data=data)
                datapath.send_msg(out)
                del out
                # self.logger.critical(f"UDP_OUT:Client,{self.msg_cnt},{ip_src},{eth_src},0,{999},0")
                return
            elif ip_dst == "10.0.0.40":
                latency: float = (time.time() - self.time[1]) * 1e3
                self.latency[1].update({eth_src: latency})
                # self.logger.info(f"updated entry[1] : {eth_src} ; {latency} msec")
                # self.logger.critical(f"UDP_IN,{self.msg_cnt},{ip_src},{eth_src},0,0,{latency}")

                if self.msg_cnt > 80:
                    self.logger.info(f"{self.latency[1]}")
                    list_1 = []
                    list_2 = []
                    _ = ""  # optimal host
                    # self.logger.info(f"{list_1} {list_2}")
                    for key, value in self.latency[1].items():
                        list_1.append(key)
                        list_2.append(value)
                    if list_2[0] > list_2[1]:
                        _ = list_1[1]
                        self.logger.info(f"CHOOSING {list_1[1]} AS SERVER, LATENCY {list_2[1]} msec ")
                    else:
                        _ = list_1[0]
                        self.logger.info(f"CHOOSING {list_1[0]} AS SERVER, LATENCY {list_2[0]} msec ")
                    # self.logger.info(f"CHOOSING {_} AS HOST")
                    actions = [parser.OFPActionOutput(self.mac_to_port[dpid][_])]
                    match = parser.OFPMatch(in_port=self.mac_to_port[dpid]["00:00:00:00:00:01"], eth_dst=_, eth_src="00:00:00:00:00:01")
                    # self.logger.info(f"ADDING FLOW")
                    if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                        self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                        return
                    else:
                        self.add_flow(datapath, 1, match, actions)

            else:  # from servers or ?
                pass

        # other packet
        else:
            pass

        if eth_dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][eth_dst]
            # self.logger.debug(f"out port {out_port}")
        else:
            # self.logger.info("flood")
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]  # out_port

        # install a flow - condition to trigger after set ammount of messages
        # if out_port != ofproto.OFPP_FLOOD:
        #     match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
        #     if msg.buffer_id != ofproto.OFP_NO_BUFFER:
        #         self.add_flow(datapath, 1, match, actions, msg.buffer_id)
        #         return
        #     else:
        #         self.add_flow(datapath, 1, match, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        # self.logger.debug(f"packet out\nport dict {self.mac_to_port}")
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
