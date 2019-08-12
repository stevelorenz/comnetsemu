from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, arp, ethernet, ipv4, ipv6, ether_types, icmp
from ryu.lib import hub

from ryu.app import simple_switch_13
from ryu.app.wsgi import ControllerBase
from ryu.app.wsgi import Response
from ryu.app.wsgi import route
from ryu.app.wsgi import WSGIApplication
import json


from enum import Enum
from multiprocessing import Process, Pipe
from collections import defaultdict
import sys
import random
import time
import numpy as np
import copy

#sys.path.append("..")
import learning_module
import functions
from routingDFS import RoutingDFS

# routing type
class RoutingType(Enum):
    DFS = 1
    DIJKSTRA = 2
    RL_GRAPH = 3
    RL_DFS = 4

class BiasRL(Enum):
    DFS = 1
    RANDOM = 2

ROUTING_TYPE = RoutingType.DFS

# update rate in s
UPDATE_INTERVAL_PROCESS_COMMUNICATION = 1
UPDATE_INTERVAL_LAT = 1
# UPDATE_INTERVAL_ECHO = 3
UPDATE_INTERVAL_DATA = 1

# Reference bandwidth = 1 Gbp/s
REFERENCE_BW = 10000000
MAX_PATHS = 2
ADDITIONAL_WAITING_TIME = 10
LOOPBACK_IP = "127.0.0.1"
# wichtung bw
DEFAULT_BW = 10000000

simple_switch_instance_name = 'simple_switch_api_app'
url = '/simpleswitch/params/{obj}'


###############################################################
########## Remote controller ##################################
###############################################################
class ControllerMain(simple_switch_13.SimpleSwitch13):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(ControllerMain, self).__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        wsgi.register(SimpleSwitchController,
                      {simple_switch_instance_name: self})

        self.bias = BiasRL.DFS

        self.waitTillStart = 0

        # initialize mac address table.
        self.mac_to_port = {}

        self.dpidToDatapath = {}
        self.arp_table = {}

        # flowId = dst_IP+src_ip
        self.paths_per_flows = {}
        # chosenPath
        self.chosen_path_per_flow = {}

        # parts of routing
        self.datapath_list = {}
        self.arp_table = {}
        self.switches = []
        self.hosts = {}
        self.adjacency = defaultdict(dict)
        # change for latency
        self.bandwidths = defaultdict(lambda: defaultdict(lambda: DEFAULT_BW))
        self.routingDFS = RoutingDFS()
        # self.routingRL = RoutingRL()

        # temporary saving RTT times
        self.echo_sent_to_dpid = {}
        self.rtt_to_dpid = {}
        self.rtt_stats_sent = {}

        # dicts so save data
        # bundled saving RTT/echo times
        self.saved_rtt_to_dpid = {}
        self.saved_echo_rtt_to_dpid = {}
        self.saved_echo_timeToSw = {}
        self.saved_echo_timeToC = {}
        self.saved_rtt_to_dpid_portStats = {}
        self.rtt_portStats_to_dpid = {}
        # temporary saving of port stats
        self.temp_bw_map_ports = {}
        self.temp_bw_map_flows = {}

        # BW in Kbit/s, Latency in ms
        self.data_map = {}
        self.lastArrivedPackage = {}

        self.latencyDict = {}
        self.bandwithPortDict = {}
        self.bandwithFlowDict = {}
        self.bestRouteRL = []

        # already routed
        self.alreadyRouted = []
        # Matrix Creation

        # load levels (for leanring Module)
        self.reset_flag = False
        self.loadLevel = 0
        # iteration levels
        self.iteration_flag = False
        self.iteration = 0
        # rerouting
        # hub.spawn(self.reroutingSimulator)
        self.parent_conn, self.child_conn = Pipe()
        # starting learning process
        p = Process(target=learning_module.learningModule, args=[self.child_conn])
        p.start()
        # p.join()
        hub.spawn(self.checkingUpdates)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        # register datapaths
        dpid = datapath.id
        # install the table-miss flow entry.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        # no icmp level 3 (iperf sends these ones)
        match = parser.OFPMatch(
                eth_type=0x0800,
                ip_proto=1,
                icmpv4_type=3
              )
        actions = []
        self.add_flow(datapath, 1, match, actions)

        self.dpidToDatapath[dpid] = datapath
        self.lastArrivedPackage[dpid] = {}
        # ggf max BW abfragen / phys. mgl.
        #  starting the monitoring elements
        #  echo_request
        hub.spawn(self.monitor_sw_controller_latency, datapath)
        # Starting flooding thread for flooding monitoring package
        hub.spawn(self.monitor_latency, datapath, ofproto)

    # checks for action done
    # updates latency dict learning module
    def checkingUpdates(self):
        i = 0
        hub.sleep(5)
        while True:
            # check if action in pipe
            if self.parent_conn.poll():
                action = self.parent_conn.recv()
                if len(action) > 0:
                    actionIdString = action[0]
                    newPath = action[1]
                    self.rerouteNonLV(actionIdString, newPath)
                    i = 0
            # if matrix necessary:
            # self.latencyMatrix = functions.create_matrix(self.data_map, 'latencyRTT')
            # self.latencyDict = functions.convertMatrixToDict(self.latencyMatrix)
            self.latencyDict = functions.convertDataMapToDict(self.data_map, 'latencyRTT')
            if i > 3:
                sendingTuple = (self.chosen_path_per_flow, self.paths_per_flows, self.latencyDict, self.reset_flag, self.loadLevel)
                self.parent_conn.send(sendingTuple)
                # if sent once, set resetflag to False
                self.reset_flag = False
            i = i + 1
            hub.sleep(UPDATE_INTERVAL_PROCESS_COMMUNICATION)

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # construct flow_mod message and send it.
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath,
                                flags=ofproto.OFPFC_ADD,
                                priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

    def mod_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # construct flow_mod message and send it.
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, flags=ofproto.OFPFC_MODIFY, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

    def del_flow(self, datapath, match):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        mod = parser.OFPFlowMod(datapath=datapath,
                                command=ofproto.OFPFC_DELETE,
                                out_port=ofproto.OFPP_ANY,
                                out_group=ofproto.OFPG_ANY,
                                match=match)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        timestampRecieve = time.time()
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        # get Datapath ID to identify OpenFlow switches.
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})
        # analyse the received packets using the packet library.
        pkt = packet.Packet(msg.data)

        eth_pkt = pkt.get_protocols(ethernet.ethernet)[0]
        arp_pkt = pkt.get_protocol(arp.arp)
        ipv4_pkt = pkt.get_protocol(ipv4.ipv4)

        dst_mac = eth_pkt.dst
        src_mac = eth_pkt.src
        dpidRec = datapath.id
        in_port = msg.match['in_port']

        if (eth_pkt.ethertype == 0x07c3):
            pkt_header_list = pkt[-1].decode("utf-8").split('#')
            timestampSent = (float)(pkt_header_list[0])
            dpidSent = (int)(pkt_header_list[1])
            if not dpidSent in self.lastArrivedPackage[dpidRec].keys():
                self.lastArrivedPackage[dpidRec][dpidSent] = 0.0
                # createLink
            # timedifference
            timeDifference = timestampRecieve - timestampSent
            # if package is newest
            if (timestampSent > self.lastArrivedPackage[dpidRec][dpidSent]):
                # creating dictionaries and arrays
                if not dpidRec in self.data_map.keys():
                    self.data_map[dpidRec] = {}
                if not dpidSent in self.data_map[dpidRec].keys():
                    self.data_map[dpidRec][dpidSent] = {}
                    self.data_map[dpidRec][dpidSent]['in_port'] = in_port
                    self.data_map[dpidRec][dpidSent]['bw'] = []
                    self.data_map[dpidRec][dpidSent]['latencyRTT'] = []
                latencyLinkEchoRTT = timeDifference - (float(self.rtt_portStats_to_dpid[dpidSent]) / 2) - (
                        float(self.rtt_portStats_to_dpid[dpidRec]) / 2)
                # latency object echo RTT
                latencyObjRTT = {}
                latencyObjRTT['timestamp'] = timestampSent
                latencyObjRTT['value'] = latencyLinkEchoRTT * 1000
                self.data_map[dpidRec][dpidSent]['latencyRTT'].append(latencyObjRTT)
            return

        if src_mac not in self.hosts:
            self.hosts[src_mac] = (dpidRec, in_port)
        ## filter packets
        if eth_pkt.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
            # -------------------
            # avoid broadcast from LLDP
        if eth_pkt.ethertype == 35020:
            return

        if pkt.get_protocol(ipv6.ipv6):  # Drop the IPV6 Packets.
            match = parser.OFPMatch(eth_type=eth_pkt.ethertype)
            actions = []
            self.add_flow(datapath, 1, match, actions)
            return None

        # -------------------
        out_port = ofproto.OFPP_FLOOD

        if arp_pkt:
            # print dpid, pkt
            src_ip = arp_pkt.src_ip
            dst_ip = arp_pkt.dst_ip

            if arp_pkt.opcode == arp.ARP_REPLY:
                self.arp_table[src_ip] = src_mac
                h1 = self.hosts[src_mac]
                h2 = self.hosts[dst_mac]
                if (h1, h2) not in self.alreadyRouted:
                    self.routingAfterARP(h1, h2, src_ip, dst_ip)
                return
            elif arp_pkt.opcode == arp.ARP_REQUEST:
                if dst_ip in self.arp_table:
                    dst_mac = self.arp_table[dst_ip]
                    h1 = self.hosts[src_mac]
                    h2 = self.hosts[dst_mac]
                    if (h1, h2) not in self.alreadyRouted:
                        self.arp_table[src_ip] = src_mac
                        dst_mac = self.arp_table[dst_ip]
                        h1 = self.hosts[src_mac]
                        h2 = self.hosts[dst_mac]
                        t0 = time.time()
                        self.routingAfterARP(h1, h2, src_ip, dst_ip)
                        self.logger.info(
                            "Calc needed for DFS routing between h1: {} and h2: {}: {}".format(src_ip, dst_ip, (
                                    time.time() - t0) * 10 ** 6))
                        self.alreadyRouted.append((h1, h2))
                    return
                else:
                    # flooding ARP request
                    actions = [parser.OFPActionOutput(out_port)]
                    data = None
                    if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                        data = msg.data
                    out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                              in_port=in_port, actions=actions, data=data)
                    datapath.send_msg(out)

        if ipv4_pkt:
            src_ip = ipv4_pkt.src
            dst_ip = ipv4_pkt.dst
            if dst_ip in self.arp_table and src_ip in self.arp_table:
                src_mac = self.arp_table[src_ip]
                dst_mac = self.arp_table[dst_ip]
                h1 = self.hosts[src_mac]
                h2 = self.hosts[dst_mac]
                self.routingAfterIP(h1, h2, src_ip, dst_ip)

    def monitor_sw_controller_latency(self, datapath):
        hub.sleep(0.5 + self.waitTillStart)
        # self.waitTillStart += 0.25
        iterator = 0
        while True:
            # data = ''
            # self.send_echo_request(datapath, data)
            if iterator % 2 == 0:
                self.send_portStatsRequest(datapath)
            else:
                self.send_flow_stats_request(datapath)
            iterator += 1
            hub.sleep(UPDATE_INTERVAL_DATA)

    # the monitoring package
    def monitor_latency(self, datapath, ofproto):
        hub.sleep(self.waitTillStart+5)
        # self.waitTillStart += 0.25
        print("MONITORING LATENCY STARTED dpid: {}".format(datapath.id))
        while True:
            self.send_packet_out(datapath, ofproto.OFP_NO_BUFFER, ofproto.OFPP_CONTROLLER)
            hub.sleep(UPDATE_INTERVAL_LAT)

    def send_portStatsRequest(self, datapath):
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser
        req = ofp_parser.OFPPortStatsRequest(datapath, 0, ofp.OFPP_ANY)
        self.rtt_stats_sent[datapath.id] = time.time()
        datapath.send_msg(req)
        # save timeStamp for RTT

    def send_flow_stats_request(self, datapath):
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser
        # only the ones with layer 4
        match =  ofp_parser.OFPMatch(eth_type = 2048)
        req = ofp_parser.OFPFlowStatsRequest(datapath, 0, ofp.OFPTT_ALL,
                                             ofp.OFPP_ANY, ofp.OFPG_ANY, 0, 0, match)
        self.rtt_stats_sent[datapath.id] = time.time()
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        currentTime = time.time()
        dpidRec = ev.msg.datapath.id
        # updating switch controller latency
        oldTime = self.rtt_stats_sent[dpidRec]
        totalRTT = currentTime - oldTime
        self.rtt_portStats_to_dpid[dpidRec] = totalRTT
        body = ev.msg.body
        # parsing the answer
        for stat in body:
            # get port id
            port_no = (int)(stat.port_no)
            # self.rtt_port_stats_sent[dpidRec] = 0
            if dpidRec in self.data_map.keys():
                for dpidSentElement in self.data_map[dpidRec]:
                    in_port = self.data_map[dpidRec][dpidSentElement]["in_port"]
                    if in_port == port_no:
                        # found the right connection

                        # check if bw-map is built, first time!
                        if not dpidRec in self.temp_bw_map_ports.keys():
                            self.temp_bw_map_ports[dpidRec] = {}
                            self.bandwithPortDict[dpidRec] = {}
                        if not port_no in self.temp_bw_map_ports[dpidRec].keys():
                            self.temp_bw_map_ports[dpidRec][port_no] = {}
                            bytes_now = stat.rx_bytes
                            # bytes_now = stat.tx_bytes
                            ts_now = (stat.duration_sec + stat.duration_nsec / (10 ** 9))
                            # overwriting tempMap
                            self.temp_bw_map_ports[dpidRec][port_no]['ts'] = ts_now
                            self.temp_bw_map_ports[dpidRec][port_no]['bytes'] = bytes_now
                            # save the time
                            self.temp_bw_map_ports[dpidRec][port_no]['ts'] = ts_now
                            # self.logger.info("TS BW: {}".format(self.temp_bw_map[dpidRec][port_no]['ts']))
                            #self.temp_bw_map_ports[dpidRec][port_no]['tsUTC'] = time.time()
                        else:
                            ts_before = self.temp_bw_map_ports[dpidRec][port_no]['ts']
                            bytes_before = self.temp_bw_map_ports[dpidRec][port_no]['bytes']
                            # ts_now = time.time()
                            bytes_now = stat.tx_bytes
                            ts_now = (stat.duration_sec + stat.duration_nsec / (10 ** 9))
                            byteDiff = bytes_now - bytes_before
                            tsDiff = ts_now - ts_before  # TODO: ggf RTT mit einbeziehen
                            # overwriting tempMap
                            self.temp_bw_map_ports[dpidRec][port_no]['ts'] = ts_now
                            self.temp_bw_map_ports[dpidRec][port_no]['bytes'] = bytes_now
                            # bw (bytes/sec)
                            bw = byteDiff / tsDiff
                            self.bandwithPortDict[dpidRec][port_no] = bw

    # for getting flow stats
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply_handler(self, ev):
        dpidRec = ev.msg.datapath.id
        # updating switch controller latency
        self.rtt_portStats_to_dpid[dpidRec] = time.time() - self.rtt_stats_sent[dpidRec]
        flows = []

        for stat in ev.msg.body:
            if 'icmpv4_type' not in stat.match:
                ipSrc = stat.match['ipv4_src']
                ipDst = stat.match['ipv4_dst']
                numberBytes = stat.byte_count
                if dpidRec not in list(self.temp_bw_map_flows):
                    self.temp_bw_map_flows[dpidRec] = {}
                if ipSrc not in list(self.temp_bw_map_flows[dpidRec]):
                    self.temp_bw_map_flows[dpidRec][ipSrc] = {}
                if ipDst not in list(self.temp_bw_map_flows[dpidRec][ipSrc]):
                    self.temp_bw_map_flows[dpidRec][ipSrc][ipDst] = {}
                    ts_now = (stat.duration_sec + stat.duration_nsec / (10 ** 9))
                    self.temp_bw_map_flows[dpidRec][ipSrc][ipDst]['ts'] = ts_now
                    self.temp_bw_map_flows[dpidRec][ipSrc][ipDst]['bytes'] = stat.byte_count
                else:
                    ts_now = (stat.duration_sec + stat.duration_nsec / (10 ** 9))
                    timeDiff = ts_now - self.temp_bw_map_flows[dpidRec][ipSrc][ipDst]['ts']
                    bytesDiff = numberBytes - self.temp_bw_map_flows[dpidRec][ipSrc][ipDst]['bytes']
                    bw = bytesDiff / timeDiff
                    if dpidRec not in list(self.bandwithFlowDict.keys()):
                        self.bandwithFlowDict[dpidRec] = {}
                    if ipSrc not in list(self.bandwithFlowDict[dpidRec].keys()):
                        self.bandwithFlowDict[dpidRec][ipSrc] = {}
                    if ipDst not in list(self.bandwithFlowDict[dpidRec][ipSrc].keys()):
                        self.bandwithFlowDict[dpidRec][ipSrc][ipDst] = bw
                    self.temp_bw_map_flows[dpidRec][ipSrc][ipDst]['ts'] = ts_now
                    self.temp_bw_map_flows[dpidRec][ipSrc][ipDst]['bytes'] = stat.byte_count
                    self.bandwithFlowDict[dpidRec][ipSrc][ipDst] = bw


    def send_packet_out(self, datapath, buffer_id, in_port):
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser
        packet = self.create_packet(datapath.id)
        data = packet.data
        actions = [ofp_parser.OFPActionOutput(ofp.OFPP_FLOOD, 0)]
        req = ofp_parser.OFPPacketOut(datapath, buffer_id,
                                      in_port, actions, data)
        datapath.send_msg(req)

    def create_packet(self, dpid):
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=0x07c3,
                                           dst='ff:ff:ff:ff:ff:ff',
                                           src='00:00:00:00:00:09'))
        wholeData = str(time.time()) + '#' + str(dpid) + '#'
        pkt.add_protocol(bytes(wholeData, "utf-8"))
        pkt.serialize()
        return pkt

    # saving the Bw in Map
    def saveInMap(self, dpidRec, in_port, bw, ts_before):
        for keysDpidSent in self.data_map[dpidRec].keys():
            # matching the portNumber
            if self.data_map[dpidRec][keysDpidSent]['in_port'] == in_port:
                # bw object
                bwObject = {}
                bwObject['timestamp'] = ts_before
                # in kb/s
                bwObject['value'] = bw / 1000
                self.data_map[dpidRec][keysDpidSent]['bw'].append(bwObject)
                break

    def routingAfterARP(self, h1, h2, src_ip, dst_ip):

        self.logger.info("Routing ARP DFS")
        idForward = functions.buildConnectionBetweenHostsId(src_ip, dst_ip)
        pathOptimal, paths = self.routingDFS.get_optimal_path(self, h1[0], h2[0])
        self.routingDFS.install_path(self, pathOptimal, h1[1], h2[1], src_ip, dst_ip, 'arp')

    def routingAfterIP(self, h1, h2, src_ip, dst_ip):
        if (ROUTING_TYPE == RoutingType.DFS):
            idForward = functions.buildConnectionBetweenHostsId(src_ip, dst_ip)
            pathOptimal, paths = self.routingDFS.get_optimal_path(self, h1[0], h2[0])
            self.paths_per_flows[idForward] = paths
            if self.bias.value == BiasRL.DFS.value:
                self.routingDFS.install_path(self,  pathOptimal, h1[1], h2[1], src_ip, dst_ip, 'ipv4')
                self.chosen_path_per_flow[idForward] = pathOptimal
            elif self.bias.value == BiasRL.RANDOM.value:
                chosenPath = random.choice(paths)
                self.routingDFS.install_path(self, chosenPath, h1[1], h2[1], src_ip, dst_ip, 'ipv4')
                self.chosen_path_per_flow[idForward] = chosenPath

    # prev: self, src_ip, dst_ip, newPath
    def rerouteNonLV(self, idForward, newPath):

        chosenflowPrev = copy.deepcopy(self.chosen_path_per_flow[idForward])

        # newPath = self.getRandomPath(pathsWithCostForward, chosenflowPrev)
        src_ip, dst_ip = functions.buildIpAdresses(idForward)
        self.chosen_path_per_flow[idForward] = newPath

        # first and last are same
        i = 0
        flowAddList = []
        flowModList = []
        flowDeleteList = []

        differenceSet = set(chosenflowPrev).difference(newPath)
        # check if things deleted
        if len(differenceSet) > 0:
            flowDeleteList = list(differenceSet)

        for switch in newPath:
            # self.logger.info("Checking Switch (new): {}".format(switch))
            if switch in chosenflowPrev:
                # check prev
                indexPrev = chosenflowPrev.index(switch)
                if (i > 0):
                    if newPath[i - 1] == chosenflowPrev[indexPrev - 1]:
                        i += 1
                        continue
                    # have to change index before
                    else:
                        if ((newPath[i - 1] not in flowAddList)) and (
                                (newPath[i - 1] not in flowDeleteList) and chosenflowPrev[indexPrev] not in flowDeleteList):
                            print("Not same: {}".format(switch))
                            flowModList.append(newPath[i - 1])
            else:
                flowAddList.append(switch)
                # print("switch not in list: {}".format(switch))
                indexPrev = newPath.index(switch)
                flowModList.append(newPath[indexPrev - 1])
            i += 1
        # flowDeleteList = chosenflowPrevCopy
        for j in range(0, len(flowDeleteList), 1):
            switchOldIndex = chosenflowPrev.index(flowDeleteList[j])
            switchOldIndexPrev = switchOldIndex - 1
            if chosenflowPrev[switchOldIndexPrev] not in flowDeleteList:
                flowModList.append(chosenflowPrev[switchOldIndexPrev])
            j += 1

        # first addFlows
        for switch in flowAddList:
            # get index of next switch
            index = newPath.index(switch)
            nextIndex = index + 1
            if (nextIndex < len(newPath)):
                followingSwitch = newPath[nextIndex]
                self.addFlowSpecificSwitch(switch, src_ip, dst_ip,
                                           functions.getOutputPort(self, switch, followingSwitch))

        # second: mod flows
        for switch in flowModList:
            index = newPath.index(switch)
            nextIndex = index + 1
            if nextIndex < len(newPath):
                followingSwitch = newPath[nextIndex]
                self.modFlowSpecificSwitch(switch, src_ip, dst_ip,
                                           functions.getOutputPort(self, switch, followingSwitch))
        # third: delete flows
        for switch in flowDeleteList:
            # clean up bw flow list
            try:
                self.bandwithFlowDict[switch][src_ip].pop(dst_ip, None)
            except KeyError:
                print("Key {} not found".format(dst_ip))
            self.delFlowSpecificSwitch(switch, src_ip, dst_ip)

    def addFlowSpecificSwitch(self, switch, ip_src, ip_dst, outPort):
        dp = self.dpidToDatapath[switch]
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser
        actions = [ofp_parser.OFPActionOutput(outPort)]
        match_ip = ofp_parser.OFPMatch(
            eth_type=0x0800,
            ipv4_src=ip_src,
            ipv4_dst=ip_dst
        )
        match_arp = ofp_parser.OFPMatch(
            eth_type=0x0806,
            arp_spa=ip_src,
            arp_tpa=ip_dst
        )
        self.add_flow(dp, 32768, match_ip, actions)

    def modFlowSpecificSwitch(self, switch, ip_src, ip_dst, outPort):
        dp = self.dpidToDatapath[switch]
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser
        actions = [ofp_parser.OFPActionOutput(outPort)]
        match_ip = ofp_parser.OFPMatch(
            eth_type=0x0800,
            ipv4_src=ip_src,
            ipv4_dst=ip_dst
        )
        match_arp = ofp_parser.OFPMatch(
            eth_type=0x0806,
            arp_spa=ip_src,
            arp_tpa=ip_dst
        )
        self.mod_flow(dp, 32768, match_ip, actions)

    def delFlowSpecificSwitch(self, switch, ip_src, ip_dst):
        dp = self.dpidToDatapath[switch]
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser
        match_ip = ofp_parser.OFPMatch(
            eth_type=0x0800,
            ipv4_src=ip_src,
            ipv4_dst=ip_dst
        )
        match_arp = ofp_parser.OFPMatch(
            eth_type=0x0806,
            arp_spa=ip_src,
            arp_tpa=ip_dst
        )
        self.del_flow(dp, match_ip)



    ################################ just for testing###################################################
    def reroutingSimulator(self):
        hub.sleep(20)
        self.rerouteNonLV('10.0.0.1', '10.0.0.4')
        while True:
            hub.sleep(10)
            self.rerouteNonLV('10.0.0.1', '10.0.0.4')
            hub.sleep(10)
            self.rerouteNonLV('10.0.0.4', '10.0.0.1')

    def getRandomPath(self, pathsWithCostForward, chosenflowPrev):
        pathsCleaned = copy.deepcopy(pathsWithCostForward)
        # comment: iteration via index -> so no ValueError possible
        i = 0
        # ignore already chosen flow
        for path in pathsCleaned:
            if (path[0] == chosenflowPrev):
                pathsCleaned.pop(i)
                # self.logger.info("Kicked Out: {}".format(path))
            i += 1
        # choose new flow randomly
        newChoice = random.choice(pathsCleaned)
        newPath = newChoice[0]
        return newPath

    def rerouteLV(self, src_ip, dst_ip):
        self.logger.info("Rerouting started")
        idForward = functions.buildConnectionBetweenHostsId(src_ip, dst_ip)
        self.logger.info("pathsperflow: {}".format(self.paths_per_flows))
        pathsWithCostForward = self.paths_per_flows[idForward]
        chosenflowForward = self.chosen_path_per_flow[idForward]
        # ignore already chosen flow
        pathsCleaned = copy.deepcopy(pathsWithCostForward)
        # comment: iteration via index -> so no ValueError possible
        i = 0
        for path in pathsCleaned:
            if (path[0] == chosenflowForward):
                pathsCleaned.pop(i)
                self.logger.info("Kicked Out: {}".format(path))
            i += 1
        # choose new flow randomly
        newPath = random.choice(pathsCleaned)
        self.logger.info("new PATH: {}".format(newPath))
        changeList = functions.getCommandsRerouting(copy.deepcopy(chosenflowForward), newPath[0])
        # insertcommands: (i, i+1)
        insertOperation, flowModOperations, deleteOperation = functions.retrieveOperations(changeList, newPath[0],
                                                                                           chosenflowForward)

        self.logger.info("Insert Operations: {}".format(insertOperation))
        self.logger.info("Mod Operations: {}".format(flowModOperations))
        self.logger.info("Delete Operations: {}".format(deleteOperation))


############### REST API ###################################################

class SimpleSwitchController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(SimpleSwitchController, self).__init__(req, link, data, **config)
        self.simple_switch_app = data[simple_switch_instance_name]

    @route('simpleswitch', url, methods=['GET'], )
    def get_param(self, req, **kwargs):

        simple_switch = self.simple_switch_app
        obj = kwargs["obj"]
        # if obj not in globals().keys():  # or new_value[key] not in globals().keys():
        #     return Response(status=404)
        if obj not in dir(self.simple_switch_app):  # or new_value[key] not in globals().keys():
            return Response(status=404)

        # body = json.dumps({obj: str_to_class(obj)})
        body = json.dumps({obj: getattr(self.simple_switch_app, obj)})
        return Response(content_type='application/json', body=body, charset='UTF-8')

    @route('simpleswitch', url, methods=['PUT'])
    def put_param(self, req, **kwargs):

        response = {}
        simple_switch = self.simple_switch_app
        obj = kwargs["obj"]
        try:
            new_value = req.json if req.body else {}
        except ValueError:
            raise Response(status=400)
        print("PUT  obj: {} new_value: {}".format(obj, new_value))

        # if key not in globals().keys():# or new_value[key] not in globals().keys():
        #     return Response(status=404)
        for key in new_value:
            if obj not in dir(self.simple_switch_app):
                return Response(status=404)

            try:
                # obj = str_to_class(key)
                obj = getattr(self.simple_switch_app, key)
                print("PUT  obj: {} old_value: {} new_value: {}".format(key, obj, new_value[key]))
                setattr(self.simple_switch_app, key, new_value[key])
                response[key] = new_value[key]
            except Exception as e:
                return Response(status=500)
        body = json.dumps(response)
        return Response(content_type='application/json', body=body, charset='UTF-8')