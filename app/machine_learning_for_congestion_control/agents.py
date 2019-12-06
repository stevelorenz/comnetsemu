import sys
import os
import time
import math
import copy
import keras
import rl.agents
import rl.callbacks
import rl.memory
import numpy as np
import visualizer

# keras.backend.tf.compat.v1.logging.set_verbosity(keras.backend.tf.compat.v1.logging.ERROR)
# use XLA:CPU
os.environ["TF_XLA_FLAGS"] = "--tf_xla_cpu_global_jit"

print("Python version:", sys.version)

class Agent(rl.agents.DQNAgent):
    agents = []
    verbose = os.getenv("VERBOSE") == "1"
    visualize = os.getenv("VISUALIZE") == "1"
    if visualize:
        rlcc_nodes_num = int(os.getenv("RLCCNUM"))

    def __init__(self, model, *args, **kwargs):
        super(Agent, self).__init__(model=model, *args, **kwargs)
        self.id = len(Agent.agents)
        self.observation_space_dim = None
        self.action_space_dim = None
        self.episode = np.int16(-1)
        self.nb_steps = np.int16(10**4)
        assert os.getenv("EPISODES"), "Env variable 'EPISODES' is not set"
        self.nb_episodes = int(os.getenv("EPISODES"))
        self.episode_step = 0
        self.step = 0
        self.last_observation = None
        self.last_action = None
        self.callbacks = None
        self.history = rl.core.History()
        Agent.agents.append(self)
        if self.visualize:
            self.visualizer = visualizer.Visualizer(self.rlcc_nodes_num)

    def begin_training(self):
        if self.training:
            self._on_train_begin()
        else:
            self._on_test_begin()
        self.callbacks.on_train_begin()

    def end_training(self):
        self.callbacks.on_train_end(logs=dict(did_abort=False))
        if self.training:
            self._on_train_end()
        else:
            self._on_test_end()

    def make_callbacks(self, callbacks=list(), verbose=2, log_interval=5):
        if not self.training and verbose >= 1:
            callbacks.append(rl.callbacks.TestLogger())
        elif self.training and  verbose == 1:
            callbacks.append(rl.callbacks.TrainIntervalLogger(interval=log_interval))
        elif self.training and verbose > 1:
            callbacks.append(rl.callbacks.TrainEpisodeLogger())
        callbacks.append(self.history)
        self.callbacks = rl.core.CallbackList(callbacks)
        self.callbacks.set_model(self)
        self.callbacks.set_params(dict(nb_steps=self.nb_steps, nb_episodes=self.nb_episodes))
        # self.callbacks.set_env(env)

    def start_new_episode(self):
        self.episode += 1
        self.episode_step = np.int16(0)
        self.episode_reward = np.float32(0)
        self.nb_episode_steps = np.int16(0)
        self.reset_states()
        self.callbacks.on_episode_begin(self.episode)

    def get_action(self):
        self.callbacks.on_step_begin(self.episode_step)
        action = self.forward(self.last_observation)
        self.last_action = action
        self.callbacks.on_action_begin(action)
        return action

    def backward_step(self, reward, done, observation):
        # action has been executed on the c++ side
        self.callbacks.on_action_end(self.last_action)
        self.last_observation = copy.deepcopy(observation)
        reward = np.float32(reward)
        self.episode_reward += reward
        metrics = self.backward(reward, terminal=done)

        step_logs = dict(action=self.last_action,
                         observation=observation,
                         reward=reward,
                         metrics=metrics,
                         episode=self.episode,
                         info=dict(),
                         )
        self.callbacks.on_step_end(self.episode_step, step_logs)
        self.step += 1
        self.episode_step += 1

    def reset(self, begin_new_episode, initial_observation=None):
        # The terminal state is reached, but the agent did not learn from the last action yet.
        # One last forward-backward call is necessary before the environment is reset.
        if self.step > 1:
            self.forward(self.last_observation)
            self.backward(0., terminal=False)

            episode_logs = dict(episode_reward=self.episode_reward,
                                nb_episode_steps=self.episode_step,
                                nb_steps=self.step,
                                )
            self.callbacks.on_episode_end(self.episode, episode_logs)
            print()

            if self.visualize:
                self.visualizer.clear_data()
        if begin_new_episode:
            # Initial observation is always just zeros.
            self.start_new_episode()
            if initial_observation is None:
                initial_observation = np.zeros(self.observation_space_dim)
            self.last_observation = initial_observation
            action = self.forward(self.last_observation)
            return action
        else:
            self.end_training()

def get_agent(aid):
    aid = int(aid)
    agent = Agent.agents[aid]
    return agent

def make_model(observation_space_dim, actions_dim):
    model = keras.models.Sequential()
    model.add(keras.layers.Flatten(input_shape=(1,) + (observation_space_dim,)))
    for _ in range(3):
        model.add(keras.layers.Dense(16))
        model.add(keras.layers.Activation("relu"))
    model.add(keras.layers.Dense(actions_dim))
    model.add(keras.layers.Activation("linear"))
    if Agent.verbose:
        print(model.summary())
    return model

def create_agent(num_agents, observation_space_dim, actions_dim, training_mode):
    assert len(Agent.agents) == num_agents
    observation_space_dim = int(observation_space_dim)
    actions_dim = int(actions_dim)
    model = make_model(observation_space_dim, actions_dim)
    memory = rl.memory.SequentialMemory(limit=50000, window_length=1)
    policy = rl.policy.EpsGreedyQPolicy()
    agent = Agent(model=model, policy=policy, nb_actions=actions_dim,
                  memory=memory, nb_steps_warmup=50, target_model_update=1e-2,
                  gamma=.99)
    agent.observation_space_dim = observation_space_dim
    agent.action_space_dim = actions_dim
    agent.compile(keras.optimizers.Adam(lr=1e-4), metrics=["mae"])
    agent.training = training_mode
    agent.make_callbacks()
    agent.begin_training()
    return agent.id

def step(aid, reward, done, *observation):
    done = bool(done)
    agent = get_agent(aid)
    reward = check_value(reward)
    observation = [check_value(x, False) for x in observation]
    agent.backward_step(reward, done, observation)

def get_action(aid):
    agent = get_agent(aid)
    return agent.get_action()

def tell_observation(aid, *observation):
    agent = get_agent(aid)
    agent.last_observation = copy.deepcopy([check_value(x) for x in observation])

def reset(aid, begin_new_episode, initial_obs=None):
    agent = get_agent(aid)
    return agent.reset(bool(begin_new_episode), initial_obs)

def save_weights(aid, filepath):
    agent = get_agent(aid)
    filepath += time.strftime("dqn_weights_%d.%m.%Y_%H:%M.%S_episode_{}.h5f".format(agent.episode))
    print(f"Saving weight file to '{filepath}'.")
    return agent.save_weights(filepath, overwrite=False)

def load_weights(aid, filepath, weightfile):
    agent = get_agent(aid)
    files = [x for x in os.listdir(filepath) if x.endswith(".h5f")]
    if weightfile:
        print(f"Loading weights from '{os.path.join(filepath, weightfile)}'.")
        agent.load_weights(os.path.join(filepath, weightfile))
        return

    if files:
        newest = max(((os.path.getmtime(os.path.join(filepath, x)), x) for x in files))[1]
        print(f"Loading weights from '{newest}'.")
        agent.load_weights(os.path.join(filepath, newest))

def tell_bdp_to_visualizer(aid, bdp):
    agent = get_agent(aid)
    agent.visualizer.bdp = bdp / agent.visualizer.n

def visualize(aid, index, t, cwnd, rtt, reward):
    agent = get_agent(aid)
    agent.visualizer.update(int(index), t, cwnd, rtt, reward)

def change_recent_action(aid, action):
    agent = get_agent(aid)
    agent.recent_action = action

def report_rto(aid, t):
    agent = get_agent(aid)
    if Agent.visualize:
        agent.visualizer.plot_rto_vline(t)

def report_enter_recovery(aid, t):
    agent = get_agent(aid)
    if Agent.visualize:
        agent.visualizer.plot_enter_recovery(t)

def report_exit_recovery(aid, t):
    agent = get_agent(aid)
    if Agent.visualize:
        agent.visualizer.plot_exit_recovery(t)

def check_value(value, reward=True):
    if math.isinf(value) or math.isnan(value):
        t = "reward" if reward else "observation"
        if Agent.verbose:
            cprint(FAIL, "Warning! Got " + t + " '" + str(value) + "'")
        return 0
    return value

FAIL = '\033[91m'
ENDC = '\033[0m'

def cprint(color, *args):
    print(color + " ".join(args), ENDC)
