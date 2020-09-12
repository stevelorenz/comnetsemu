from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import udp
from ryu.lib.packet import tcp
from ryu.lib.packet import icmp


class MiddleServing(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(MiddleServing, self).__init__(*args, **kwargs)

        # outport = self.mac_to_port[dpid][mac_address]
        self.mac_to_port = {
            1: {
                "00:00:00:00:00:01": 4,
                "00:00:00:00:00:02": 5,
                "00:00:00:00:00:03": 2,
                "00:00:00:00:00:04": 2,
            },
            5: {
                "00:00:00:00:00:03": 4,
                "00:00:00:00:00:04": 5,
                "00:00:00:00:00:01": 2,
                "00:00:00:00:00:02": 2,
            },
        }
        self.slice_Voipport = 9998
        self.end_switches = [1, 5]

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # construct flow_mod message and send it.
        mod = parser.OFPFlowMod(
            datapath=datapath,
            match=match,
            cookie=0,
            command=ofproto.OFPFC_ADD,
            idle_timeout=20,
            hard_timeout=0,
            priority=priority,
            flags=ofproto.OFPFF_SEND_FLOW_REM,
            actions=actions,
        )
        datapath.send_msg(mod)

    def _send_package(self, msg, datapath, in_port, actions):
        data = None
        ofproto = datapath.ofproto
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        )
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        in_port = msg.in_port
        dpid = datapath.id

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src

        # self.logger.info("packet in s%s in_port=%s eth_src=%s eth_dst=%s pkt=%s", dpid, in_port, src, dst, pkt)
        self.logger.info("INFO packet served from MiddleServing controller")
        self.logger.info("INFO packet arrived in s%s (in_port=%s)", dpid, in_port)

        if dpid in self.mac_to_port:
            if pkt.get_protocol(tcp.tcp):
                return

            elif pkt.get_protocol(icmp.icmp):
                return

            elif dst in self.mac_to_port[dpid]:
                out_port = self.mac_to_port[dpid][dst]
                self.logger.info(
                    "INFO sending packet from s%s (out_port=%s) w/ mac-to-port rule",
                    dpid,
                    out_port,
                )
                actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
                match = datapath.ofproto_parser.OFPMatch(dl_dst=dst)
                self.add_flow(datapath, 1, match, actions)
                self._send_package(msg, datapath, in_port, actions)

        elif dpid not in self.end_switches:
            out_port = ofproto.OFPP_FLOOD
            self.logger.info(
                "INFO sending packet from s%s (out_port=%s) w/ flooding rule",
                dpid,
                out_port,
            )
            actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
            match = datapath.ofproto_parser.OFPMatch(in_port=in_port)
            self.add_flow(datapath, 1, match, actions)
            self._send_package(msg, datapath, in_port, actions)
