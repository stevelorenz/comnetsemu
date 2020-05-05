from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3


class Hub(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Hub, self).__init__(*args, **kwargs)

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
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=0,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

    # register an event handler
    # EventOFPPacketIn is triggered when a switch sends a packet_in message
    # MAIN_DISPATCHER just means that the switch is fully configured
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        # the message sent by the switch
        msg = ev.msg
        # the connection to the switch
        dp = msg.datapath
        # OpenFlow protocol
        ofproto = dp.ofproto
        # constructs and deconstructs OpenFlow messages
        ofp_parser = dp.ofproto_parser
        # port number of incoming packet
        in_port = msg.match['in_port']

        # let's output some message
        self.logger.debug('packet from %016x at port %d (length %d)' % (dp.id, in_port, msg.msg_len))

        # here we gather the actions the switch should execute with the packet
        # OFPActionOutput instructs the switch to send the message to an output port
        # OFPP_FLOOD is a special output port for sending on all output ports
        actions = [ofp_parser.OFPActionOutput(ofproto.OFPP_FLOOD)]

        # if the packet is not in the switch buffer, include it in the PacketOut message
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        # we put the actions into a packet_out message
        # the message also contains
        out = ofp_parser.OFPPacketOut(
            datapath=dp,  # assign the message to the switch
            buffer_id=msg.buffer_id,  # reflect the id assigned by the switch
            in_port=in_port,  # input port
            actions=actions,  # our list of actions
            data=data)  # send the packet back

        # send the message to the switch
        dp.send_msg(out)
