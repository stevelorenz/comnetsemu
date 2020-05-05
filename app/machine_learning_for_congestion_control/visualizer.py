import os
import matplotlib.pyplot as plt
from matplotlib import use

class Visualizer():
    def __init__(self, n):
        self.n = n
        self.bdp = 0
        self.xlimit = float(os.getenv("STOPTIME"))
        self.time_data = list()
        self.cwnd_data = list()
        self.rtt_data = list()
        self.reward_data = list()
        self.cwnd_lines = list()
        self.rtt_lines = list()
        self.reward_lines = list()
        fig = plt.figure()
        ax_cwnd = fig.add_subplot(311)
        ax_rtt = fig.add_subplot(312)
        ax_reward = fig.add_subplot(313)
        self.fig = fig
        self.axes = (ax_cwnd, ax_rtt, ax_reward)
        if n == 1:
            self.rtos = []
            self.enter_recoveries = []
            self.exit_recoveries = []
        for _ in range(n):
            self.time_data.append([0])
            self.cwnd_data.append([0])
            self.rtt_data.append([0])
            self.reward_data.append([0])
            self.cwnd_lines.append(ax_cwnd.plot(self.time_data, self.cwnd_data)[0])
            self.bdp_line = ax_cwnd.axhline(self.bdp, color='r', linestyle='--', linewidth=.8)
            self.rtt_lines.append(ax_rtt.plot(self.time_data, self.rtt_data)[0])
            self.reward_lines.append(ax_reward.plot(self.time_data, self.reward_data)[0])
        ax_cwnd.set_xlabel("time in s")
        ax_rtt.set_xlabel("time in s")
        ax_reward.set_xlabel("time in s")
        ax_cwnd.set_ylabel("cwnd in segments")
        ax_rtt.set_ylabel("rtt in ms")
        ax_reward.set_ylabel("reward")
        plt.ion()
        plt.show()

    def set_line_data(self, line, xdata, ydata):
        line.set_xdata(xdata)
        line.set_ydata(ydata)

    def update(self, index, t, cwnd, rtt, reward):
        self.time_data[index].append(t)
        self.cwnd_data[index].append(cwnd)
        self.rtt_data[index].append(rtt)
        self.reward_data[index].append(reward)
        # self.cwnd_lines[index].set_xdata(self.time_data[index])
        # self.cwnd_lines[index].set_ydata(self.cwnd_data[index])
        self.set_line_data(self.cwnd_lines[index], self.time_data[index], self.cwnd_data[index])
        self.set_line_data(self.rtt_lines[index], self.time_data[index], self.rtt_data[index])
        self.set_line_data(self.reward_lines[index], self.time_data[index], self.reward_data[index])
        for ax in self.axes:
            ax.relim()
            ax.autoscale()
            ax.set_xlim((0, self.xlimit))
        if self.bdp > 0:
            cwnd_ax = self.axes[0]
            self.set_line_data(self.bdp_line, self.time_data[index], [self.bdp for _ in enumerate(self.time_data[index])]) 
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def clear_data(self):
        if self.n == 1:
            self.delete_lines(self.rtos)
            self.delete_lines(self.enter_recoveries)
            self.delete_lines(self.exit_recoveries)

        for index in range(self.n):
            self.time_data[index] = [0]
            self.cwnd_data[index] = [0]
            self.rtt_data[index] = [0]
            self.reward_data[index] = [0]

    def delete_lines(self, lines):
        for l in lines:
            l.remove()
        lines.clear()

    def plot_rto_vline(self, t):
        if self.n == 1:
            cwnd_ax = self.axes[0]
            self.rtos.append(cwnd_ax.axvline(t, color='k', linestyle='--', linewidth=.8))
    
    def plot_enter_recovery(self, t):
        if self.n == 1:
            cwnd_ax = self.axes[0]
            self.enter_recoveries.append(cwnd_ax.axvline(t, color='m', linestyle='--', linewidth=.8))

    def plot_exit_recovery(self, t):
        if self.n == 1:
            cwnd_ax = self.axes[0]
            self.exit_recoveries.append(cwnd_ax.axvline(t, color='g', linestyle='-', linewidth=.8))
