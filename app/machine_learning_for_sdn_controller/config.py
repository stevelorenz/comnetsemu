"""
config values for learning
"""
from enum import Enum

class QMode(Enum):
  SHORTEST_PATH = -1
  MULTI_ARMED_BANDIT_NO_WEIGHT = 1
  MULTI_ARMED_BANDIT_WITH_WEIGHT = 2
  Q_LEARNING = 3

class ExplorationMode(Enum):
  CONSTANT_EPS = 0
  FALLING_EPS = 1


class Config(object):

  qMode = QMode.Q_LEARNING
  alpha = 0.8
  gamma = 0.3
  epsilon = 0.2
  # how long to wait until starting to gather new rewards
  delay_reward = 1
  # how many rewards are gathred before considering taking a new action
  measurements_for_reward = 1
  # duration to stay in one load level by iperf
  duration_iperf_per_load_level_minutes = 5

  exploration_mode = ExplorationMode.CONSTANT_EPS

  # if LoadLevel Test Case
  resetQTestFlag = True

  # splitting up - each load level different log file
  splitUpLoadLevelsFlag = False

  # if meraging QTables when new flow joins
  mergingQTableFlag = True

  # load level
  loadLevels = [9]

  # where to save the logs
  log_path = 'logs'

  # TODO !!! not implemented !!!
  # number of iterations per measurement
  iterations = 1