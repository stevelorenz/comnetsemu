# Copyright (C) 2016 Nippon Telegraph and Telephone Corporation.
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

"""
About: Ryu application for the multi-hop topology.
TODO (Zuo): Reduce duplicated code.
"""
import os, sys
import json
import shlex
import subprocess
import argparse

import ryu.lib.packet as packet_lib
import ryu.topology.api as topo_api

from ryu import cfg
from ryu.app.wsgi import ControllerBase, Response, WSGIApplication, route
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.lib import dpid as dpid_lib
from ryu.lib.ovs import vsctl
from ryu.ofproto import ofproto_v1_3


APP_INSTANCE_NAME = "multi_hop_api_app"

# Assume the controller knows the IPs of end-hosts.
CLIENT_IP = "10.0.1.11"
SERVER_IP = "10.0.3.11"
SERVER_UDP_PORT = 9999
url = 'http://127.0.0.1:8080/mactable/{dpid}'




# set a new arg for recode_node
# First setting default recode_node_list


# CONF=cfg.CONF
# CONF.register_cli_opts([cfg.StrOpt('recode_node', default='[0,0,0]',
#          help='recode_node for switch')],group='test-switch') 



class MultiHopRest(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {"wsgi": WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(MultiHopRest, self).__init__(*args, **kwargs)
        self.switches = {}
        self.nodes = {}
        self.mac_to_port = {}
        self.ip_to_port = {}
        # Map specific interface names to port.
        self.vnf_iface_to_port = {} 
        # read recode_node from recode_node.temp
        self.is_recoded=False
        self.recode_node_list=[0,0,0]
        re_temp=open("recode_node.temp","r+")
        s1=re_temp.read()
        re_temp.close()
        os.remove("recode_node.temp")
        self.logger.info("[naibao]: succuessful delete recode_node.temp")
        s1_list_str=s1.split(',')
        self.recode_node_list=[int(i) for i in s1_list_str]
        # wsgi
        wsgi = kwargs["wsgi"]
        wsgi.register(MultiHopController, {APP_INSTANCE_NAME: self})

    # ISSUE: This is a temp workaround to get openflow port of each VNF instance
    # without adding a service discovery system.
    @staticmethod
    def _get_ofport(ifce: str):
        """Get the openflow port based on the iterface name.
        :param ifce (str): Name of the interface.
        """
        try:
            # MARK: root privilege is required to access the OVS DB.
            ret = int(
                subprocess.check_output(
                    shlex.split(f"sudo ovs-vsctl get Interface {ifce} ofport")
                )
                .decode("utf-8")
                .strip()
            )
        except Exception as e:
            print(e)
            import pdb

            pdb.set_trace()

        return ret

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):

        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.logger.info(f"*** Connect with datapath with ID: {datapath.id}")

        # Install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        self.add_flow(datapath, 0, match, actions)

        self.switches[datapath.id] = datapath

        # Get port number of the specific interface for VNF processing.
        port_num = self._get_ofport(f"s{datapath.id}-vnf{datapath.id}")
        self.vnf_iface_to_port[datapath.id] = port_num

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
                datapath=datapath,
                priority=priority,
                match=match,
                instructions=inst,
            )
        datapath.send_msg(mod)

    def action_l2fwd(self, msg, pkt, add_flow=False):
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match["in_port"]
        dpid = datapath.id
        eth = pkt.get_protocol(packet_lib.ethernet.ethernet)
        dst = eth.dst
        src = eth.src
        vnf_out_port = self.vnf_iface_to_port[datapath.id]

        self.mac_to_port.setdefault(dpid, {})

        ip = pkt.get_protocol(packet_lib.ipv4.ipv4)
        if ip:
            self.ip_to_port.setdefault(dpid, {})
            self.ip_to_port[dpid][ip.src] = in_port

            self.logger.info(
                f"""<Packet-In>[L2FWD]: DPID:{dpid}, l2_src:{src}, l2_dst:{dst}, in_port: {in_port}"""
            )

        self.mac_to_port[dpid][src] = in_port
        

        #-----   handle recode -------
        if dst in self.mac_to_port[dpid]: 
            # TODO: recode, here just let it work
            out_port = self.mac_to_port[dpid][dst]  
            # # here to deside if recode 
            # self.logger.info(f'[naibao]: packet can forward, judge recode, current dpid:{dpid}')
            # # true, need to recode
            # if self.recode_node_list[dpid-1] and in_port != vnf_out_port and ip:
            #     self.logger.info(f'[naibao]: {dpid} need to recode')
            #     out_port= vnf_out_port
            # else :
            #     out_port = self.mac_to_port[dpid][dst]            
        # ---------------------------
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        if add_flow:
            if out_port != ofproto.OFPP_FLOOD:
                match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
                # verify if we have a valid buffer_id, if yes avoid to send both
                # flow_mod & packet_out
                if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                    self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                    return
                else:
                    self.add_flow(datapath, 1, match, actions)

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

    @staticmethod
    def _check_sanity_udp(pkt):
        ip = pkt.get_protocol(packet_lib.ipv4.ipv4)
        udp = pkt.get_protocol(packet_lib.udp.udp)

        if (
            ip.src == CLIENT_IP
            and ip.dst == SERVER_IP
            and udp.dst_port == SERVER_UDP_PORT
        ):
            return True

        return False

    def handle_udp(self, msg, pkt):
        if not self._check_sanity_udp(pkt):
            self.logger.info(
                "<Packet-In>[UDP]: Receive un-known UDP flows. Action: L2FWD."
            )
            self.action_l2fwd(msg, pkt, add_flow=True)
            return

        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match["in_port"]
        dpid = datapath.id
        eth = pkt.get_protocol(packet_lib.ethernet.ethernet)
        ip = pkt.get_protocol(packet_lib.ipv4.ipv4)
        udp = pkt.get_protocol(packet_lib.udp.udp)

        l3_info = f"<Packet-In>[UDP]: DPID:{dpid}, l3_src:{ip.src}, l3_dst:{ip.dst}, in_port: {in_port}"
        l4_info = f"l4_src:{udp.src_port}, l4_dst: {udp.dst_port}, total_len: {udp.total_length}"
        self.logger.info(", ".join((l3_info, l4_info)))

        # --- Handle upstream flows.
        vnf_out_port = self.vnf_iface_to_port[datapath.id]
        # --- judge if need recode 
        if self.recode_node_list[dpid-1]:           
            if in_port == vnf_out_port:
                out_port = self.mac_to_port[dpid].get(eth.dst, None)
                if not out_port:
                    self.logger.error(
                        f"Can not find the output port of upstream UDP flows for vnf port of datapath {datapath.id}"
                    )
                    return
                actions = [parser.OFPActionOutput(out_port)]
            else:
                actions = [parser.OFPActionOutput(vnf_out_port)]
        else: 
            actions = [parser.OFPActionOutput(out_port)]
        # Add forwarding rules for these specific UDP flows.
        match = parser.OFPMatch(
            in_port=in_port,
            eth_src=eth.src,
            eth_dst=eth.dst,
            eth_type=0x0800,
            ip_proto=0x11,
            udp_dst=udp.dst_port,
        )
        # Use a higher priority to avoid overriding.
        if msg.buffer_id != ofproto.OFP_NO_BUFFER:
            self.add_flow(datapath, 17, match, actions, msg.buffer_id)
            return
        else:
            self.add_flow(datapath, 17, match, actions)

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

    def set_mac_to_port(self, dpid, entry):
        mac_table = self.mac_to_port.setdefault(dpid, {})
        datapath = self.switches.get(dpid)

        entry_port = entry['port']
        entry_mac = entry['mac']

        if datapath is not None:
            parser = datapath.ofproto_parser
            if entry_port not in mac_table.values():

                for mac, port in mac_table.items():

                    # from known device to new device
                    actions = [parser.OFPActionOutput(entry_port)]
                    match = parser.OFPMatch(in_port=port, eth_dst=entry_mac)
                    self.add_flow(datapath, 1, match, actions)

                    # from new device to known device
                    actions = [parser.OFPActionOutput(port)]
                    match = parser.OFPMatch(in_port=entry_port, eth_dst=mac)
                    self.add_flow(datapath, 1, match, actions)

                mac_table.update({entry_mac: entry_port})
        return mac_table

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug(
                "- Packet truncated: only %s of %s bytes",
                ev.msg.msg_len,
                ev.msg.total_len,
            )
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto

        # # here to recode
        #  is_recoded
        # if msg.reason == ofp.OFPR_ACTION:
        #     # TODO recode here
        #     self.logger.info('[naibao]: recoding...')
        #     is_recoded= True
        #     self.logger.info('[naibao]: recode finish')
        #     reason = 'Action'
        #     self.logger.info('[naibao] received: '
        #               'buffer_id=%x total_len=%d reason=%s '
        #               'table_id=%d match=%s data=%s',
        #               msg.buffer_id, msg.total_len, reason,
        #               msg.table_id, msg.match, msg.data)
            

        pkt = packet_lib.packet.Packet(msg.data)
        eth = pkt.get_protocol(packet_lib.ethernet.ethernet)
        arp = pkt.get_protocol(packet_lib.arp.arp)
        ip = pkt.get_protocol(packet_lib.ipv4.ipv4)
        udp = pkt.get_protocol(packet_lib.udp.udp)
        self.logger.info(f'[packet_in_handler]: udp={udp}')
        # Ignore LLDP packets
        if eth.ethertype == packet_lib.ether_types.ETH_TYPE_LLDP:
            return

        if arp:
            # MARK: If the MAC-based flow is added, all following UDP packets
            # will also be l2 forwarded.
            self.action_l2fwd(msg, pkt, add_flow=True)
        elif ip:
            if udp:
                self.logger.info('this is a UDP!!!')
                self.handle_udp(msg, pkt)
            else:
                self.action_l2fwd(msg, pkt, add_flow=True)
        else:
            # Ignore other packets.
            return


###############
#  REST APIs  #
###############


class MultiHopController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(MultiHopController, self).__init__(req, link, data, **config)
        self.multi_hop_api_app = data[APP_INSTANCE_NAME]

    @route("topology", "/mactable", methods=["GET"])
    def list_mac_table(self, req, **kwargs):
        body = json.dumps(list(self.multi_hop_api_app.mac_to_port.items()))
        return Response(content_type="application/json", body=body)

    @route("topology", "/iptable", methods=["GET"])
    def list_ip_table(self, req, **kwargs):
        body = json.dumps(list(self.multi_hop_api_app.ip_to_port.items()))
        return Response(content_type="application/json", body=body)

    @route('topology', url, methods=['PUT'],requirements={'dpid': dpid_lib.DPID_PATTERN})
    def put_mac_table(self, req, **kwargs):

        multi_hop_api_app = self.multi_hop_api_app
        dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
        try:
            new_entry = req.json if req.body else {}
        except ValueError:
            raise Response(status=400)

        if dpid not in multi_hop_api_app.mac_to_port:
            return Response(status=404)

        try:
            mac_table = multi_hop_api_app.set_mac_to_port(dpid, new_entry)
            body = json.dumps(mac_table)
            return Response(content_type='application/json', body=body)
        except Exception as e:
            return Response(status=500)