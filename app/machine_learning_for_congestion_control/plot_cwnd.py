import sys
import tikzplotlib
import numpy as np
import matplotlib.pyplot as plt


plt.style.use("zzo_color")
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

def main(k):
    x = []
    y = []

    path_cwnd = "/tmp/source{}_cwnd_data.tsv"
    path_rtt = "/tmp/source{}_rtt_data.tsv"

    legend = []
    for i in range(1, k+1):
        plot_data(path_cwnd.format(i))
        legend.append("$w_{{{}}}(t)$")
    bdp = 420
    plt.plot([0, 30], [420 / k, 420 / k], color="black", linestyle="dotted")
    legend.append("BDP")
    plt.legend(legend)
    plt.xlabel("time $t$ in \\si{\\second}")
    plt.ylabel("congestion window $w(t)$ in segments")
    tikzplotlib.save("/tmp/cwnd.tikz",
                     figurewidth=r"\textwidth", figureheight=r".25\textheight")

    plt.figure()
    for i in range(1, k+1):
        plot_data(path_rtt.format(i), 1e3)
    plt.xlabel("time $t$ in \\si{\\second}")
    plt.ylabel("RTT $\\tau(t)$ in \\si{\\milli\\second}")
    plt.yticks(range(140, 211, 10))
    tikzplotlib.save("/tmp/rtt.tikz",
                     figurewidth=r"\textwidth", figureheight=r".25\textheight")
    plt.show()

if __name__ == '__main__':
    try:
        k = int(sys.argv[1])
        assert k > 0
    except (IndexError, ValueError, AssertionError):
        print("Usage: python plot_graphs k")
        print("k is the number of flows that were emulated, k > 0!")
        exit(-1)
    main(k)
