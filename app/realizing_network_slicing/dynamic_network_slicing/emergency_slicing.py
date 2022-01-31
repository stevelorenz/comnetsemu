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
from ryu.lib.packet import icmp
import subprocess
import time
import threading

class TrafficSlicing(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TrafficSlicing, self).__init__(*args, **kwargs)

        # Destination Mapping [router --> MAC Destination --> Eth Port Output]
        self.mac_to_port = {
            1: {"00:00:00:00:00:01": 2, "00:00:00:00:00:02": 3, "00:00:00:00:00:03": 4, "00:00:00:00:00:04": 1, "00:00:00:00:00:05": 1, "00:00:00:00:00:06": 1},
            2: {"00:00:00:00:00:04": 2, "00:00:00:00:00:05": 3, "00:00:00:00:00:06": 4, "00:00:00:00:00:01": 1, "00:00:00:00:00:02": 1, "00:00:00:00:00:03": 1},
        }
        
        self.emergency = 0          # Boolean that indicates the presence of an emergency scenario
        self.time = time.time()     # Timer that keeps track of time for an emergency scenario
        
        self.print_flag = 0         # Helper variable that helps us with printing/output
        
        # Creation of an additional thread that automates the process for Emergecy Scenario and Normal Scenario!
        # Listens to the timer() function.  
        self.threadd = threading.Thread(target=self.timer, args=())
        self.threadd.daemon = True
        self.threadd.start()

        # Source Mapping        
        self.port_to_port = {
            1: {2:1, 3:1, 4:1},
            2: {2:1, 3:1, 4:1},
        }
        self.end_swtiches = [1, 4]
        


    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install the table-miss flow entry.
        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # construct flow_mod message and send it.
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath, priority=priority, match=match, instructions=inst
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
        in_port = msg.match["in_port"]

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        
        dst = eth.dst
        src = eth.src
        
        dpid = datapath.id
        
        if dpid in self.mac_to_port:
            if (self.emergency == 1): # Emergency Scenario - Create New Topology
                
                if dst in self.mac_to_port[dpid]:
                    out_port = self.mac_to_port[dpid][dst]
                    actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
                    match = datapath.ofproto_parser.OFPMatch(eth_dst=dst)
                    self.add_flow(datapath, 1, match, actions)
                    self._send_package(msg, datapath, in_port, actions)


                
            else:                    
                if dst in self.mac_to_port[dpid]:
                    out_port = self.mac_to_port[dpid][dst]
                    actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
                    match = datapath.ofproto_parser.OFPMatch(eth_dst=dst)
                    self.add_flow(datapath, 1, match, actions)
                    self._send_package(msg, datapath, in_port, actions)

                    
    # Function that automates the alternation between Emergency and Non-Emergency Scenario                
    def timer(self):
        while True:
            time.sleep(60)                              # For 40 seconds we have the Normal/Non-Emergency Scenario
            print()
            print('                ***Emergency***                ')
            self.emergency = 1
            subprocess.call("./sos_scenario.sh")        # Creating the third slice
            self.print_flag = 0
            time.sleep(60)                              # For 40 seconds we have the Emergency Scenario
            print(' ')
            print('Update: 60 seconds have passed.')
            print('Ending the Emergency Scenario...')
            print('Recreate the initial Network Slicing...')
            print(' ')    
            subprocess.call("./common_scenario.sh")     # End of Emergency - Return to 2 slices
            self.emergency = 0
            self.time = time.time()

                    
                