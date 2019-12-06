import time
from typing import Tuple, Dict
import socket

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
        """
        initalize controller, no arguments expected
        :param mac_to_port: map MAC address to ports
        :param eth_to_ip: map MAC address to IPv4
        """
        super(Controller, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.eth_to_ip = {}
        self.latency = ({}, {})  # (link latency (with ARP), service latency (with UDP))
        self.time: Tuple[float, float] = (
            0.0,
            0.0,
        )  # timestamp to calculate (link, service) latency
        self.msg_cnt = 0  # msg count to decide on end of startup
        self.optimal_host = ""
        self.tx_socket = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM
        )  # socket for REST
        self.tx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.tx_socket.connect(("127.0.0.1", 8016))

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        self.add_flow(datapath, 0, match, actions)

    def remove_table_flows(self, datapath, table_id, match, instructions):
        """
        remove flows with empty flow mod
        """
        ofproto = datapath.ofproto
        flow_mod = datapath.ofproto_parser.OFPFlowMod(
            datapath,
            0,
            0,
            table_id,
            ofproto.OFPFC_DELETE,
            0,
            0,
            ofproto.OFPP_ANY,
            ofproto.OFPG_ANY,
            0,
            match,
            instructions,
        )
        return flow_mod

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(
                datapath=datapath,
                buffer_id=buffer_id,
                priority=priority,
                match=match,
                instructions=inst,
            )
        else:
            mod = parser.OFPFlowMod(
                datapath=datapath, priority=priority, match=match, instructions=inst
            )
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):  # avoid triggering this for server -> client
        """
        handle incoming packets\n
        separate actions for ARP / UDP control / probing and data packets
        notify host application about migration / update of optimal host via REST
        :param ev: event message (contains packet)
        :return: None
        """
        self.msg_cnt += 1
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug(
                "packet truncated: only %s of %s bytes",
                ev.msg.msg_len,
                ev.msg.total_len,
            )
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match["in_port"]

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
            # update latency if from serv
            if eth_dst == "00:00:00:00:01:ff":
                latency: float = (time.time() - self.time[0]) * 1e3
                self.latency[0].update({eth_src: latency})
                for key, value in self.latency[0].items():
                    if key != "00:00:00:00:00:01":
                        self.logger.info(f"ARP,{key},{value}")

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

            # probing packet from probing agent
            if ip_src == "10.0.0.40":
                for key, value in self.mac_to_port[
                    dpid
                ].items():  # send arp probe to all servers
                    if (
                        key != "00:00:00:00:00:01"
                        and key != "ff:ff:ff:ff:ff:ff"
                        and key != "00:00:00:00:01:ff"
                    ):
                        try:
                            probe_packet = packet.Packet()
                            addr = self.eth_to_ip.get(key)
                            if addr is None:
                                if key == "00:00:00:00:01:01":
                                    addr = "10.0.0.21"
                                elif key == "00:00:00:00:01:02":
                                    addr = "10.0.0.22"
                                else:
                                    raise
                            probe_packet.add_protocol(
                                ethernet.ethernet(
                                    dst="ff:ff:ff:ff:ff:ff",
                                    src="00:00:00:00:01:ff",
                                    ethertype=ether.ETH_TYPE_ARP,
                                )
                            )
                            probe_packet.add_protocol(
                                arp.arp(
                                    hwtype=1,
                                    proto=0x0800,
                                    hlen=6,
                                    plen=4,
                                    opcode=1,
                                    src_mac="00:00:00:00:01:ff",
                                    src_ip="10.0.0.40",
                                    dst_mac="00:00:00:00:00:00",
                                    dst_ip=addr,
                                )
                            )
                            probe_packet.serialize()
                            out = parser.OFPPacketOut(
                                datapath=datapath,
                                buffer_id=msg.buffer_id,
                                in_port=in_port,
                                actions=[parser.OFPActionOutput(value)],
                                data=probe_packet.data,
                            )
                            datapath.send_msg(out)
                            del out
                            del probe_packet
                            self.time = (time.time(), self.time[1])
                        except Exception:
                            pass

                        data = None
                        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                            data = msg.data
                        out = parser.OFPPacketOut(
                            datapath=datapath,
                            buffer_id=msg.buffer_id,
                            in_port=in_port,
                            actions=[parser.OFPActionOutput(value)],
                            data=data,
                        )
                        datapath.send_msg(out)
                        del out
                        self.time = (self.time[0], time.time())
                return

            # data packet from client (drop due to no flow yet ?)
            elif ip_src == "10.0.0.10":
                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data
                out = parser.OFPPacketOut(
                    datapath=datapath,
                    buffer_id=msg.buffer_id,
                    in_port=in_port,
                    actions=[parser.OFPActionOutput(ofproto.OFPP_FLOOD)],
                    data=data,
                )
                datapath.send_msg(out)
                del out
                return

            # probing packet from server
            elif ip_dst == "10.0.0.40":
                latency: float = (time.time() - self.time[1]) * 1e3
                self.latency[1].update({eth_src: latency})
                # no optimal host evaluation during startup period, msg_cnt of 80 assumed sufficient by experience
                if self.msg_cnt > 80:
                    mac_list = []
                    latency_list = []
                    _ = ""
                    for key, value in self.latency[
                        1
                    ].items():  # @TODO replace with more elegant parsing dict to list
                        mac_list.append(key)
                        latency_list.append(value)
                        self.logger.info(f"UDP,{key},{value}")
                    # find optimal host (min latency)
                    min_ = latency_list.index(min(latency_list))
                    _ = mac_list[min_]
                    # update optimal host on change with REST approach
                    if self.optimal_host != mac_list[min_]:
                        self.optimal_host = mac_list[min_]
                        self.tx_socket.sendall(f"NEW SERVER {mac_list[min_]}".encode())
                    actions = [parser.OFPActionOutput(self.mac_to_port[dpid][_])]
                    match = parser.OFPMatch(
                        in_port=self.mac_to_port[dpid]["00:00:00:00:00:01"],
                        eth_dst=_,
                        eth_src="00:00:00:00:00:01",
                    )
                    # add new optimal flow (@TODO check this)
                    if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                        self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                        return
                    else:
                        self.add_flow(datapath, 1, match, actions)
            else:  # other data source
                pass
        else:  # -> default msg out
            pass

        # set out_port for known host, else FLOOD
        if eth_dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][eth_dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]  # out_port

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        )
        datapath.send_msg(out)
