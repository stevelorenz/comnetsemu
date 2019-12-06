"""
   config values for learning
"""
from enum import Enum
import math


class QMode(Enum):
    SHORTEST_PATH = -1
    MULTI_ARMED_BANDIT_NO_WEIGHT = 1
    MULTI_ARMED_BANDIT_WITH_WEIGHT = 2
    Q_LEARNING = 3
    SARSA = 4
    TD_ZERO = 5


class ExplorationMode(Enum):
    CONSTANT_EPS = 0
    FALLING_EPS = 1
    SOFTMAX = 2
    UCB = 3


class BiasRL(Enum):
    SPF = 1
    RANDOM = 2


class ActionMode(Enum):
    ONE_FLOW = 1
    DIRECT_CHANGE = 2


class RewardMode(Enum):
    ONLY_LAT = 1
    LAT_UTILISATION = 2


class Config(object):
    ################### Learning ########################
    qMode = QMode.Q_LEARNING
    alpha = 0.8
    gamma = 0.8

    # for eps-greedy
    epsilon = 0.05
    # for Softmax
    temperature = 0.00005  # tau
    # for UCB
    exploration_degree = 30  # c

    # how long to wait until starting to gather new rewards
    delay_reward = 2

    # how many rewards are gathered before considering taking a new action
    measurements_for_reward = 1

    # duration to stay in one load level by iperf
    duration_iperf_per_load_level_minutes = 5

    # load level
    load_levels = [10]

    # number of iterations per measurement
    iterations = 1

    # init_value for softmax
    softmax_init_value = - 140
    # - float('inf')

    # Scaling amount
    scaling_amount = 4

    #
    exploration_mode = ExplorationMode.SOFTMAX

    # action mode
    action_mode = ActionMode.ONE_FLOW

    # if LoadLevel Test Case
    reset_Q_test_flag = True

    # splitting up - each load level different log file
    split_up_load_levels_flag = False

    # if merging QTables when new flow joins
    merging_q_table_flag = False

    wait_between_load_lavel_change = False
    waiting_time = 0.5
    # if initialise with shortest path first or with a random selected path
    bias = BiasRL.RANDOM

    # where to save the logs
    log_path = './logs'

    # how many rewards sould be taken until building an average for the saved reward
    savingRewardCounter = 1

    # style of reward
    reward_mode = RewardMode.ONLY_LAT

    ################### Remote Controller ########################

    # update interval latency in seconds
    interval_update_latency = 1

    # sending to leanring module interval in seconds
    interval_communication_processes = 1

    # update interval flow and port statictics
    interval_controller_switch_latency = 0.5

    # maximum amount of possible paths
    max_possible_paths = 50
    # q array
    Q_array_path = "Q_array.json"
    number_of_actions = 9477

    ################## Mininet #########################

    # queue lenght
    queue_lenght = 30
    # size (bytes) packet iperf udp
    # size_iperf_pkt_bytes = 100
    # bandwith, in Mbit/s
