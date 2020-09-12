from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0

from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types


class InitFlowEntry(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(InitFlowEntry, self).__init__(*args, **kwargs)

        # out_port = slice_to_port[dpid][in_port]
        self.slice_to_port = {
            2: {3: 1, 1: 3},
            4: {2: 4, 4: 2},
            7: {1: 3, 3: 1},
        }

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        # install the table-miss flow entry.
        self.logger.info("INFO New entry to switch")
        for key in self.slice_to_port[dpid]:
            in_port = key
            out_port = self.slice_to_port[dpid][key]
            match = datapath.ofproto_parser.OFPMatch(in_port=in_port)
            actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
            self.logger.info(
                "INFO adding entry (in_port=%s out_port=%s) to s%s",
                in_port,
                out_port,
                dpid,
            )
            self.add_flow(datapath, 2, match, actions)

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # construct flow_mod message and send it.
        mod = parser.OFPFlowMod(
            datapath=datapath,
            match=match,
            cookie=0,
            command=ofproto.OFPFC_ADD,
            idle_timeout=0,
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
        # self.logger.info("send_msg %s", out)
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        in_port = msg.in_port
        dpid = datapath.id

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return

        self.logger.info("INFO packet arrived in s%s (in_port=%s)", dpid, in_port)
        out_port = self.slice_to_port[dpid][in_port]
        actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
        match = datapath.ofproto_parser.OFPMatch(in_port=in_port)
        self.logger.info("INFO sending packet from s%s (out_port=%s)", dpid, out_port)
        self.add_flow(datapath, 2, match, actions)
        self._send_package(msg, datapath, in_port, actions)
