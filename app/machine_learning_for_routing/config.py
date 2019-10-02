"""
   config values for learning
  """
from enum import Enum

class QMode(Enum):

  NO_LEARNING = -1
  MULTI_ARMED_BANDIT_NO_WEIGHT = 1
  MULTI_ARMED_BANDIT_WITH_WEIGHT = 2
  Q_LEARNING = 3

class ExplorationMode(Enum):
  CONSTANT_EPS = 0
  FALLING_EPS = 1

class Config(object):
  # Controller
  qMode = QMode.Q_LEARNING
  alpha = 0.8
  gamma = 0.3
  epsilon = 0.15
  # how long to wait until starting to gather new rewards
  delay_reward = 3
  # how many rewards are gathred before considering taking a new action
  measurements_for_reward = 3
  running_minutes = 61
  exploration_mode = ExplorationMode.CONSTANT_EPS



