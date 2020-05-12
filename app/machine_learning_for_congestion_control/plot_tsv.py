import sys
import os
import numpy as np
import matplotlib.pyplot as plt

"""Get x and y data from a .tsv file."""
def get_data(path, x, y):
    with open(path) as f:
        lines = f.readlines()
    for line in lines:
        t, cwnd = line.split("\t")
        x.append(float(t))
        y.append(float(cwnd.strip()))


def plot_data(path, scale=1):
    x = []
    y = []
    get_data(path, x, y)
    plt.plot(x, np.array(y) * scale)

"""Plot cwnd and RTT against time after running an emulation that created .tsv
files."""
def main():
    cwnd_files = [x for x in os.listdir() if "cwnd" in x and x.endswith(".tsv")]
    rtt_files = [x for x in os.listdir() if "rtt" in x and x.endswith(".tsv")]
    assert len(cwnd_files) == len(rtt_files), \
    "The number of source<i>_cwnd_data.tsv and source<i>_rtt_data.tsv files must be the same!"
    k = len(cwnd_files)

    legend = []
    for i, path in enumerate(cwnd_files):
        plot_data(path)
        legend.append("source {}".format(i+1))
    bdp = 420
    plt.plot([0, 30], [bdp / k, bdp / k], color="black", linestyle="dotted")
    legend.append("BDP")
    plt.legend(legend)
    plt.xlabel("time in s")
    plt.ylabel("congestion window in segments")

    plt.figure()
    for i, path in enumerate(rtt_files):
        plot_data(path, 1e3)
    plt.xlabel("time in s")
    plt.ylabel("RTT in ms")
    plt.show()

if __name__ == '__main__':
    main()
