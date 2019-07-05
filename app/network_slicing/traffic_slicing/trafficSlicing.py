from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import udp
from ryu.lib.packet import tcp
from ryu.lib.packet import arp


class TrafficSlicing(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TrafficSlicing, self).__init__(*args, **kwargs)
        # initialize mac address table.
        self.mac_to_port = {}
        self.slice_TCport = 9999
        self.mac = '6D:0D:E5:0A:C4:7E'.lower()
        self.ip = '10.1.1.1'
        self.hosts_IPs = ['10.0.0.1', '10.0.0.2', '10.0.0.3', '10.0.0.4']
        self.slice_ports = {1 : {1 : 1, 2 : 2}, 4 : {1 : 1 , 2 : 2}}
        self.end_swtiches = [1 ,4]

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install the table-miss flow entry.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        
        for ip in self.hosts_IPs:
            self._broadcast_arp_request(datapath, ip)


    def _broadcast_arp_request(self, datapath, dest_ip):
        pkg_request = packet.Packet()
        pkg_request.add_protocol(ethernet.ethernet(ethertype=ether_types.ETH_TYPE_ARP, dst='ff:ff:ff:ff:ff:ff', src=self.mac))
        pkg_request.add_protocol(arp.arp(opcode=arp.ARP_REQUEST,
                                 src_mac=self.mac,
                                 src_ip=self.ip,
                                 dst_ip=dest_ip))

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkg_request.serialize()
        #self.logger.info("send arp request: packet-out %s" % (pkg_request,))
        actions = [parser.OFPActionOutput(ofproto.OFPP_ALL)]
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=ofproto.OFP_NO_BUFFER,
                                  in_port=ofproto.OFPP_CONTROLLER,
                                  actions=actions,
                                  data=pkg_request.data)
        datapath.send_msg(out)
        
    def _handle_arp_response(self, dpid, src, in_port):
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # construct flow_mod message and send it.
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

    def _send_package(self, msg, datapath, in_port, actions):
        data = None
        ofproto = datapath.ofproto
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
            actions=actions, data=data)
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src

        dpid = datapath.id

        #self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        if dst == self.mac and pkt.get_protocol(arp.arp):
            self._handle_arp_response(dpid, src, in_port)
            print(self.mac_to_port)
            return

        elif dpid in self.mac_to_port:
            if dst in self.mac_to_port[dpid]:
                out_port = self.mac_to_port[dpid][dst]
                actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
                match = datapath.ofproto_parser.OFPMatch(eth_dst=dst)
                self.add_flow(datapath, 1, match, actions)
                self._send_package(msg, datapath, in_port, actions)
                
            elif pkt.get_protocol(udp.udp) and pkt.get_protocol(udp.udp).dst_port == self.slice_TCport:
                pkt_udp = pkt.get_protocol(udp.udp)
                slice_number = 1
                out_port = self.slice_ports[dpid][slice_number]
                match = datapath.ofproto_parser.OFPMatch(   
                    in_port = in_port,
                    eth_dst = dst,
                    eth_type = ether_types.ETH_TYPE_IP,
                    ip_proto = 0x11,    #udp
                    udp_dst = self.slice_TCport
                )
                
                actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
                self.add_flow(datapath, 2, match, actions)
                self._send_package(msg, datapath, in_port, actions)

            else:
                slice_number = 2
                out_port = self.slice_ports[dpid][slice_number]
                match = datapath.ofproto_parser.OFPMatch(   
                    in_port=in_port, 
                    eth_dst=dst,
                    eth_src=src
                    )
                actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
                self.add_flow(datapath, 1, match, actions)
                self._send_package(msg, datapath, in_port, actions)

        elif dpid not in self.end_swtiches:
            out_port = ofproto.OFPP_FLOOD
            actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
            match = datapath.ofproto_parser.OFPMatch(in_port=in_port)
            self.add_flow(datapath, 1, match, actions)
            self._send_package(msg, datapath, in_port, actions)

