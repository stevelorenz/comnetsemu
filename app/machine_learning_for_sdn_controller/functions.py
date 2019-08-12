import numpy as np
from heapq import *
import math

#choices: 'latencyEchoRTT', 'bw'
def create_matrix(data_map, choice):
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
            # TODO: FALSCH
    return map

def convertMatrixToDict(matrix):
    dict_build = {}
    lenghtMatrix = len(matrix)
    for i in range(lenghtMatrix):
        for j in range(lenghtMatrix):
            if matrix[i, j] > 0:
                if (i + 1) not in dict_build:
                    dict_build[i + 1] = {}
                dict_build[i + 1][j + 1] = matrix[i, j]
    return dict_build

def convertDataMapToDict(dataMap, choice):
    dictBuild = {}
    for key1 in dataMap.keys():
        dictBuild[key1] = {}
        for key2 in dataMap[key1].keys():
            #if key2 not in dictBuild[key1].keys():
            #    dictBuild[key1] = {}
            dictBuild[key1][key2] = dataMap[key1][key2][choice][-1]['value']
    return dictBuild

def installingPaths(controller, path, firstPort, lastPort, ipSrc, ipDst):
    p = mapPortsToPath(controller, path, firstPort, lastPort)
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

def mapPortsToPath(controller, path, firstPort, lastPort):
    #
    p= {}
    in_port = firstPort
    #controller.logger.info("data_map: {}".format(controller.data_map))
    #controller.logger.info("P1: {}".format(path[:-1]))
    #controller.logger.info("P2: {}".format(path[1:]))
    #controller.logger.info("ZIP FORMAT: {}".format(str(zip(path[:-1], path[1:]))))
    #zip builds a set
    for s1, s2 in zip(path[:-1], path[1:]):
        # TODO: check dass nicht vertauscht
        out_port = controller.data_map[s1][s2]['in_port']
        p[s1] = (in_port, out_port)
        in_port = controller.data_map[s2][s1]['in_port']
        #controller.logger.info("OUT_PORT: {}".format(out_port))
        #controller.logger.info("IN_PORT: {}".format(in_port))
    p[path[-1]]= (in_port, lastPort)
    #controller.logger.info("matched ports to switch {}: {}".format(s1, p[s1]))
    return p

def buildConnectionBetweenHostsId(srcIP, dstIP):
    #return '{}'.format(srcIP.split('.')[-1]+'.'+dstIP.split('.')[-1])
    return '{}'.format(srcIP + '_' + dstIP)

def buildIpAdresses(idConn):
    strId = str(idConn)
    split = strId.split("_")
    srcIP = split[0]
    dstIP = split[1]
    #lastSrcIP = split[0]
    #ĺastDstIP = split[1]
    #srcIP = "10.0.0.{}".format(lastSrcIP)
    #dstIP = "10.0.0.{}".format(ĺastDstIP)
    return srcIP, dstIP

def getCommandsRerouting(oldPath, newPath):
    print('OldPath: {} NewPath: {}'.format(oldPath, newPath))
    npArray = np.array(iterative_levenshtein(newPath, oldPath))
    print("ArrayLevenstein: {}".format(npArray))
    aStar = astar(npArray, (0,0),(len(newPath), len(oldPath)))
    aStar.append((0, 0))
    print(aStar)
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
    print(changelist)
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
def retrieveOperations(changeList, newPath, oldPath):
    insertList = []
    deleteList = []
    deleteListSwitches = []
    flowAddOperations = []
    flowModOperations = []
    modList = []
    i = 0
    for change in changeList:
        operation = change[0]
        # substitution
        if(operation == 0):
            modList.append(change[1])
        elif(operation == 1):
            insertList.append(change[1])
            deleteList.append(change[2])
        elif (operation == 2):
            insertList.append(change[1])
        elif (operation == 3):
            deleteList.append(change[2])

    print("ModList: {}".format(modList))
    print("InsertList: {}".format(insertList))
    print("DeleteList: {}".format(deleteList))
    print("OldPath: {}".format(oldPath))

    for element in insertList:
        currentIndex = element-1
        if currentIndex < (len(newPath) - 1):
            following = newPath[currentIndex + 1]
            if(currentIndex>0):
                flowAddOperations.append([element, following])
                # no change before, do it at last

    # if next element of the path is in inserting
    # change it at last
    for element in modList:
        currentIndex = element - 1
        if currentIndex < (len(newPath) - 1):
            print("new Path: {}, current Index: {}".format(newPath, currentIndex))
            followingIndex = currentIndex + 1
            following = newPath[followingIndex]
            if followingIndex in insertList:
                flowModOperations.append([element, following])

    for element in deleteList:
        print("Delete index old: {}".format(element))
        switch = oldPath[element]
        deleteListSwitches.append(switch)
    print("Delete list switches: {}".format(deleteListSwitches))
    return flowAddOperations, flowModOperations, deleteListSwitches

def getOutputPort(controller, s1, s2):
    return controller.data_map[s1][s2]['in_port']