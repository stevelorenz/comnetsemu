from enum import Enum
import time
import os
import copy
import math
import itertools as it
import numpy as np
import json
# for communication between mininet and ryu
import random
import sys
import csv
sys.path.append("..")
sys.path.append(".")
from config import Config

# different possible modes
class QMode(Enum):
    SHORTEST_PATH = -1
    MULTI_ARMED_BANDIT_NO_WEIGHT = 1
    MULTI_ARMED_BANDIT_WITH_WEIGHT = 2
    Q_LEARNING = 3

class ExplorationMode(Enum):
    CONSTANT_EPS = 0
    FALLING_EPS = 1

MAX_LENGHT_DIFFSET = 2
MAX_PAST_REWARDS = 5
# modes:

###############################################################
########## Class for learning started by controller############
###############################################################

def learningModule(pipe, ):
    print('process id:', os.getpid())
    #### RL Parameters
    # learning rate alpha
    alpha = Config.alpha
    # discount factor gamma
    gamma = Config.gamma
    # exploration probability epsilon (0-1.0)
    epsilon = Config.epsilon
    # leanring mode: q-leanring, multiarmed bandit (constant )
    learning_mode = Config.qMode
    # defines if the exploration is eps_greedy constant, with falling eps or softmax
    exploration_mode = Config.exploration_mode

    # time steps that need to be waited until reward can be gathered
    # necessary because of the delayed reward
    delayedRewardCounter = 0
    # list of currently installed flows
    # necessary to check if new flows joined
    tempFlows = []
    # Q - Table
    Q = {}
    # how many rewards are gathred before considering taking a new action
    measurements_for_reward = Config.measurements_for_reward
    # how long to wait until starting to gather new rewards
    delay_reward = Config.delay_reward
    # running time per load level
    duration_iperf_per_load_level_minutes = Config.duration_iperf_per_load_level_minutes
    # load levels
    load_levels = Config.loadLevels
    # total running time
    duration_per_minutes = (len(load_levels) * duration_iperf_per_load_level_minutes)
    # if Q-tables should be merged
    mergingQTableFlag = Config.mergingQTableFlag

    # fill-up-arrays / dicts
    averageLatencyList = []
    tempSavedRewards = []
    tempSavedRewardBeforeSaving = []
    savingValueArray = []
    previousState = []
    previousAction = {}
    currentState = {}

    # Iterators
    savingIterator = 0
    generalIterator = 0
    ITERATOR_BEFORE_SAVING_REWARD = 5
    HOW_MANY_TIMES_UNTIL_SAVE_Q = 500

    # read Load levels
    loadLevels = Config.loadLevels

    # if its a test with resetting Q values when changing load levels
    resetQTest = Config.resetQTestFlag

    # if splitting up load level files
    splitUpLoadLevels = Config.splitUpLoadLevelsFlag

    # log folder
    logPath = Config.log_path

    # changing load level flag
    reset_flag = False

    startingTime = time.time()

    # load level difines how high the network capacity can be
    loadLevel = loadLevels[0]

    # clean up save files
    clearingSaveFile(logPath, loadLevel, 'reward_controller', splitUpLoadLevels)
    clearingSaveFile(logPath, loadLevel, 'average_latency', splitUpLoadLevels)

    print("STARTING LEARNING | Mode: {} | time: {}min | alpha: {} | epsilon: {}".format(learning_mode,
                                                                                        duration_per_minutes, alpha,
                                                                                        epsilon))
    # the load level that arrives from the controller, gathered from the pipe
    loadLevelController = 0

    while True:
        # gathers the data from the pipe (controller <-> learning module)
        elements = pipe.recv()
        # if recieved sth
        if len(elements) > 0:
            # if received latency measurement values (init)
            if len(elements[0]) > 0:
                # actual combination of flows
                currentCombination = elements[0]
                # possible paths per flow
                paths_per_flow = elements[1]
                # dictionary with latency values between the links
                latencydict = elements[2]
                # wether load lvel changed
                reset_flag = elements[3]
                # load level gathered from  the mininet file (via the controller)
                loadLevelController = elements[4]
                # if it is the first flow
                if len(tempFlows) < 1:
                    copied_paths_per_flow = copy.deepcopy(paths_per_flow)
                    Q, actions, stateTransitions = update_Q_table_path_joined(Q, copied_paths_per_flow, mergingQTableFlag)
                    currentState = currentCombination
                    tempFlows = list(elements[0].keys())
                else:
                    # new flow added -> update best route
                    setTempFlows = set(tempFlows)
                    setChosenPaths = set(list(currentCombination.keys()))
                    # if reset flag is set -> changing of load level
                    if reset_flag:
                        loadLevel = loadLevelController
                        print("change in load level. new laod level: {}".format(loadLevel))
                        # if it should be saved in different files
                        if splitUpLoadLevels:
                            clearingSaveFile(logPath, loadLevel, 'reward_controller', splitUpLoadLevels)
                            clearingSaveFile(logPath, loadLevel, 'average_latency', splitUpLoadLevels)
                            generalIterator = 0
                            savingIterator = 0
                            tempSavedRewardBeforeSaving.clear()
                            averageLatencyList.clear()
                        # resetting the Q-Table (restart of leanring process)
                        if resetQTest:
                            Q, actions, stateTransitions = update_Q_table_path_joined({}, copied_paths_per_flow, mergingQTableFlag)

                    # if flows are added/deleted etc
                    if abs(len(setChosenPaths) - len(setTempFlows)) > 0:
                        copied_paths_per_flow = copy.deepcopy(paths_per_flow)
                        # pointer to combinations
                        differenceSet = setChosenPaths.difference(setTempFlows)
                        # if flows were added -> change q-table
                        Q, actions, stateTransitions = update_Q_table_path_joined(Q, copied_paths_per_flow, mergingQTableFlag, differenceSet)
                        previousState = []
                        currentState = currentCombination
                        tempFlows = list(elements[0].keys())
                        tempSavedRewards.clear()
                    rewardsqroot, rewardList = calculateRewards(currentCombination, latencydict)

                    # check if waited sufficient long time
                    if delayedRewardCounter >= delay_reward:
                        averageLatencyList.append(getAverageLatency(currentCombination, latencydict))
                        tempSavedRewards.append(rewardsqroot)
                        tempSavedRewardBeforeSaving.append(rewardsqroot)

                    # check if epsilon should be recalculated
                    if exploration_mode.value == ExplorationMode.FALLING_EPS.value:
                        epsilon = calc_epsilon(generalIterator)



                    # if gathered sufficient reward mesaurements
                    if len(tempSavedRewards) >= measurements_for_reward:
                        # calc qValue
                        if len(previousState) > 0 and len(previousAction) > 0:
                            if (learning_mode.value ==  QMode.MULTI_ARMED_BANDIT_NO_WEIGHT.value or learning_mode.value == QMode.MULTI_ARMED_BANDIT_WITH_WEIGHT.value):
                                Q = calc_new_Q_bandit(previousState, currentCombination, alpha, gamma, copy.deepcopy(Q),
                                           np.mean(tempSavedRewards), previousAction, learning_mode)
                            if learning_mode.value is QMode.Q_LEARNING.value:
                                Q = calc_new_Q_QL(previousState, currentCombination, alpha, gamma, copy.deepcopy(Q),
                                           np.mean(tempSavedRewards), previousAction)

                        # if not shotest path -> choose new action
                        if learning_mode.value != QMode.SHORTEST_PATH.value:
                            # choose action
                            action = json.loads(choose_action(currentState, Q, epsilon))
                            # do the action (if it is a transition) (send it into the pipe):
                            if "_" in action[0]:
                                pipe.send(action)
                            previousAction = copy.deepcopy(action)
                            previousState = copy.deepcopy(currentState)
                            # find out next state:
                            currentState = getNextState(stateTransitions, currentState, action)
                            print("Next State: {} PrevReward: {}".format(currentState, np.mean(tempSavedRewards)))

                        # log output
                        if (generalIterator % 100) < 1:
                            print("-------number of batch: {} epsilon: {}".format(generalIterator, epsilon))

                        # saving the reward if enough gathered
                        if not (savingIterator % ITERATOR_BEFORE_SAVING_REWARD) and savingIterator > 0:
                            saveCsvFile(logPath, loadLevel, 'reward_controller', np.mean(tempSavedRewardBeforeSaving),
                                        generalIterator // measurements_for_reward, splitUpLoadLevels)
                            saveCsvFile(logPath, loadLevel, 'average_latency', np.mean(averageLatencyList),
                                        generalIterator // measurements_for_reward, splitUpLoadLevels)
                            tempSavedRewardBeforeSaving.clear()
                            averageLatencyList.clear()

                        # saving the q-table (for DEBUG or to approximate agent actions)
                        if not (savingIterator % HOW_MANY_TIMES_UNTIL_SAVE_Q) and savingIterator > 0:
                            # Q , savingIterator, averageReward
                            savingValueArray.append((copy.deepcopy(Q), savingIterator // measurements_for_reward,
                                                     np.mean(tempSavedRewardBeforeSaving)))

                        generalIterator = generalIterator + 1
                        savingIterator = savingIterator + 1
                        delayedRewardCounter = 0
                        tempSavedRewards.clear()
                    delayedRewardCounter += 1

                # check if exit -> time.time are seconds
                if int((time.time() - startingTime) / 60) > duration_per_minutes:
                    #saveQ(savingValueArray)
                    print("Exited after {} steps (last load level)".format(generalIterator))
                    break

def getNextState(stateTransitions, currentState, action):
    nextState = {}
    actionTuple = tuple(action)
    if(actionTuple[0] == 'NoTrans'):
        return currentState
    for stateTrans in stateTransitions:
        if stateTrans[0] == currentState and stateTrans[1] == actionTuple:
            nextState = stateTrans[2]
    return nextState

def getAverageLatency(chosenPaths, latencyDict):
    rewardList = []
    rewardListJustValues = []
    sqrootLatency = 0
    for path in chosenPaths:
        cost = get_path_cost(latencyDict, chosenPaths[path])
        rewardList.append((path, cost))
        rewardListJustValues.append(cost)
    costBefore = 0
    for element in rewardListJustValues:
        costBefore += element
    avgLat = costBefore / len(rewardListJustValues)
    return avgLat

def calculateRewards (chosenPaths, latencyDict):
    rewardList = []
    rewardListJustValues = []
    sqrootLatency = 0
    for path in chosenPaths:
        cost = get_path_cost(latencyDict, chosenPaths[path])
        rewardList.append((path, cost))
        rewardListJustValues.append(cost)
    costBefore = 0
    for element in rewardListJustValues:
        costBefore += element ** 2
    sqrootLatency = math.sqrt(costBefore)
    return -sqrootLatency, rewardList

def update_Q_table_path_joined(prevQ, paths_per_flow, mergingQTableFlag, diffSet={}):
    t0 = time.time()
    paths_per_flow_copied = copy.deepcopy(paths_per_flow)
    paths_per_flow_filtered = filterStateSpacesByHOPS(paths_per_flow_copied, paths_per_flow, 1)
    print("got filtered flows")
    new_states = getPossibleStates(copy.deepcopy(paths_per_flow_filtered))
    print("got possible states: {}".format(len(new_states)))
    actions = getActionsForStates(new_states, paths_per_flow_filtered)
    print("got actions per states: {}".format(len(actions)))
    t01 = time.time()
    stateTransitions = getStateTransitions(new_states, actions)
    print("got state transitions: {}".format(time.time() - t01))
    # matching
    # create Q table
    Q = createNewQTable(actions)

    # if Q-Table should be merged
    if mergingQTableFlag:
        if len(prevQ) > 0 and len(diffSet) and len(diffSet) == MAX_LENGHT_DIFFSET:
            Q = mergingQtable(prevQ, Q, diffSet)

    print("Time to merge: {} micro_sec".format((time.time() - t0) * 10 ** 6))
    print("Action Size: {}".format(len(actions)))
    return Q, actions, stateTransitions

# merging operation of the Q-Table
def mergingQtable(oldQ, newQ, differenceSet):
    newQCopy = copy.deepcopy(newQ)
    for state in newQ:
        for action in newQ[state]:
            actionId = action[0]
            if actionId not in differenceSet:
                # find the sate with the smallest difference
                dictStateStr = ''
                dictState = json.loads(state)
                # delete the flow IDs of difference
                for difference in differenceSet:
                    dictState.pop(difference)
                # necessary to find the constellation that matches -> just json.dump does not give deterministic order
                oldQKeysDict = list(oldQ.keys())
                for oldQComb in oldQKeysDict:  # NEED TO BUILD UP TUPLE
                    oldKeysSet = json.loads(oldQComb)
                    # other variant:
                    # oldKeysSet = list(json.loads(oldQComb).items())
                    # if len(oldKeysSet.difference(set(dictState.items()))) < 1 and len(set(dictState.keys()).difference(oldKeysSet)) < 1:
                    if oldKeysSet == dictState:
                        dictStateStr = oldQComb  # json.dumps(oldQComb)
                if (len(dictStateStr) > 0):
                    # clean up the action set
                    actionOld = json.loads(action)
                    if list(actionOld)[0] not in differenceSet:
                        newQCopy[state][action] = oldQ[dictStateStr][action]
    return newQCopy


# creates a new Q table based on the actions of a state consellation
def createNewQTable(actions):
    Q = {}
    for actionElement in actions:
        state = json.dumps(actionElement[0], sort_keys=True)
        action = json.dumps(actionElement[1], sort_keys=True)
        # flowId = action[0]
        # nextPath = action[1]
        if state not in Q.keys():
            Q[state] = {}
        # steps
        Q[state][action] = [0, -math.inf, []]
    #print("newQTable: {}".format(Q))
    return Q


# find out matched items, no deep copy!!
def additionalStates(prevQ, stateTransitions):
    for stateTransition in stateTransitions:
        prevState = stateTransition[0]
        nextState = stateTransition[2]
        # check if in Q
        for currentCombination in prevQ:
            if prevState == currentCombination[0] and nextState == currentCombination[2]:
                print("Removed state while iterating".format(stateTransition))
                stateTransitions.remove(stateTransition)
    return stateTransitions


def getStateTransitions(states, actions):
    stateTransitionPairs = []
    for action in actions:
        currentstate = action[0]
        id = action[1][0]
        nextPath = action[1][1]
        nextState = copy.deepcopy(currentstate)
        if 'NoTrans' not in id:
        # change the state
            nextState[id] = nextPath
        stateTransitionPairs.append((currentstate, action[1], nextState))
    return stateTransitionPairs


# k^n, k.. possibilities, n.. flows
# 1 flows, 2 directions: 5 possibilities -> 5^2: 16
# 2 flows, 2 directions: 5 possibilities -> 5^4: 625
# 3 flows, 2 directions: 5 possibilities -> 5^6: 15625
# 4 flows, 2 directions: 5 possibilities -> 5^8: 390625
def getPossibleStates(paths_per_flow):
    t0 = time.time()
    # reduce action and state space
    # paths_per_flow = filterStateSpacesByHOPS(paths_per_flow, paths_per_flow, 1)
    # combinations = it.product(*(paths_per_flow[id] for id in allIds))
    # print("Path per flow: {}".format(paths_per_flow))
    # print("Path per flow item: {}".format(paths_per_flow.items()))
    flat = [[(k, v) for v in vs] for k, vs in paths_per_flow.items()]
    combinations = [dict(items) for items in it.product(*flat)]
    combinationsList = list(combinations)
    # print("Combinations: {}".format(combinationsList))
    print("calcLenght possibleStates: {} micro_sec".format((time.time() - t0) * 6))
    # print("Combinations Len: {}".format(len(combinationsList)))
    return combinationsList


def filterStateSpacesByHOPS(paths_per_flow, chosen_paths, bound=1):
    print("PATHS PER FLOW: {}".format(paths_per_flow))
    for flowId in paths_per_flow:
        print("Array: {}".format(paths_per_flow[flowId][0]))
        minimumlenght = min([len(x) for x in paths_per_flow[flowId]])
        print("MINIMUM LENGHT: {}".format(minimumlenght))
        for path in paths_per_flow[flowId]:
            if len(path) > minimumlenght + bound:
                # that is not the current chosen one
                if chosen_paths[flowId] != path:
                    paths_per_flow[flowId].remove(path)
    print("paths_per_copy: {}".format(paths_per_flow))
    return paths_per_flow


def getActionsForStates(combinations, paths_per_flows):
    actions = []
    for combination in combinations:
        otherPaths = copy.deepcopy(paths_per_flows)
        for flowId in combination:
            # find out other combinations
            chosenPath = combination[flowId]
            # all the other paths
            for otherPathById in otherPaths[flowId]:
                # kick out same paths of combinations
                if (otherPathById == chosenPath):
                    otherPaths[flowId].remove(otherPathById)
            # now, build possible next actions
            for chosenPath in otherPaths[flowId]:
                actions.append((combination, (flowId, chosenPath)))
        actions.append((combination, ('NoTrans', [])))
    return actions


def getActionsPerCurrentState(chosenPaths, paths_per_flow):
    actions = []
    otherPaths = copy.deepcopy(paths_per_flow)
    for chosenPath in chosenPaths:
        idPath = chosenPath
        selectedPath = chosenPaths[idPath]
        # cleaning up so possible actions get clear
        for path in otherPaths[idPath]:  # is it idPath?
            print("Path[0]: {}".format(path[0]))
            if path[0] == selectedPath:
                otherPaths[idPath].remove(path)
    ids = otherPaths.keys()
    for id in ids:
        for possiblePath in otherPaths[id]:
            actions.append((id, chosenPaths[id], possiblePath[0]))
    return actions

# calculates the route with the lowest cost
def getBestRoute(Q, startNode, endNode, maxHops):
    route = [startNode]
    # if last element not in end node, do not stop
    while route[-1] not in endNode:
        # check for minimum-value of all possible hops
        a = Q[route[-1]]
        nextHop = min(a, key=a.get)  # ,key=Q[route[-1]].get)
        route.append(nextHop)
        # prevent loop!!
        if len(route) > 2 and route[-1] in route[:-1]:
            break
    return route


# Q(s,a) <- Q(S,a) + alpha[R + gamma*max Q(S',a)-Q(S,a)]
# tracking a non stationary problem
def calc_new_Q_bandit(stateNow, nextState, alpha, gamma, Q, reward, action, learning_mode):
    # cambiamos
    stateNowStr = json.dumps(stateNow, sort_keys=True)
    nextStateStr = json.dumps(nextState, sort_keys=True)
    actionStr = json.dumps(action, sort_keys=True)
    keyMaxValue = keywithmaxActionval(Q[nextStateStr])
    try:
        # if chosen Q-value is set infinity -> necessary to change
        if math.isinf(Q[stateNowStr][actionStr][1]):
            Q[stateNowStr][actionStr][1] = 0
        # weighted average: Q_(n+1) = (1-alpha)^n*Q_1 + sum(i=1 -> n) alpha * (1 - alpha)^(n-i) R_i)
        if learning_mode.value == QMode.MULTI_ARMED_BANDIT_WITH_WEIGHT.value:
            lastRewards = Q[stateNowStr][actionStr][2]
            n = len(lastRewards)
            q_n = 0
            # last one is highest weighted
            for i in range(0, n, 1):
                q_n = q_n + alpha * (1 - alpha) ** (n - i) * lastRewards[i]
            Q[stateNowStr][actionStr][1] = q_n + alpha * (reward - q_n)
            # save the previous reward (list max elements)
            Q[stateNowStr][actionStr][2].append(reward)
            # kick one out if too much
            if (len(Q[stateNowStr][actionStr][2]) > MAX_PAST_REWARDS):
                Q[stateNowStr][actionStr][2].pop(0)
        # non weighted average; Q_n+1 = Q_n + 1/n * (R_n - Q_n)
        elif learning_mode.value == QMode.MULTI_ARMED_BANDIT_NO_WEIGHT.value:
            Q[stateNowStr][actionStr][1] = Q[stateNowStr][actionStr][1] + (1 / (Q[stateNowStr][actionStr][0])) * (
                        reward - Q[stateNowStr][actionStr][1])
        # total visits
        Q[stateNowStr][actionStr][0] = Q[stateNowStr][actionStr][0] + 1
    except KeyError:
        print("Q: {}".format(Q))
        print("StateNowStr: {}".format(stateNowStr))
    return Q

# calculate new Q-Value via Q-learning
def calc_new_Q_QL(stateNow, nextState, alpha, gamma, Q, reward, action):
    # cambiamos
    stateNowStr = json.dumps(stateNow, sort_keys=True)
    nextStateStr = json.dumps(nextState, sort_keys=True)
    actionStr = json.dumps(action, sort_keys=True)
    #actionStr = json.dumps(action)
    # Q[stateNow][action] = Q[stateNow][action] + alpha*(reward + gamma * max(Q[nextState]) - Q[stateNow][action])
    keyMaxValue = keywithmaxActionval(Q[nextStateStr])
    # if chosen Q-value is set infinity -> necessary to change
    if math.isinf(Q[stateNowStr][actionStr][1]):
        qAction = 0
    else:
        qAction = copy.deepcopy(Q[stateNowStr][actionStr][1])
    if math.isinf(Q[nextStateStr][keyMaxValue][1]):
        qMax_t_plus_1 = 0
    else:
        qMax_t_plus_1 = copy.deepcopy(Q[nextStateStr][keyMaxValue][1])
    try:
        Q[stateNowStr][actionStr][1] = qAction + alpha * (reward + gamma * qMax_t_plus_1 - qAction)
        Q[stateNowStr][actionStr][0] = Q[stateNowStr][actionStr][0] + 1
    except KeyError:
        print("Q: {}".format(Q))
        print("StateNowStr: {}".format(stateNowStr))
    return Q


# TODO: implement logic
def choose_action(stateNow, Q, e_greedy):
    # first find the actions possible
    stateString = json.dumps(stateNow, sort_keys=True)
    try:
        qActions = Q[stateString]
    except KeyError:
        print("Q: {}".format(Q))
        print("StateNowStr: {}".format(stateNow))
    actionChosen = keywithmaxActionval(qActions)
    # take random decision, if value between 0-1 is smaller than e greedy
    if random.random() < e_greedy:
        listKeys = list(qActions.keys())
        # kick out chosenaction
        listKeys.remove(actionChosen)
        actionChosen = random.choice(listKeys)
        print("xxxxxxxxxxxChosen randomly")
    # take max value
    return actionChosen


### fucntions for calculating.. maybe outsource to "functions"
def get_paths(latencyDict, src, dst):
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
        for next in set(latencyDict[node].keys()) - set(path):
            if next is dst:
                paths.append(path + [next])
            else:
                stack.append((next, path + [next]))
    return paths


# can also be changed to BWs, or to hops
def get_link_cost(latencyDict, s1, s2):
    # only latency:
    ew = latencyDict[s2][s1]
    return ew


# get the cost of a path
def get_path_cost(latencyDict, path):
    cost = 0
    for i in range(len(path) - 1):
        cost += get_link_cost(latencyDict, path[i], path[i + 1])
    return cost


def keywithmaxActionval(actions):
    """ a) create a list of the dict's keys and values;
        b) return the key with the max value"""
    v = list(actions.values())
    k = list(actions.keys())
    return k[v.index(max(v, key=scndElement))]


def scndElement(e):
    return e[1]


def calc_epsilon(steps, mode):
    return 0.507928 - 0.08 * math.log(steps)
    #return  0.507928 - 0.05993925*math.log(steps)
    #return 0.15


# TODO: not ready
def calc_UCB(Q, currentState):
    currentStateStr = json.loads(currentState)
    actions = list(Q[currentStateStr].keys())
    # number of possible actions (K)
    t = actions.len()
    BiggestValueKey = keywithmaxActionval(actions)
    # if still not checked -> take it
    if Q[currentStateStr][keywithmaxActionval][0] == 0:
        t=0


def saveQ(Q):
    with open('../Q_array.json', 'w') as file:
        json.dump(Q, file)  # use `json.loads` to do the reverse


def saveQBest(Q):
    with open('../Q_array_best.json', 'a') as file:
        json.dump(Q, file)  # use `json.loads` to do the reverse


def saveCsvFile(logPath, loadLevel, fileName,  reward, timepoint, splitUpLoadLevels):
    if splitUpLoadLevels:
        loadLevelStr = '/'+str(loadLevel)
    else:
        loadLevelStr = ''
    dirStr = '{}{}'.format(logPath, loadLevelStr)
    with open('{}/{}.csv'.format(dirStr, fileName), 'a') as csvfile:
        fileWriter = csv.writer(csvfile, delimiter=',')
        fileWriter.writerow([timepoint, reward, time.time()])


def clearingSaveFile(logPath, loadLevel, fileName, splitUpLoadLevels):
    if splitUpLoadLevels:
        loadLevelStr = '/'+str(loadLevel)
    else:
        loadLevelStr = ''
    dirStr = '{}{}'.format(logPath, loadLevelStr)
    if not os.path.exists(dirStr):
        os.makedirs(dirStr)
    with open('{}/{}.csv'.format(dirStr, fileName), 'w') as file:
        file.write("# iterator, reward, timestamp \n")