import time
from collections import defaultdict
import random
#from remote_controller_RL import ControllerMain
REFERENCE_BW = 10000000
# maximum possible paths to choose from, IMPORTANT!!! can control how useful paths are
MAX_PATHS = 100

class RoutingDFS():
    def __init__(self):
        print("")

    # gives back paths and optimal path
    def get_optimal_path (self, controller, src, dst):
        pathsOptimal, paths = self.get_optimal_paths(controller, src, dst)
        pathOptimal = pathsOptimal[0]
        return pathOptimal, paths

    def install_path(self, controller, chosenPath, first_port, last_port, ip_src, ip_dst, type):

        path = self.add_ports_to_path(controller, chosenPath, first_port, last_port)
        #switches_in_paths = set().union(*chosenPath)

        for node in chosenPath:
            dp = controller.dpidToDatapath[node]
            ofp = dp.ofproto
            ofp_parser = dp.ofproto_parser
            ports = defaultdict(list)
            actions = []

            if node in path:
                in_port = path[node][0]
                out_port = path[node][1]
                if out_port not in ports[in_port]:
                    ports[in_port].append(out_port)

            for in_port in ports:
                out_ports = ports[in_port]
                actions = [ofp_parser.OFPActionOutput(out_ports[0])]
                controller.add_flow(dp, self.get_priority(type), self.get_match(type, ofp_parser, ip_src, ip_dst), actions)

    def get_match(self, type, ofp_parser, ip_src, ip_dst):
        if type == 'ipv4':
            match_ip = ofp_parser.OFPMatch(
                eth_type=0x0800,
                ipv4_src=ip_src,
                ipv4_dst=ip_dst
            )
            return match_ip
        if type == 'arp':
            match_arp = ofp_parser.OFPMatch(
                eth_type=0x0806,
                arp_spa=ip_src,
                arp_tpa=ip_dst
            )
            return match_arp

    def get_priority(self, type):
        if type == 'ipv4':
            return 1
        if type == 'arp':
            return 32768
        return 32768

    def get_paths(self, controller, src, dst):
            '''
            Get all paths from src to dst using DFS algorithm
            '''
            if src == dst:
                # host target is on the same switch
                return [[src]]
            paths = []
            stack = [(src, [src])]
            while stack:
                (node, path) = stack.pop()
                for next in set(controller.latencyDict[node].keys()) - set(path):
                    if next is dst:
                        paths.append(path + [next])
                    else:
                        stack.append((next, path + [next]))
            return paths

    # can also be changed to BWs, or to hops
    def get_link_cost(self, controller, s1, s2):
        # only latency:
        ew = controller.latencyDict[s2][s1]
        return ew

    def get_path_cost(self, controller, path):
        cost = 0
        for i in range(len(path) - 1):
            cost += self.get_link_cost(controller, path[i], path[i+1])
        return cost

    # Add the ports that connects the switches for all paths
    def add_ports_to_path(self, controller, path, first_port, last_port):
        p = {}
        in_port = first_port
        for s1, s2 in zip(path[:-1], path[1:]):
            out_port = controller.data_map[s1][s2]['in_port']
            p[s1] = (in_port, out_port)
            in_port = controller.data_map[s2][s1]['in_port']
        p[path[-1]] = (in_port, last_port)
        return p

    def get_optimal_paths(self, controller, src, dst):
        paths = self.get_paths(controller, src, dst)
        paths_count = len(paths) if len(
            paths) < MAX_PATHS else MAX_PATHS
        return sorted(paths, key=lambda x: self.get_path_cost(controller, x))[0:(paths_count)], paths

    ''' 
    def install_paths(self, controller, src, first_port, dst, last_port, ip_src, ip_dst, noBackward):


      pw = []
      for path in pathOptimal:
          pw.append(self.get_path_cost(controller, path))
          #print(path, "cost = ", pw[len(pw) - 1])


      #controller.logger.info("paths: {}, switches: {}".format(pathsOptimal, switches_in_paths))

      connections_in_path = []
      i=0
      for node in switches_in_paths:
          #if (i>0):
          #    connections_in_path.append((switches_in_paths[i-1],node))
          dp = controller.dpidToDatapath[node]
          ofp = dp.ofproto
          ofp_parser = dp.ofproto_parser

          ports = defaultdict(list)
          actions = []
          i = 0

          for path in paths_with_ports:
              if node in path:
                  in_port = path[node][0]
                  out_port = path[node][1]
                  if (out_port, pw[i]) not in ports[in_port]:
                      ports[in_port].append((out_port, pw[i]))
              i += 1

          for in_port in ports:
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
              out_ports = ports[in_port]

              if len(out_ports) > 1:
                  actions = []
                  if noBackward:
                      controller.add_flow(dp, 32768, match_ip, actions)
                  controller.add_flow(dp, 1, match_arp, actions)
              elif len(out_ports) == 1:
                  actions = [ofp_parser.OFPActionOutput(out_ports[0][0])]
                  if noBackward:
                      controller.add_flow(dp, 32768, match_ip, actions)
                  controller.add_flow(dp, 1, match_arp, actions)
      return paths_with_ports[0][src][1], paths, pathOptimal[0]
      
          
      '''
