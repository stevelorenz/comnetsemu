from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.dpid import str_to_dpid
from ryu.lib.packet import ethernet, ipv4, udp
# from ryu.lib.packet import *
from ryu.app import simple_switch_13
from ryu.app.wsgi import ControllerBase
from ryu.app.wsgi import Response
from ryu.app.wsgi import route
from ryu.app.wsgi import WSGIApplication
from ryu.lib.packet import packet

from ryu.lib import hub
from operator import attrgetter, itemgetter
import copy
import struct
import sys
from functools import reduce
import os
import time
import atexit
import configparser
import json
import numpy as np
from scipy.stats import norm
from scipy.stats import nbinom
from scipy.stats import t
import math
from fractions import Fraction

import redundancy_calculator
import common


simple_switch_instance_name = 'simple_switch_api_app'
url = '/simpleswitch/params/{obj}'


class SimpleSwitchIgmp13(simple_switch_13.SimpleSwitch13):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(SimpleSwitchIgmp13, self).__init__(*args, **kwargs)
        self.config = configparser.ConfigParser()
        self.config.read('adapt_nc.cfg')

        self.mac_to_port = {}

        wsgi = kwargs['wsgi']
        wsgi.register(SimpleSwitchController,
                      {simple_switch_instance_name: self})

        self.datapaths = {}
        self.datapath_connections = {}
        self.stats = {}
        self.diff_stats = {}
        self.loss_hist = {}
        self.error_to_dpid = {}
        self.monitor_thread = hub.spawn(self._monitor)
        self.redundancy = 0

        self.PROTOCOL = self.config.get("Coding", "PROTOCOL")
        self.SYSTEMATIC = int(self.config.get("Coding", "SYSTEMATIC"))
        self.CODED = int(self.config.get("Coding", "CODED"))
        self.REDUNDANCY_MODE = self.config.get("Coding", "redundancy_mode")
        self.FIXED = float(self.config.get("Coding", "fixed"))
        self.TPPROTO = 17 # 6 TCP, 17 UDP

        self.SYMBOLS = self.config.get("Coding", "SYMBOLS")  # used in cmds.py
        self.PREDICTION_LEVEL = float(self.config.get("Measurement", "PREDICTION_LEVEL"))
        self.QOS_LEVEL = float(self.config.get("Measurement", "QOS_LEVEL"))
        # Z = norm.ppf(PREDICTION_LEVEL)
        self.hist_length = int(self.config.get("Measurement", "hist_length"))
        self.t_sn = t.ppf(self.PREDICTION_LEVEL, self.hist_length) / np.sqrt(self.hist_length)
        self.update_cycle = 1  # measurements per second

        self.loss_log_file_name = self.config.get("Measurement", "loss_log_file")
        self.write_to_log = "False"  # flag for either writing to log file or not
        # Note: has to be a string, idk if string to bool cast is possible
        if not self.loss_log_file_name == "":
            self.logger.info("Log loss measurement to: {}".format(self.loss_log_file_name))
            self.loss_log_file = open(self.loss_log_file_name, "a+")
            self.loss_log_file.write(
                "#START,SYMBOLS={},QOS_LEVEL={},PREDICTION_LEVEL={}\n".format(self.SYMBOLS, self.QOS_LEVEL,
                                                                       self.PREDICTION_LEVEL))
            # self.loss_log_file.write("time,last_measure,prediction\n")
            self.loss_log_file.flush()
        else:
            self.loss_log_file = False

        self.config_pkt = packet.Packet()
        self.config_pkt.add_protocol(ethernet.ethernet(ethertype=0x07c3,
                                           dst='ff:ff:ff:ff:ff:ff',
                                           src='00:00:00:00:00:0c'))
        self.config_pkt.add_protocol(ipv4.ipv4(dst="255.255.255.255",
                                   src="0.0.0.0",
                                   proto=ipv4.udp))
        self.config_pkt.add_protocol(udp.udp(dst_port=UDP_PORT_OAM))

        atexit.register(self.__del__)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser


        self.logger.info("Connected to switch: Address {} ID {}".format(datapath.address, datapath.id))

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        # Encode flows

        if self.TPPROTO == 17:
            kwargs = {"udp_dst": 5001}
        elif self.TPPROTO == 6:
            kwargs = {"tcp_dst": 5001}
        else:
            self.logger.error("Unknown transport protocol")
            raise Exception

        if str(datapath.id) == "1":  # Encoder
            match = parser.OFPMatch(in_port=2, eth_type=0x0800, ip_proto=self.TPPROTO, **kwargs)
            actions = [parser.OFPActionOutput(3)]
            self.add_flow(datapath, 65535, match, actions)

            match = parser.OFPMatch(in_port=3, eth_type=0x0800, ip_proto=17, udp_dst=5001)
            actions = [parser.OFPActionOutput(1)]
            self.add_flow(datapath, 65535, match, actions)

            match = parser.OFPMatch(in_port=1, eth_type=0x0800)
            actions = [parser.OFPActionOutput(2)]
            self.add_flow(datapath, 65535, match, actions)
            self.logger.info("added encode flow to switch %s", datapath.id)


        # Decode flows
        else:
            match = parser.OFPMatch(in_port=1, eth_type=0x0800, ip_proto=17, udp_dst=5001)
            actions = [parser.OFPActionOutput(3)]
            self.add_flow(datapath, 65535, match, actions)

            match = parser.OFPMatch(in_port=3, eth_type=0x0800, ip_proto=self.TPPROTO, **kwargs)
            actions = [parser.OFPActionOutput(2)]
            self.add_flow(datapath, 65535, match, actions)

            match = parser.OFPMatch(in_port=2, eth_type=0x0800, ip_proto=self.TPPROTO, **kwargs)
            actions = [parser.OFPActionOutput(1)]
            self.add_flow(datapath, 65535, match, actions)

            link = 's1-s2'
            self.loss_hist[link] = [0.0]
            self.logger.info("added decode flow to switch %s", datapath.id)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)
        return

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        if out_port == "dismiss":
            actions = []
        else:
            actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            print("in_port: ", in_port, " out_port: ", out_port)
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            self.add_flow(datapath, 1, match, actions)
        else:
            # print("Flood packet")
            pass
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
                self.stats[datapath.id] = {}
                self.diff_stats[datapath.id] = {}

        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]
                del self.stats[datapath.id]
                del self.diff_stats[datapath.id]

    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(self.update_cycle)
            # TODO: count bytes instead of packets? (unequal packet sizes??)
            # nc -U /run/nc3.sock       set redundancy=3
            # /home/justus/Programs/ncnet/build/bin/ncctl -C run/nc{number}.sock set redundancy=3
            try:
                # self.logger.info('stats: {}'.format(self.stats.items()))
                # self.logger.info('diff_stats: {}'.format(self.diff_stats.items()))
                self.logger.info('Link        tx-pkts '
                                 '  rx-pkts diff-tx-pkts '
                                 'diff-rx-pkts diff-lost-pkts loss_rate loss_mean loss_std pred_loss')
                self.logger.info('--------- --------- '
                                 '--------- ------------ '
                                 '------------ -------------- --------- --------- -------- ---------')
                for dpid in self.stats:
                    if dpid == str_to_dpid("0000000000000001"):
                        link = 's1-s2'

                        # TODO: this should be dependent if with or without recoding
                        # self.logger.info("error_to_dpid: {}".format(self.error_to_dpid))
                        try:
                            pred_loss = self.error_to_dpid[link]
                        except KeyError:
                            # no value yet
                            continue

                        if self.REDUNDANCY_MODE == "dynamic":
                            pred_loss = float(str(pred_loss))  # problem with numpy
                            if pred_loss == 0.0:
                                pred_loss = 0.0000001
                            elif pred_loss >= 0.95:
                                pred_loss = 0.95
                            if str(pred_loss) == "NaN" or pred_loss < 0.0:
                                pred_loss = 0.0

                            self.redundancy = redundancy_calculator.systematic_redundancy(
                                int(self.SYMBOLS), 1 - pred_loss,
                                qos=self.QOS_LEVEL) - int(self.SYMBOLS)


                            # TODO:just for testing
                            self.logger.info("pred_loss: {} qos_level: {}".format(pred_loss, self.QOS_LEVEL))
                            self.logger.info(
                                "SYMBOLS: {}  REDUNDANCY:  {}".format(self.SYMBOLS, self.redundancy))

                            if str(self.redundancy) == "nan":
                                continue
                            elif self.redundancy < 0:
                                self.redundancy = 0

                            self._set_redundancy(dpid, self.redundancy)

                            if self.loss_log_file and self.write_to_log == "True":
                                self._write_to_logfile(link, pred_loss)


                        elif self.REDUNDANCY_MODE == "fixed":
                            if self.PROTOCOL == "noack" or self.PROTOCOL == "nocode":

                                self.redundancy = int(round(int(self.SYMBOLS) * (float(self.FIXED) - 1)))

                                # if self.redundancy == 0:
                                #     self.redundancy = 1

                                # TODO:just for testing
                                self.logger.info("redundancy mode: {}".format(self.REDUNDANCY_MODE))
                                self.logger.info(
                                    "SYMBOLS: {}  REDUNDANCY:  {} FIXED: {}".format(self.SYMBOLS, self.redundancy,self.FIXED))

                                nc = "enc"
                                stdin, stdout, stderr = self.datapath_connections[dpid].exec_command(
                                    '/home/justus/Programs/ncnet/build/bin/ncctl -C /run/nc{}.sock set redundancy={}'.format(
                                        nc, self.redundancy))
                                stdout.readlines()
                                # self.logger.info("stdout: {} stderr: {}".format(stdout.read(), stderr.read()))

                                stdin, stdout, stderr = self.datapath_connections[dpid].exec_command(
                                    'echo \"set redundancy={}\" >> /tmp/nc{}.sock.txt'.format(
                                        self.redundancy, nc))
                                stdout.readlines()

                                if self.loss_log_file and self.write_to_log == "True":
                                    self._write_to_logfile(link, pred_loss)

                            else:
                                self.logger.error("Specify NC protocol")
                        else:
                            self.logger.error('Specify redundancy mode')
                        continue

                    elif "{:0>16}".format(str(dpid)) == '0000000000000002':
                        link = 's1-s2'
                        tx = self.stats[str_to_dpid('0000000000000001')][1]['tx-pkts']
                        diff_tx = self.diff_stats[str_to_dpid('0000000000000001')][1]['tx-pkts']
                        rx = self.stats[str_to_dpid('0000000000000002')][1]['rx-pkts']
                        diff_rx = self.diff_stats[str_to_dpid('0000000000000002')][1]['rx-pkts']

                        losses = diff_tx - diff_rx
                        if not diff_tx > 100:
                            pass
                        else:
                            loss_rate = float(losses) / diff_tx
                            self.loss_hist[link].insert(0, loss_rate)  # TODO: truncate array
                            del self.loss_hist[link][self.hist_length:]

                        mean = np.mean(self.loss_hist[link])  # TODO: how many measurements?
                        if str(mean) == "nan":
                            mean = 0.0
                        std = np.std(self.loss_hist[link], ddof=1)
                        if str(std) == "nan":
                            std = 0.0
                        self.T_a = t.ppf(self.PREDICTION_LEVEL, self.hist_length - 1)  # for one-sided interval
                        pred_loss = mean + self.T_a * math.sqrt(1 + (1.0 / self.hist_length)) * std
                        self.error_to_dpid[link] = pred_loss

                        self.logger.info(
                            '{:>9} {:>9} {:>9} {:>12} {:>12} {:>14} {:>9.3f} {:>9.3f} {:>8.3f} {:>9.3f}'.format(link,
                                                                                                                tx,
                                                                                                                rx,
                                                                                                                diff_tx,
                                                                                                                diff_rx,
                                                                                                                losses,
                                                                                                                self.loss_hist[
                                                                                                                    link][
                                                                                                                    -1],
                                                                                                                mean,
                                                                                                                std,
                                                                                                                pred_loss))
                    else:
                        continue


            except Exception as e:
                self.logger.info("Error in loss rate calculation: {}".format(e))
                self.logger.info("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
                # pass
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                self.logger.info("Additional info: {} {} {}".format(exc_type, fname, exc_tb.tb_lineno))


    def _set_redundancy(self, datapath, redundancy):
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        pkt = copy.deepcopy(self.config_pkt)
        pkt.add_protocol(struct.pack(">B", redundancy))
        pkt.serialize()
        data = pkt.data
        buffer_id = 0xffffffff
        in_port = 0xfffffffd
        actions = [ofp_parser.OFPActionOutput(ofp.OFPP_FLOOD, 0)]
        req = ofp_parser.OFPPacketOut(datapath, buffer_id,
                                      in_port, actions, data)
        datapath.send_msg(req)

    def _request_stats(self, datapath):
        self.logger.debug('send stats request: %016x', datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        return
        body = ev.msg.body

        self.logger.info('datapath         '
                         'in-port  eth-dst           '
                         'out-port packets  bytes')
        self.logger.info('---------------- '
                         '-------- ----------------- '
                         '-------- -------- --------')
        for stat in sorted([flow for flow in body if flow.priority == 1],
                           key=lambda flow: (flow.match['in_port'],
                                             flow.match['eth_dst'])):
            self.logger.info('%016x %8x %17s %8x %8d %8d',
                             ev.msg.datapath.id,
                             stat.match['in_port'], stat.match['eth_dst'],
                             stat.instructions[0].actions[0].port,
                             stat.packet_count, stat.byte_count)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        body = ev.msg.body
        for stat in sorted(body, key=attrgetter('port_no')):

            self.diff_stats[ev.msg.datapath.id][stat.port_no] = {'rx-pkts': 0, 'tx-pkts': 0,
                                                                 'rx-error': 0, 'tx-errors': 0}
            try:
                self.diff_stats[ev.msg.datapath.id][stat.port_no]['rx-pkts'] = stat.rx_packets - \
                                                                               self.stats[ev.msg.datapath.id][
                                                                                   stat.port_no][
                                                                                   'rx-pkts']
                self.diff_stats[ev.msg.datapath.id][stat.port_no]['tx-pkts'] = stat.tx_packets - \
                                                                               self.stats[ev.msg.datapath.id][
                                                                                   stat.port_no]['tx-pkts']
                self.diff_stats[ev.msg.datapath.id][stat.port_no]['rx-error'] = stat.rx_errors - \
                                                                                self.stats[ev.msg.datapath.id][
                                                                                    stat.port_no][
                                                                                    'rx-error']
                self.diff_stats[ev.msg.datapath.id][stat.port_no]['tx-errors'] = stat.tx_errors - \
                                                                                 self.stats[ev.msg.datapath.id][
                                                                                     stat.port_no]['tx-errors']
            except Exception as e:
                self.logger.info("Error in port_stats_reply_handler: {}".format(e))
                self.logger.info("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
                # pass
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                self.logger.info("Additional info: {} {} {}".format(exc_type, fname, exc_tb.tb_lineno))

            self.stats[ev.msg.datapath.id][stat.port_no] = {'rx-pkts': stat.rx_packets, 'tx-pkts': stat.tx_packets,
                                                            'rx-error': stat.rx_errors, 'tx-errors': stat.tx_errors}

    def _write_to_logfile(self, link, pred_loss):
        # timestamp = str(datetime.datetime.now())
        timestamp = time.time()
        # Could save statistics per link
        self.logger.info("Error_log: {},{:7.5f},{:7.5f}\n".format(timestamp, self.loss_hist[link][0],
                                                                        pred_loss))
        if self.loss_log_file:
            self.loss_log_file.write(
                "{},{:7.5f},{:7.5f}\n".format(timestamp, self.loss_hist[link][0],
                                                    pred_loss))
            self.loss_log_file.flush()

    def __del__(self):
        self.logger.info("Cleaning up")
        if self.loss_log_file:
            self.loss_log_file.close()


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


# https://stackoverflow.com/questions/1176136/convert-string-to-python-class-object
def str_to_class(str):
    # similiar to eval()
    return reduce(getattr, str.split("."), sys.modules[__name__])


def str_to_class_and_modify(str):
    # similiar to eval()
    return reduce(getattr, str.split("."), sys.modules[__name__])