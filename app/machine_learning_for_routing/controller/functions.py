import numpy as np
from heapq import *
import math


def create_matrix(data_map, choice):
    """
    Creates matrix from metrics
    :rtype: object
    """
    dimension = len(data_map.keys())
    s = (dimension, dimension)
    map = np.zeros(s)
    # with high dpids - order for list of keys
    keyList_sorted = sorted(list(data_map.keys()))
    # create new object
    i = 0
    keyDict = {}
    for element in keyList_sorted:
        keyDict[element] = i
        i = i + 1
    for key1 in data_map.keys():
        for key2 in data_map[key1].keys():
            map[keyDict[key1]][keyDict[key2]] = data_map[key1][key2][choice][-1]['value']
    return map

def convert_matrix_to_dict(matrix):
    """
    Converts matrix to dictionary
    :param matrix:
    :return:
    """
    dict_build = {}
    lenghtMatrix = len(matrix)
    for i in range(lenghtMatrix):
        for j in range(lenghtMatrix):
            if matrix[i, j] > 0:
                if (i + 1) not in dict_build:
                    dict_build[i + 1] = {}
                dict_build[i + 1][j + 1] = matrix[i, j]
    return dict_build

def convert_data_map_to_dict(dataMap, choice):
    """
    Creates dictionary of data_map
    :param dataMap:
    :param choice:
    :return:
    """
    dictBuild = {}
    for key1 in dataMap.keys():
        dictBuild[key1] = {}
        for key2 in dataMap[key1].keys():
            #if key2 not in dictBuild[key1].keys():
            #    dictBuild[key1] = {}
            dictBuild[key1][key2] = dataMap[key1][key2][choice][-1]['value']
    return dictBuild

def installingPaths(controller, path, firstPort, lastPort, ipSrc, ipDst):
    """
    Modify the flow table entries on path
    :param controller:
    :param path:
    :param firstPort:
    :param lastPort:
    :param ipSrc:
    :param ipDst:
    """
    p = map_ports_to_path(controller, path, firstPort, lastPort)
    controller.logger.info("MAP TO PORTS: {}".format(p))
    # get DP from DPID for each switch
    for dpid in path:
        dp = controller.dpidToDatapath[dpid]
        #ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser

        match_ip = ofp_parser.OFPMatch(
            eth_type=0x0800,
            ipv4_src=ipSrc,
            ipv4_dst=ipDst
        )
        match_arp = ofp_parser.OFPMatch(
            eth_type=0x0806,
            arp_spa=ipSrc,
            arp_tpa=ipDst
        )
        in_port = p[dpid][0]
        out_port = p[dpid][1]
        actions = [ofp_parser.OFPActionOutput(out_port)]
        controller.logger.info("Added the crap sw: {} to port: {}".format(dpid, out_port))
        controller.add_flow(dp, 32768, match_ip, actions)
        controller.add_flow(dp, 1, match_arp, actions)

def map_ports_to_path(controller, path, firstPort, lastPort):
    """
    Returns path switch in path
    :param controller:
    :param path:
    :param firstPort:
    :param lastPort:
    :return:
    """
    #
    p = {}
    in_port = firstPort

    #zip builds a set
    for s1, s2 in zip(path[:-1], path[1:]):
        # TODO: check dass nicht vertauscht
        out_port = controller.data_map[s1][s2]['in_port']
        p[s1] = (in_port, out_port)
        in_port = controller.data_map[s2][s1]['in_port']
    p[path[-1]] = (in_port, lastPort)
    return p

def build_connection_between_hosts_id(srcIP, dstIP):
    """
    Creates identification of flows by the ip adresses
    :param srcIP:
    :param dstIP:
    :return:
    """
    return '{}'.format(srcIP + '_' + dstIP)

def build_ip_adresses(flow_id):
    """
    Returns ip addresses of an connection
    :param idConn:
    :return:
    """
    strId = str(flow_id)
    split = strId.split("_")
    srcIP = split[0]
    dstIP = split[1]

    return srcIP, dstIP

def get_commands_rerouting(oldPath, newPath):
    """
    Returns the mod/add/operations that are necessary to reroute the flows
    :param oldPath:
    :param newPath:
    :return:
    """
    print('OldPath: {} NewPath: {}'.format(oldPath, newPath))
    npArray = np.array(iterative_levenshtein(newPath, oldPath))
    print("ArrayLevenstein: {}".format(npArray))
    aStar = astar(npArray, (0, 0), (len(newPath), len(oldPath)))
    aStar.append((0, 0))
    # analyze:
    i = 0
    # tuple: (operation, index)
    changelist = []
    # 0 - no change
    # 1 - substitution
    # 2 - insert
    # 3 - delete
    # numpy: (zeile, spalte)
    for nextElement in aStar:
        if i > 0:
            previousElement = aStar[i - 1]
            # aenderung spalte deletion
            if (nextElement[1] < previousElement[1] and nextElement[0] < previousElement[0]):
                # no change
                if (npArray[nextElement[0]][nextElement[1]] == npArray[previousElement[0]][previousElement[1]]):
                    changelist.append((0, previousElement[0], previousElement[1]))
                else:
                    changelist.append((1, previousElement[0], previousElement[1]))
            elif (nextElement[1] == previousElement[1] and nextElement[0] < previousElement[0]):
                changelist.append((2, previousElement[0], previousElement[1]))
            elif (nextElement[1] < previousElement[1] and nextElement[0] == previousElement[0]):
                changelist.append((3, previousElement[0], previousElement[1]))
        i += 1

    # command, switch number
    preOperation = -1
    nextOperation = -1
    for change in changelist:
        operation = change[0]
        indexOld = change[2] - 1
        indexNew = change[1] - 1
        if operation == 0:
            print('noChange indexold: {}  Indexnew: {}'.format(indexOld, indexNew))
        elif operation == 1:
            # put it into changelast
            print('substitute: {} from {}'.format(indexOld, indexNew))
            oldPath[indexOld] = newPath[indexNew]
            opPrev = 1
        elif operation == 2:
            print('insert from {} to {}'.format(indexOld, indexNew))
            oldPath.insert(indexOld + 1, newPath[indexNew])
            opPrev = 1
        elif operation == 3:
            print('delete from: {}'.format(indexOld))
            oldPath.pop(indexOld)
            opPrev = 1
    print(oldPath)
    print(newPath)
    return changelist

def get_link_cost(latency_dict, s1, s2):
    """
    Link cost of a link between two switches
    :param latency_dict:
    :param s1:
    :param s2:
    :return:
    """
    # only latency:
    ew = latency_dict[s2][s1]
    return ew

def get_path_cost(latency_dict, path):
    """
    Cost of all links over a path combined
    :param latency_dict:
    :param path:
    :return:
    """
    cost = 0
    for i in range(len(path) - 1):
        cost += get_link_cost(latency_dict, path[i], path[i+1])
    return cost

def filter_paths(latencyDict, paths, max_possible_paths):
    """
    filter paths for latency
    returns maximum
    :rtype: object
    """
    best_paths = []
    for path in paths:
        best_paths.append((path, get_path_cost(latencyDict, path)))
    # sorted(best_paths, key= scndElement)
    sorted(best_paths, key=lambda scndElement: scndElement[1])

    print("PATHS: {}".format(paths))
    return [path[0] for path in best_paths[:max_possible_paths]]


#########################
# Rerouting Levensteihn #
#########################
def iterative_levenshtein(s, t):
    """
        iterative_levenshtein(s, t) -> ldist
        ldist is the Levenshtein distance between the strings
        s and t.
        For all i and j, dist[i,j] will contain the Levenshtein
        distance between the first i characters of s and the
        first j characters of t
    """
    rows = len(s) + 1
    cols = len(t) + 1
    dist = [[0 for x in range(cols)] for x in range(rows)]
    # source prefixes can be transformed into empty strings
    # by deletions:
    for i in range(1, rows):
        dist[i][0] = i
    # target prefixes can be created from an empty source string
    # by inserting the characters
    for i in range(1, cols):
        dist[0][i] = i

    for col in range(1, cols):
        for row in range(1, rows):
            if s[row - 1] == t[col - 1]:
                cost = 0
            else:
                cost = 1
            dist[row][col] = min(dist[row - 1][col] + 1,        # deletion
                                 dist[row][col - 1] + 1,         # insertion
                                 dist[row - 1][col - 1] + cost)  # substitution
    return dist

def heuristic(a, b):
    #return (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2
    # euclidian
    return math.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)

def astar(array, start, goal):
    #neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
    #neighbors = [(0, -1), (-1, 0),  (-1, -1)]
    # with diagonal
    neighbors = [(0, 1), (1, 0), (1, 1)]
    #without diagonal
    #neighbors = [(0, 1), (1, 0)]
    close_set = set()
    came_from = {}
    gscore = {start: 0}
    fscore = {start: heuristic(start, goal)}
    oheap = []
    heappush(oheap, (fscore[start], start))
    while oheap:
        current = heappop(oheap)[1]
        if current == goal:
            data = []
            while current in came_from:
                data.append(current)
                current = came_from[current]
            return data
        close_set.add(current)
        for i, j in neighbors:
            neighbor = current[0] + i, current[1] + j
            tentative_g_score = gscore[current] + heuristic(current, neighbor)
            if 0 <= neighbor[0] < array.shape[0] and 0 <= neighbor[1] < array.shape[1]:
                if neighbor in close_set and tentative_g_score >= gscore.get(neighbor, 0):
                    continue
                if tentative_g_score < gscore.get(neighbor, 0) or neighbor not in [i[1] for i in oheap]:
                    came_from[neighbor] = current
                    # should go as fast as possible to small values
                    neighbor_difference = array[neighbor[0]][neighbor[1]]
                    #array[neighbor[0]][neighbor[1]] - array[current[0]][current[1]]
                    gscore[neighbor] = tentative_g_score + neighbor_difference
                    fscore[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                    heappush(oheap, (fscore[neighbor], neighbor))
    return False

# 0 - no change
# 1 - substitution
# 2 - insert
# 3 - delete
def retrieve_operations(changeList, new_path, old_path):
    """
    get changes in flow table from operation code
    :param changeList:
    :param new_path:
    :param old_path:
    :return:
    """
    insert_list = []
    delete_list = []
    delete_list_switches = []
    flow_add_operations = []
    flow_mod_operations = []
    mod_list = []
    i = 0
    for change in changeList:
        operation = change[0]
        # substitution
        if(operation == 0):
            mod_list.append(change[1])
        elif(operation == 1):
            insert_list.append(change[1])
            delete_list.append(change[2])
        elif (operation == 2):
            insert_list.append(change[1])
        elif (operation == 3):
            delete_list.append(change[2])

    print("ModList: {}".format(mod_list))
    print("InsertList: {}".format(insert_list))
    print("DeleteList: {}".format(delete_list))
    print("OldPath: {}".format(old_path))

    for element in insert_list:
        current_index = element-1
        if current_index < (len(new_path) - 1):
            following = new_path[current_index + 1]
            if(current_index>0):
                flow_add_operations.append([element, following])
                # no change before, do it at last

    # if next element of the path is in inserting
    # change it at last
    for element in mod_list:
        current_index = element - 1
        if current_index < (len(new_path) - 1):
            print("new Path: {}, current Index: {}".format(new_path, current_index))
            following_index = current_index + 1
            following = new_path[following_index]
            if following_index in insert_list:
                flow_mod_operations.append([element, following])

    for element in delete_list:
        print("Delete index old: {}".format(element))
        switch = old_path[element]
        delete_list_switches.append(switch)
    print("Delete list switches: {}".format(delete_list_switches))
    return flow_add_operations, flow_mod_operations, delete_list_switches

def get_output_port(controller, s1, s2):
    """
    Gets output port of a switch2switch connection
    :param controller:
    :param s1:
    :param s2:
    :return:
    """
    return controller.data_map[s1][s2]['in_port']

def check_new_measurement(timestamp, last_measurement):
    """
    checks if latency measurements have been made for the last state
    @param timestamp:
    @param last_measurement:
    @return:
    """
    for dpid_rec in last_measurement:
        for dpid_sent in last_measurement[dpid_rec]:
            if last_measurement[dpid_rec][dpid_sent] < timestamp:
                return False
    return True

def create_average_latency_dict_from_list(dict_list):
    """
    Calculates the average latency
    :param dict_list:
    :return:
    """
    mean_dict = {}
    for key in list(dict_list[0].keys()):
        mean_dict[key] = {}
        for key2 in list(dict_list[0][key].keys()):
            mean_dict[key][key2] = sum(d[key][key2] for d in dict_list) / len(dict_list)
    return mean_dict