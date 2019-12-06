import time
import os
import copy
import math
import itertools as it
import numpy as np
import json
import random
import sys
import csv

sys.path.append("..")
sys.path.append(".")
from config import Config
from config import ExplorationMode
from config import QMode
from config import ActionMode
from config import RewardMode
from datetime import datetime

MAX_LENGHT_DIFFSET = 2
MAX_PAST_REWARDS = 5
# modes:
'''
###############################################################
########## Class for learning started by controller############
###############################################################
'''


def learning_module(pipe, ):
    """
    main function that performs the learning and decision taking based on reinforcement leanring
    @param pipe: connection to remote controller
    """
    print('process id:', os.getpid())
    # RL Parameters
    # learning rate alpha
    alpha = Config.alpha
    # discount factor gamma
    gamma = Config.gamma
    # exploration probability epsilon (0-1.0)
    epsilon = Config.epsilon
    # learning mode: q-leanring, multiarmed bandit (constant )
    learning_mode = Config.qMode
    # defines if the exploration is eps_greedy constant, with falling eps or softmax
    exploration_mode = Config.exploration_mode
    # time steps that need to be waited until reward can be gathered
    # necessary because of the delayed reward
    delayed_reward_counter = 0
    # list of currently installed flows
    # necessary to check if new flows joined
    temp_flows = []
    # Q - Table
    Q = {}
    # how many rewards are gathred before considering taking a new action
    measurements_for_reward = Config.measurements_for_reward
    # running time per load level
    duration_iperf_per_load_level_minutes = Config.duration_iperf_per_load_level_minutes
    # load levels
    load_levels = Config.load_levels
    # total iterations per measurement
    iterations = Config.iterations
    # temperature (for softmax)
    temperature = Config.temperature
    # exploration degree (for UCB)
    exploration_degree = Config.exploration_degree
    # total running time
    duration_per_minutes = (len(load_levels) * duration_iperf_per_load_level_minutes) * iterations
    # if Q-tables should be merged
    merging_q_table_flag = Config.merging_q_table_flag

    # fill-up-arrays / dicts
    average_latency_list = []
    rewards_list = []
    reward_saving_list = []
    saving_value_array = []
    previous_state = []
    previous_action = {}
    current_state = {}

    # Iterators
    saving_iterator = 0
    general_iterator = 0
    interval_saving_q = 500

    # if its a test with resetting Q values when changing load levels
    reset_q_test = Config.reset_Q_test_flag

    # if splitting up load level files
    split_up_load_levels = Config.split_up_load_levels_flag

    # log folder
    log_path = Config.log_path

    starting_time = time.time()

    # load level difines how high the network capacity can be
    load_level = load_levels[0]

    # current iterations
    iterations_level = 0

    # how many rewards sould be taken until building an average for the saved reward
    saving_reward_counter = 1

    # if direct state change or only one flow
    action_mode = Config.action_mode

    # reward mode
    reward_mode = Config.reward_mode

    # check if iterations need to be saved in different file
    if iterations > 1:
        iteration_split_up_flag = True
    else:
        iteration_split_up_flag = False

    # if SARSA, the next action is given when calculating the next action
    next_action = ''

    # clean up save files
    clearing_save_file(log_path, load_level, 'reward_controller', split_up_load_levels, iteration_split_up_flag,
                       iterations_level)
    clearing_save_file(log_path, load_level, 'average_latency', split_up_load_levels, iteration_split_up_flag,
                       iterations_level)
    time_now = time.time()
    time_finish = time_now + (duration_per_minutes * 60)
    dt_object = datetime.fromtimestamp(time_finish)
    print("STARTING LEARNING | Mode: {} | time: {}min | exp. finishing: {} | alpha: {} | epsilon: {} | temperature; {} "
          "| Exploration Mode: {}".format(learning_mode, duration_per_minutes, dt_object, alpha,
                                          epsilon, temperature, exploration_mode))
    # the load level that arrives from the controller, gathered from the pipe
    # load_level_controller = 0
    while True:
        # gathers the data from the pipe (controller <-> learning module)
        elements = pipe.recv()
        # if recieved sth
        if len(elements) > 0:
            # if received latency measurement values (init)
            if len(elements['currentCombination']) > 0:
                # actual combination of flows
                current_combination = elements['currentCombination']
                # possible paths per flow
                paths_per_flow = elements['paths_per_flow']
                # dictionary with latency values between the links
                latencydict = elements['latencyDict']
                # wether load lvel changed
                reset_load_flag = elements['resetFlag']
                # load level gathered from  the mininet file (via the controller)
                load_level_controller = elements['loadLevel']
                # flag for resetting the iterations
                reset_iteration_flag = elements['iterationFlag']
                # iterations level (int)
                iteration_controller = elements['iteration']
                # stop_flag
                stop_flag = elements['stopFlag']

                if stop_flag:
                    save_q(Q, iterations_level)
                    print("Exited after {} steps (last load level)".format(general_iterator))
                    break

                if reset_load_flag:
                    load_level = load_level_controller
                    print("change in load level. new load level: {}".format(load_level))
                    # if it should be saved in different files
                    if split_up_load_levels:
                        if not reset_iteration_flag:
                            clearing_save_file(log_path, load_level, 'reward_controller', split_up_load_levels,
                                               iteration_split_up_flag, iterations_level)
                            clearing_save_file(log_path, load_level, 'average_latency', split_up_load_levels,
                                               iteration_split_up_flag, iterations_level)
                        # resetting the Q-Table (restart of learning process)
                        if reset_q_test:
                            Q, actions, state_transitions = update_Q_table({}, copied_paths_per_flow,
                                                                           merging_q_table_flag, action_mode)
                        next_action = ''
                        temp_flows = []
                        general_iterator = 0
                        saving_iterator = 0
                        rewards_list.clear()
                        reward_saving_list.clear()
                        average_latency_list.clear()

                if reset_iteration_flag:
                    save_q(Q, iterations_level)
                    iterations_level = iteration_controller
                    # if not reset_load_flag:
                    clearing_save_file(log_path, load_level, 'reward_controller', split_up_load_levels,
                                       iteration_split_up_flag, iterations_level)
                    clearing_save_file(log_path, load_level, 'average_latency', split_up_load_levels,
                                       iteration_split_up_flag, iterations_level)
                    # resetting the Q-Table (restart of learning process)
                    if reset_q_test:
                        print("xxxxxxxx RESETTING Q LoadLevel: {} Iteration: {} xxxxxxxxxxxxx".format(load_level,
                                                                                                      iterations_level))
                        Q, actions, state_transitions = update_Q_table({}, copied_paths_per_flow,
                                                                       merging_q_table_flag, action_mode)
                    general_iterator = 0
                    saving_iterator = 0
                    next_action = ''
                    temp_flows = []
                    rewards_list.clear()
                    reward_saving_list.clear()
                    average_latency_list.clear()
                    print("xxxxxxxxxxx Iteration: {} xxxxxxxxxxxxxxxxxxxxxxxxxx".format(iterations_level))
                    continue
                # if the load level is not -1 or 0
                if load_level > 0:
                    # if it is the first flow
                    if len(temp_flows) < 1:
                        copied_paths_per_flow = copy.deepcopy(paths_per_flow)
                        Q, actions, state_transitions = update_Q_table(Q, copied_paths_per_flow, merging_q_table_flag,
                                                                       action_mode)
                        current_state = current_combination
                        previous_state = {}
                        temp_flows = list(current_combination.keys())
                    else:
                        # new flow added -> update best route
                        set_temp_flows = set(temp_flows)
                        set_chosen_paths = set(list(current_combination.keys()))
                        # if reset flag is set -> changing of load level

                        # if flows are added/deleted etc
                        if abs(len(set_chosen_paths) - len(set_temp_flows)) > 0:
                            copied_paths_per_flow = copy.deepcopy(paths_per_flow)
                            # pointer to combinations
                            difference_set = set_chosen_paths.difference(set_temp_flows)
                            # if flows were added -> change q-table
                            Q, actions, state_transitions = update_Q_table(Q, copied_paths_per_flow,
                                                                           merging_q_table_flag, action_mode,
                                                                           difference_set)
                            previous_state = []
                            current_state = current_combination
                            temp_flows = list(current_combination.keys())
                            rewards_list.clear()
                            reward_saving_list.clear()
                            average_latency_list.clear()

                        # calculate the rewards
                        if reward_mode.value == RewardMode.ONLY_LAT.value:
                            reward = get_reward(current_combination, latencydict)
                        elif reward_mode.value == RewardMode.LAT_UTILISATION.value:
                            reward = get_reward_utilization(current_combination, latencydict)

                        # check if waited sufficient long time
                        # if delayed_reward_counter >= delay_reward:
                        average_latency_list.append(get_average_latency(current_combination, latencydict))
                        rewards_list.append(reward)
                        reward_saving_list.append(reward)
                        print("Average latency: {} Reward: {}\n".format(average_latency_list, rewards_list[0]))
                        # check if epsilon should be recalculated
                        if exploration_mode.value == ExplorationMode.FALLING_EPS.value:
                            epsilon = calc_epsilon(general_iterator)

                        # if gathered sufficient reward mesaurements
                        if len(rewards_list) >= measurements_for_reward:
                            # calc qValue
                            if len(previous_state) > 0 and len(previous_action) > 0:
                                if (learning_mode.value == QMode.MULTI_ARMED_BANDIT_NO_WEIGHT.value or
                                        learning_mode.value == QMode.MULTI_ARMED_BANDIT_WITH_WEIGHT.value):
                                    Q = update_q_bandit(previous_state, alpha, copy.deepcopy(Q),
                                                        np.mean(rewards_list), previous_action, learning_mode)
                                if learning_mode.value is QMode.Q_LEARNING.value:
                                    Q = update_q_ql(previous_state, current_combination, alpha, gamma, copy.deepcopy(Q),
                                                    np.mean(rewards_list), previous_action)
                                if learning_mode.value is QMode.SARSA.value:
                                    Q, next_action = update_q_sarsa(previous_state, current_state, alpha, gamma,
                                                                    copy.deepcopy(Q), np.mean(rewards_list),
                                                                    previous_action,
                                                                    exploration_mode, epsilon, temperature,
                                                                    exploration_degree)
                                if learning_mode.value is QMode.TD_ZERO.value:
                                    Q = update_td_zero(previous_state, current_state, alpha, copy.deepcopy(Q),
                                                       np.mean(rewards_list))
                            # if not shortest path -> choose new action
                            if learning_mode.value != QMode.SHORTEST_PATH.value:
                                if learning_mode.value == QMode.TD_ZERO.value:
                                    action = get_action_td_zero(exploration_mode, current_state, Q, epsilon,
                                                                temperature,
                                                                exploration_degree, actions, state_transitions)
                                else:
                                    if learning_mode.value == QMode.SARSA.value:
                                        # first time
                                        if len(next_action) > 0:
                                            action = copy.deepcopy(next_action)
                                        else:
                                            action = get_action(exploration_mode, current_state, Q, epsilon,
                                                                temperature, exploration_degree)
                                    else:
                                        action = get_action(exploration_mode, current_state, Q, epsilon, temperature,
                                                            exploration_degree)
                                # do the action (if it is a transition) (send it into the pipe):
                                if action_mode.value == ActionMode.ONE_FLOW.value:
                                    pipe.send(action)
                                elif action_mode.value == ActionMode.DIRECT_CHANGE.value:
                                    pipe.send(action)
                                previous_action = copy.deepcopy(action)
                                previous_state = copy.deepcopy(current_state)
                                # find out next state:
                                if action_mode.value == ActionMode.DIRECT_CHANGE.value:
                                    current_state = get_next_state(state_transitions, current_state, action, True)
                                else:
                                    current_state = get_next_state(state_transitions, current_state, action)

                                print("State: {}\n\nAction: {}\n\nNext State: {} \n\nPrevious Reward: {}".format(
                                    previous_state,
                                    previous_action,
                                    current_state,
                                    np.mean(rewards_list)))

                            # log output
                            if (general_iterator % 100) < 1:
                                print("-------number of batch: {} epsilon: {}".format(general_iterator, epsilon))

                            # saving the reward if enough gathered
                            if not (saving_iterator % saving_reward_counter) and saving_iterator > 0:
                                save_csv_file(log_path, load_level, 'reward_controller', np.mean(reward_saving_list),
                                              general_iterator // measurements_for_reward, split_up_load_levels,
                                              iteration_split_up_flag, iterations_level)
                                save_csv_file(log_path, load_level, 'average_latency', np.mean(average_latency_list),
                                              general_iterator // measurements_for_reward, split_up_load_levels,
                                              iteration_split_up_flag, iterations_level)
                                reward_saving_list.clear()
                                average_latency_list.clear()

                            # saving the q-table (for DEBUG or to approximate agent actions)
                            if not (saving_iterator % interval_saving_q) and saving_iterator > 0:
                                # Q , saving_iterator, averageReward
                                saving_value_array.append((copy.deepcopy(Q), saving_iterator // measurements_for_reward,
                                                           np.mean(reward_saving_list)))
                            general_iterator = general_iterator + 1
                            saving_iterator = saving_iterator + 1
                            delayed_reward_counter = 0
                            rewards_list.clear()
                        delayed_reward_counter += 1

                # check if exit -> time.time are seconds
                if int((time.time() - starting_time) / 60) > duration_per_minutes:
                    save_q(Q)
                    print("Exited after {} steps (last load level)".format(general_iterator))
                    break


def get_action(exploration_mode, current_state, Q, epsilon, temperature, exploration_degree):
    """
    choose action
    @param exploration_mode:
    @param current_state:
    @param Q:
    @param epsilon:
    @param temperature:
    @param exploration_degree:
    @return:
    """
    if exploration_mode.value == ExplorationMode.CONSTANT_EPS.value \
            or exploration_mode.value == ExplorationMode.FALLING_EPS.value:
        action = get_action_eps_greedy(current_state, Q, epsilon)
    elif exploration_mode.value == ExplorationMode.SOFTMAX.value:
        action = get_action_softmax(Q, current_state, temperature)
    elif exploration_mode.value == ExplorationMode.UCB.value:
        action = get_action_ucb(Q, current_state, exploration_degree)
    return action


def get_action_td_zero(exploration_mode, current_state, Q, epsilon, temperature, exploration_degree, actions,
                       nextStates):
    """
    choose action based on temporal difference learning
    @param exploration_mode:
    @param current_state:
    @param Q:
    @param epsilon:
    @param temperature:
    @param exploration_degree:
    @return:
    :param actions:
    """
    if exploration_mode.value == ExplorationMode.CONSTANT_EPS.value \
            or exploration_mode.value == ExplorationMode.FALLING_EPS.value:
        action = get_action_eps_greedy(current_state, Q, epsilon)
    elif exploration_mode.value == ExplorationMode.SOFTMAX.value:
        action = get_action_softmax(Q, current_state, temperature, actions, nextStates)
    elif exploration_mode.value == ExplorationMode.UCB.value:
        action = get_action_ucb(Q, current_state, exploration_degree)
    return action


def get_next_state(state_transitions, current_state, action):
    """
    returns next state
    @param state_transitions: dict that contains the next state based on the tuple between current state and action
    @param current_state
    @param action
    @return: next state
    """
    next_state = {}
    action_tuple = tuple(action)
    if Config.action_mode.value == ActionMode.DIRECT_CHANGE.value:
        if action == 'NoTrans':
            return current_state
        else:
            return action
    else:
        if action_tuple[0] == 'NoTrans':
            return current_state
        for stateTrans in state_transitions:
            if stateTrans[0] == current_state and stateTrans[1] == action_tuple:
                next_state = stateTrans[2]
    return next_state


def get_average_latency(current_path_combination, latency_dict):
    """
    calculates the average (latency) value of all elements of a list
    @param current_path_combination:
    @param latency_dict:
    @return:
    """
    latency_list = get_costs_of_paths(current_path_combination, latency_dict)
    cost = 0
    for element in latency_list:
        cost += element
    avg_lat = cost / len(latency_list)
    return avg_lat


def get_reward(current_path_combination, latency_dict):
    """
    calculates the reward as a square root sum quadratic /n of the latency
    @param current_path_combination:
    @param latency_dict:
    @return:
    """
    latency_list = get_costs_of_paths(current_path_combination, latency_dict)
    cost = 0
    for element in latency_list:
        cost += element ** 2
    sqroot_latency = math.sqrt(cost / len(latency_list))
    return -sqroot_latency


def get_reward_utilization():
    """
    TODO: for ressource maximisation
    (current_path_combination, latency_dict, bandwidth_dict = {}, max_bw_dict = {})
    calculates the reward as a combination of utilisation and latency
    @return:
    """
    return 0


def get_costs_of_paths(current_path_combination, latency_dict):
    """
    array of path costs
    @param current_path_combination:
    @param latency_dict:
    @return: array of path costs
    """
    value_list = []
    for path in current_path_combination:
        cost = get_path_cost(latency_dict, current_path_combination[path])
        value_list.append(cost)
    return value_list


def update_Q_table(prev_q, paths_per_flow, merging_q_table_flag, action_mode, joined_flows_set={}):
    """
    updates the q table if a new flow is joined
    @param prev_q: previous Q table
    @param paths_per_flow: possible paths for all flows
    @param merging_q_table_flag: if the Q table should be merged
    @param joined_flows_set: a dict of the flows that are joined
    @return: new Q-Table, new actions, new possible state transitions
    :param action_mode:
    """
    t0 = time.time()
    paths_per_flow_copied = copy.deepcopy(paths_per_flow)
    paths_per_flow_filtered = filter_possible_paths_by_hops(paths_per_flow_copied, paths_per_flow, 100)
    print("got filtered flows")
    new_states = get_possible_states(copy.deepcopy(paths_per_flow_filtered))
    print("got possible states: {}".format(len(new_states)))
    if Config.qMode.value != QMode.TD_ZERO.value:
        if action_mode.value == ActionMode.ONE_FLOW.value:
            actions = get_actions_for_states(new_states, paths_per_flow_filtered)
            state_transitions = get_state_transitions(actions)
            Q = create_new_q_table(actions, False)
        elif action_mode.value == ActionMode.DIRECT_CHANGE.value:
            actions = get_actions_for_states_direct(new_states)
            state_transitions = get_state_transitions_direct(actions)
            Q = create_new_q_table(actions, True)
    else:
        Q = create_new_value_table(new_states)
        actions = get_actions_for_states(new_states, paths_per_flow_filtered)
        state_transitions = get_state_transitions(actions)
    print("got actions per states: {}".format(len(actions)))
    # matching
    # create Q table
    # if Q-Table should be merged
    if merging_q_table_flag:
        if len(prev_q) > 0 and len(joined_flows_set) and len(joined_flows_set) < MAX_LENGHT_DIFFSET:
            Q = merging_qtable(prev_q, Q, joined_flows_set)
    print("Time to merge: {} micro_sec".format((time.time() - t0) * 10 ** 6))
    print("Action Size: {}".format(len(actions)))
    return Q, actions, state_transitions


def merging_qtable(prev_q, new_q, difference_set):
    """
    merging a Q table by searching similar states
    @param prev_q: previous Q table
    @param new_q: new calculated q table
    @param difference_set:
    @return: merged Q-table
    """
    new_q_copy = copy.deepcopy(new_q)
    for state in new_q:
        for action in new_q[state]:
            action_id = action[0]
            if action_id not in difference_set:
                # find the sate with the smallest difference
                dict_state_str = ''
                dict_state = json.loads(state)
                # delete the flow IDs of difference
                for difference in difference_set:
                    dict_state.pop(difference)
                # necessary to find the constellation that matches -> just json.dump does not give deterministic order
                old_q_keys_dict = list(prev_q.keys())
                for oldQComb in old_q_keys_dict:
                    old_keys_set = json.loads(oldQComb)
                    if old_keys_set == dict_state:
                        dict_state_str = oldQComb
                if len(dict_state_str) > 0:
                    # clean up the action set
                    action_old = json.loads(action)
                    if list(action_old)[0] not in difference_set:
                        new_q_copy[state][action] = prev_q[dict_state_str][action]
    return new_q_copy


def create_new_value_table(states, init_value=-math.inf):
    """
    creates a new value table
    :param states:
    :param init_value:
    :return:
    """
    Q = {}
    if Config.exploration_mode.value == ExplorationMode.SOFTMAX.value:
        init_value = Config.softmax_init_value
    for state in states:
        state_str = json.dumps(state, sort_keys=True)
        Q[state_str] = [0, init_value]
    return Q


#    creates a new Q table based on the actions of the possible states
def create_new_q_table(actions, direct=False):
    """
    creates new q-table based on the states and actions
    @param actions
    @return: Q table
    :param direct:
    """
    Q = {}
    for action_element in actions:
        state = json.dumps(action_element[0], sort_keys=True)
        if direct:
            action = json.dumps(action_element[1][0], sort_keys=True)
        else:
            action = json.dumps(action_element[1], sort_keys=True)
        if state not in Q.keys():
            Q[state] = {}
        # steps
        init_value = -math.inf
        # TODO: adapt init valued based on worst path
        if Config.exploration_mode.value == ExplorationMode.SOFTMAX.value:
            init_value = Config.softmax_init_value
        Q[state][action] = [0, init_value, []]
    # NOTE: Just a debug feature
    if len(actions) == Config.number_of_actions and len(Config.Q_array_path) > 0:
        try:
            path = Config.log_path + "/" + Config.Q_array_path
            # print(path)
            with open(path) as json_file:
                Q = json.load(json_file)
        except Exception as e:
            print(e)
            print("Q-array-file not found")
    return Q


def get_state_transitions(actions):
    """
    get the next state
    @param actions:
    @return: tuple (current_state, action, nextstate)
    """
    state_transition_pairs = []
    for action in actions:
        current_state = action[0]
        id = action[1][0]
        next_path = action[1][1]
        next_state = copy.deepcopy(current_state)
        if 'NoTrans' not in id:
            # change the state
            next_state[id] = next_path
        state_transition_pairs.append((current_state, action[1], next_state))
    return state_transition_pairs


def get_state_transitions_direct(actions):
    """
    get the next state
    @param actions:
    @return: tuple (current_state, action, nextstate)
    """
    state_transition_pairs = []
    for action in actions:
        current_state = action[0]
        next_state = action[1][0]
        state_transition_pairs.append((current_state, action[1], next_state))
    return state_transition_pairs


def get_possible_states(paths_per_flow):
    """
    get all possible states
    @param paths_per_flow:
    @return: states
    """
    t0 = time.time()
    flat = [[(k, v) for v in vs] for k, vs in paths_per_flow.items()]
    combinations = [dict(items) for items in it.product(*flat)]
    states = list(combinations)
    print("calcLenght possibleStates: {} micro_sec".format((time.time() - t0) * 6))
    return states


def filter_possible_paths_by_hops(paths_per_flow, chosen_paths, bound=1):
    """
    filter possible paths by maximum hops
    kicks out too long paths
    @param paths_per_flow:
    @param chosen_paths: current chosen
    @param bound: maximum amount of hops for considering flows in comparison to minimum lenght
    @return:
    """
    for flowId in paths_per_flow:
        minimumlenght = min([len(x) for x in paths_per_flow[flowId]])
        for path in paths_per_flow[flowId]:
            if len(path) > minimumlenght + bound:
                # that is not the current chosen one
                if chosen_paths[flowId] != path:
                    paths_per_flow[flowId].remove(path)
    return paths_per_flow


def get_actions_for_states(states, paths_per_flows):
    """
    get the possible actions
    @param states:
    @param paths_per_flows:
    @return: actions
    """
    actions = []
    for state in states:
        other_paths = copy.deepcopy(paths_per_flows)
        for flowId in state:
            # find out other combinations
            chosen_path = state[flowId]
            # all the other paths
            for other_path_by_id in other_paths[flowId]:
                # kick out same paths of combinations
                if other_path_by_id == chosen_path:
                    other_paths[flowId].remove(other_path_by_id)
            # now, build possible next actions
            for chosen_path in other_paths[flowId]:
                actions.append((state, (flowId, chosen_path)))
        actions.append((state, ('NoTrans', [])))
    return actions


def get_actions_for_states_direct(states):
    """
    get the possible actions for a direct change
    @param states:
    @param paths_per_flows:
    @return: actions
    """
    actions = []
    for state in states:
        state_changes = []
        other_states = copy.deepcopy(states)
        # kick out original state
        other_states.remove(state)

        for next_state in other_states:
            # find out which states should be changed
            for flowId in state:
                path_state = state[flowId]
                path_other_state = next_state[flowId]
                if path_state != path_other_state:
                    state_changes.append((flowId, path_other_state))
            actions.append((state, (next_state, copy.deepcopy(state_changes))))
        actions.append((state, ('NoTrans', [])))
    return actions


def get_actions_per_current_state(chosen_paths, paths_per_flow):
    """
    gets possible actions for the current state
    @param chosen_paths:
    @param paths_per_flow:
    @return: actions per state
    """
    actions = []
    other_paths = copy.deepcopy(paths_per_flow)
    for chosenPath in chosen_paths:
        id_path = chosenPath
        selected_path = chosen_paths[id_path]
        # cleaning up so possible actions get clear
        for path in other_paths[id_path]:  # is it id_path?
            print("Path[0]: {}".format(path[0]))
            if path[0] == selected_path:
                other_paths[id_path].remove(path)
    ids = other_paths.keys()
    for id in ids:
        for possible_path in other_paths[id]:
            actions.append((id, chosen_paths[id], possible_path[0]))
    return actions


# Q(s,a) <- Q(S,a) + alpha[R + gamma*max Q(S',a)-Q(S,a)]
# tracking a non stationary problem
def update_q_bandit(current_state, alpha, Q, reward, action, learning_mode):
    """
    updates Q table based on the multiarmed bandit method
    @param current_state:
    @param alpha: learning rate
    @param Q:
    @param reward:
    @param action:
    @param learning_mode:
    @return: updated Q table
    """
    # cambiamos
    state_now_str = json.dumps(current_state, sort_keys=True)
    action_str = json.dumps(action, sort_keys=True)
    try:
        # if chosen Q-value is set infinity -> necessary to change
        if math.isinf(Q[state_now_str][action_str][1]):
            Q[state_now_str][action_str][1] = 0
        # weighted average: Q_(n+1) = (1-alpha)^n*Q_1 + sum(i=1 -> n) alpha * (1 - alpha)^(n-i) R_i)
        if learning_mode.value == QMode.MULTI_ARMED_BANDIT_WITH_WEIGHT.value:
            last_rewards = Q[state_now_str][action_str][2]
            n = len(last_rewards)
            q_n = 0
            # last one is highest weighted
            for i in range(0, n, 1):
                q_n = q_n + alpha * (1 - alpha) ** (n - i) * last_rewards[i]
            Q[state_now_str][action_str][1] = q_n + alpha * (reward - q_n)
            # save the previous reward (list max elements)
            Q[state_now_str][action_str][2].append(reward)
            # kick one out if too much
            if len(Q[state_now_str][action_str][2]) > MAX_PAST_REWARDS:
                Q[state_now_str][action_str][2].pop(0)
        # non weighted average; Q_n+1 = Q_n + 1/n * (R_n - Q_n)
        elif learning_mode.value == QMode.MULTI_ARMED_BANDIT_NO_WEIGHT.value:
            Q[state_now_str][action_str][1] = Q[state_now_str][action_str][1] + (1 / (Q[state_now_str][action_str][0])) \
                                              * (reward - Q[state_now_str][action_str][1])
        # total visits
        Q[state_now_str][action_str][0] = Q[state_now_str][action_str][0] + 1
    except KeyError:
        print("Q: {}".format(Q))
        print("StateNowStr: {}".format(state_now_str))
    return Q


def update_q_ql(current_state, next_state, alpha, gamma, Q, reward, action):
    """
    updates Q table based on Q-Learning
    @param current_state:
    @param next_state:
    @param alpha: learning rate
    @param gamma: discount factor
    @param Q:
    @param reward:
    @param action:
    @return:
    """
    state_now_str = json.dumps(current_state, sort_keys=True)
    next_state_str = json.dumps(next_state, sort_keys=True)
    action_str = json.dumps(action, sort_keys=True)
    key_max_value = key_max_action_value(Q[next_state_str])
    # if chosen Q-value is set infinity -> necessary to change
    if math.isinf(Q[state_now_str][action_str][1]):
        q_action = 0
    else:
        q_action = copy.deepcopy(Q[state_now_str][action_str][1])
    if math.isinf(Q[next_state_str][key_max_value][1]):
        q_max_t_plus_1 = 0
    else:
        q_max_t_plus_1 = copy.deepcopy(Q[next_state_str][key_max_value][1])
    try:
        Q[state_now_str][action_str][1] = q_action + alpha * (reward + gamma * q_max_t_plus_1 - q_action)
        Q[state_now_str][action_str][0] = Q[state_now_str][action_str][0] + 1
    except KeyError:
        print("Q: {}".format(Q))
        print("StateNowStr: {}".format(state_now_str))
    return Q


def update_td_zero(current_state, next_state, alpha, Q, reward):
    """
    updates Q table based on Temporal Difference leanring (TDO0)
    :param current_state:
    :param next_state:
    :param alpha:
    :param Q:
    :param reward:
    :return:
    """
    state_now_str = json.dumps(current_state, sort_keys=True)
    next_state_str = json.dumps(next_state, sort_keys=True)
    try:
        # if chosen Q-value is set infinity -> necessary to change
        if math.isinf(Q[state_now_str][1]):
            q_action = 0
        else:
            q_action = copy.deepcopy(Q[state_now_str][1])
        value_next_action = Q[next_state_str][1]
        if math.isinf(value_next_action):
            value_next_action = 0
        else:
            value_next_action = copy.deepcopy(value_next_action)
        print("value next action: {}".format(value_next_action))
        Q[state_now_str][1] = q_action + alpha * (reward + 0.1 * value_next_action - q_action)
        Q[state_now_str][0] = Q[state_now_str][0] + 1
    except KeyError:
        print("Q: {}".format(Q))
        print("StateNowStr_TD_ZERO: {}".format(state_now_str))
    return Q


def update_q_sarsa(current_state, next_state, alpha, gamma, Q, reward, action, exploration_mode, epsilon,
                   temperature, exploration_degree):
    """
    updates Q table based on Q-Learning
    @param next_state:
    @param alpha:
    @param gamma:
    @param Q:
    @param reward:
    @param action:
    @return:
    @param current_state:
    @param exploration_mode:
    @param epsilon:
    @param temperature:
    @param exploration_degree:

    """
    # cambiamos
    state_now_str = json.dumps(current_state, sort_keys=True)
    next_state_str = json.dumps(next_state, sort_keys=True)
    action_str = json.dumps(action, sort_keys=True)
    # get next action
    action_following_state_key = json.dumps(
        get_action(exploration_mode, next_state, Q, epsilon, temperature, exploration_degree),
        sort_keys=True)
    try:
        # if chosen Q-value is set infinity -> necessary to change
        if math.isinf(Q[state_now_str][action_str][1]):
            q_action = 0
        else:
            q_action = copy.deepcopy(Q[state_now_str][action_str][1])
        if math.isinf(Q[next_state_str][action_following_state_key][1]):
            q_next_action = 0
        else:
            q_next_action = copy.deepcopy(Q[next_state_str][action_following_state_key][1])

        Q[state_now_str][action_str][1] = q_action + alpha * (reward + gamma * q_next_action - q_action)
        Q[state_now_str][action_str][0] = Q[state_now_str][action_str][0] + 1
    except KeyError:
        print("Q: {}".format(Q))
        print("StateNowStr: {}".format(state_now_str))
    return Q, json.loads(action_following_state_key)


def get_paths(latency_dict, src, dst):
    """
    Get all paths from src to dst using DFS algorithm
    @param latency_dict: dict of all link latencuies
    @param src:
    @param dst:
    @return: possible paths
    """
    if src == dst:
        # host target is on the same switch
        return [[src]]
    paths = []
    stack = [(src, [src])]
    while stack:
        (node, path) = stack.pop()
        for nxt in set(latency_dict[node].keys()) - set(path):
            if nxt is dst:
                paths.append(path + [nxt])
            else:
                stack.append((nxt, path + [nxt]))
    return paths


# can also be changed to BWs, or to hops
def get_link_cost(latency_dict, s1, s2):
    """
    returns the link cost
    @param latency_dict:
    @param s1: switch 1
    @param s2: switch 2
    @return:
    """
    link_cost = latency_dict[s2][s1]
    return link_cost


# get the cost of a path
def get_path_cost(latency_dict, path):
    """
    gets the cost of an path
    @param latency_dict:
    @param path:
    @return:
    """
    cost = 0
    for i in range(len(path) - 1):
        cost += get_link_cost(latency_dict, path[i], path[i + 1])
    return cost


def key_max_action_value(actions, element=2):
    """
        a) create a list of the dict's keys and values;
        b) return the key with the max value
    """
    v = list(actions.values())
    k = list(actions.keys())
    if element == 1:
        return k[v.index(max(v, key=first_element))]
    else:
        return k[v.index(max(v, key=scnd_element))]


def first_element(e):
    """
    returns first element of a list
    :param e:
    :return:
    """
    return e[0]


def scnd_element(e):
    """
    returns second element of a list
    :param e:
    :return:
    """
    return e[1]


def calc_epsilon(steps):
    """
    calculates eps in a fucntion of steps, to achieve annealing
    :param steps:
    :return:
    """
    return 0.507928 - 0.08 * math.log(steps)
    # return  0.507928 - 0.05993925*math.log(steps)
    # return 0.15


# TODO: implement logic
def get_action_eps_greedy(current_state, Q, e_greedy, actions={}, state_transitions={}):
    """
    chossing action based on eps_greedy
    @param current_state:
    @param Q:
    @param state_transitions:
    @param actions:
    @param e_greedy:
    @return:

    """
    # first find the actions possible
    if Config.qMode.value != QMode.TD_ZERO:
        state_string = json.dumps(current_state, sort_keys=True)
        try:
            q_actions = Q[state_string]
        except KeyError:
            print("Q: {}".format(Q))
            print("StateNowStr: {}".format(current_state))
        # take max value
        action_chosen = key_max_action_value(q_actions)
        # take random decision, if value between 0-1 is smaller than e greedy
        if random.random() < e_greedy:
            list_keys = list(q_actions.keys())
            # kick out chosenaction
            list_keys.remove(action_chosen)
            action_chosen = random.choice(list_keys)
            print("xxxxxxxxxxx Chosen randomly action: {} xxxxxxxxxxxxxxx".format(action_chosen))
        return json.loads(action_chosen)
    else:
        # possible_actions = actions[current_state]
        # next_state_dict = {}
        # for action in possible_actions:
        #     next_state = get_next_state(state_transitions, current_state, action, True)
        # TODO: implement TD_0
        return 0


def get_action_softmax(Q, current_state, tau, actions={}, state_transitions={}):
    """
    get the action based on the softmax exploration strategy
    @param Q:
    @param current_state:
    @param state_transitions:
    @param actions:
    @param tau: temperature parameter
    """
    current_state_str = json.dumps(current_state, sort_keys=True)
    if Config.qMode.value != QMode.TD_ZERO.value:
        actions = copy.deepcopy(Q[current_state_str])
        actions_keys = list(actions)
        try:
            total = sum([np.exp(-1 / (actions[action][1] * tau), dtype=np.float128) for action in actions])
            probs = [(np.exp(-1 / (actions[action][1] * tau), dtype=np.float128) / total) for action in actions]
        except ZeroDivisionError:
            print("actions: {}".format(actions))
            print("total: {}".format(total))
        chosen_key = np.random.choice(actions_keys, p=probs)
        return json.loads(chosen_key)
    else:
        # print(actions)
        possible_actions = []
        for action in actions:
            # print("ACTION_PARSE: {}, current: {}".format(action,currentState))
            if action[0] == current_state:
                possible_actions.append(copy.deepcopy(action))
        actions_value = {}
        for action in possible_actions:
            next_state = get_next_state(state_transitions, current_state, action[1])
            nextstate_str = json.dumps(next_state, sort_keys=True)
            value = Q[nextstate_str][1]
            actions_value[json.dumps(action[1], sort_keys=True)] = value
        try:
            print("ActionsValue: {}".format(actions_value))
            total = sum([np.exp(-1 / (actions_value[action] * tau), dtype=np.float128) for action in actions_value])
            probs = [(np.exp(-1 / (actions_value[action] * tau), dtype=np.float128) / total) for action in
                     actions_value]
            print("probs: {}".format(probs))
        except ZeroDivisionError:
            print("actions: {}".format(actions))
            print("total: {}".format(total))
        actions_keys = list(actions_value.keys())
        try:
            chosen_key = np.random.choice(actions_keys, p=probs)
        except ValueError:
            print("actionsValues: {}".format(actions_value))
            print("possible_actions: {}".format(possible_actions))
        return json.loads(chosen_key)


def get_action_ucb(Q, current_state, c):
    """
    get the action based on the upper confident bound
    @param Q:
    @param current_state:
    @param c: degree of exploration, c > 0
    """
    current_state_str = json.dumps(current_state, sort_keys=True)
    if Config.qMode.value != QMode.TD_ZERO.value:
        q_current_state = Q[current_state_str]
        actions = list(q_current_state.keys())
        values = {}
        iterator_state_visits = 0
        for action in actions:
            iterator_state_visits = iterator_state_visits + q_current_state[action][0]
        for action in actions:
            # if never chosen -> choose it!
            if q_current_state[action][0] == 0:
                return json.loads(action)
            values[action] = q_current_state[action][1] + c * np.sqrt(np.log(iterator_state_visits) /
                                                                      q_current_state[action][0])
        return json.loads(max(values, key=values.get))


def save_csv_file(log_path, load_level, file_name, reward, timepoint, split_up_load_levels, iterations_split_upflag,
                  iteration):
    """
    saving the reward or latency in a csv file
    @param log_path:
    @param load_level:
    @param file_name:
    @param reward:
    @param timepoint:
    @param split_up_load_levels:
    @param iterations_split_upflag:
    @param iteration: number iteration
    """
    if split_up_load_levels:
        load_level_str = '/' + str(load_level)
    else:
        load_level_str = ''
    if iterations_split_upflag:
        iteration_level_str = '/' + str(iteration)
    else:
        iteration_level_str = ''
    dir_str = '{}{}{}'.format(log_path, iteration_level_str, load_level_str)
    with open('{}/{}.csv'.format(dir_str, file_name), 'a') as csvfile:
        file_writer = csv.writer(csvfile, delimiter=',')
        file_writer.writerow([timepoint, reward, time.time()])


def clearing_save_file(log_path, load_level, file_name, split_up_load_levels, iterations_split_upflag, iteration):
    """
    empties a save file
    @param log_path:
    @param load_level:
    @param file_name:
    @param split_up_load_levels:
    @param iterations_split_upflag:
    @param iteration: number iteration
    """
    if split_up_load_levels:
        load_level_str = '/' + str(load_level)
        print("LoadLevelStr: {}".format(load_level_str))
    else:
        load_level_str = ''
    if iterations_split_upflag:
        iteration_level_str = '/' + str(iteration)
    else:
        iteration_level_str = ''
    dirStr = '{}{}{}'.format(log_path, iteration_level_str, load_level_str)
    if not os.path.exists(dirStr):
        os.makedirs(dirStr)
    with open('{}/{}.csv'.format(dirStr, file_name), 'w') as file:
        file.write("# iterator, reward, timestamp \n")


'''
###################### Debugging functions #############################
'''


def save_q(Q, iteration=-1):
    # debug function
    return
    if iteration > 0:
        file_path = '../logs/{}/Q_array.json'.format(iteration)
    else:
        file_path = '../logs/Q_array.json'
    with open(file_path, 'w') as file:
        json.dump(Q, file)  # use `json.loads` to do the reverse


def save_q_best(Q):
    # debug function
    return
    with open('../Q_array_best.json', 'a') as file:
        json.dump(Q, file)  # use `json.loads` to do the reverse
