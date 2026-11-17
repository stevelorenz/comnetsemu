# Plan: Experimenting with Congestion Control (TCP and QUIC) in ComNetsEmu

This plan explains how to use ComNetsEmu/Mininet to run, observe and compare
congestion control algorithms, first with kernel TCP and then with QUIC. It builds
on the existing app in `app/machine_learning_for_congestion_control/`.

---

## 0. Background

### Congestion control vs. QUIC

- **Congestion control (CC)** is the algorithm a sender uses to decide how fast to
  send: how big the congestion window (cwnd) is, or what pacing rate to use. It
  reacts to signals such as packet loss, RTT growth or ECN marks. Common algorithms:
  - **NewReno**: loss-based, additive increase / multiplicative decrease (AIMD).
  - **CUBIC**: loss-based, cwnd grows as a cubic function of time since the last
    loss. Linux default.
  - **BBR**: model-based, estimates bottleneck bandwidth and minimum RTT and paces
    at that rate instead of filling the buffer.
- **QUIC** is a transport protocol (UDP-based, used by HTTP/3). It does not define
  one CC algorithm. It *runs* algorithms like the ones above, but in **userspace**,
  inside the application, not in the kernel as TCP does.

This is why QUIC is convenient for CC research: you can read, change and swap the
algorithm by editing a library, without touching or rebooting the kernel.

### What we want to learn

Typical questions for these experiments:

1. How does each algorithm use a bottleneck link (throughput, link utilization)?
2. How much queueing delay does it cause (bufferbloat)?
3. How does it react to random loss vs. congestion loss?
4. How fairly do competing flows share the link (same algorithm, and mixed
   algorithms such as CUBIC vs. BBR, or TCP vs. QUIC)?
5. How quickly does a new flow converge to its fair share?

---

## 1. Environment setup

1. Use the ComNetsEmu Vagrant VM (from the repo root):

   ```bash
   vagrant up comnetsemu
   vagrant ssh comnetsemu          # add `-- -X` if you want xterm windows
   ```

2. Inside the VM the repo is at `~/comnetsemu`. Check that Mininet works:

   ```bash
   sudo mn --test pingall
   sudo mn -c                      # clean up
   ```

3. Tools already installed by the `Vagrantfile`: `iperf`, `iperf3`, `python3-pip`.
   Install a few more:

   ```bash
   sudo apt install -y tcpdump tshark python3-matplotlib
   sudo modprobe tcp_bbr           # make BBR available to kernel TCP
   sysctl net.ipv4.tcp_available_congestion_control
   ```

4. **You do not need libvirt or TensorFlow** unless you want to run the
   reinforcement-learning agent in `source.py`. The dumbbell topology and
   everything else in this plan work in the default VirtualBox VM.

---

## 2. Understand the test topology

`app/machine_learning_for_congestion_control/dumbbell.py` builds a **dumbbell**,
the standard topology for CC experiments:

```
source1 ─┐                                         ┌─ sink1
source2 ─┤── g1 ═══════ bottleneck ═══════ g2 ──────┤─ sink2
  ...    │                                         │   ...
sourcek ─┘                                         └─ sinkk
```

| Link | Bandwidth | One-way delay | Queue |
|---|---|---|---|
| source*i* ↔ g1 | 400 Mbit/s (`50*8`) | 10 ms | 1000 packets |
| g2 ↔ sink*i* | 400 Mbit/s | 10 ms | 1000 packets |
| **g1 ↔ g2 (bottleneck)** | **24 Mbit/s** (`3*8`) | **50 ms** | **373 packets** |

Derived values:

- **Base RTT** = 2 × (10 + 50 + 10) ms = **140 ms**
- **Bandwidth-delay product (BDP)** = 3 MB/s × 0.14 s ≈ **420 KB**, about 420
  segments of 1000 bytes. This is the dotted "BDP" line in `plot_tsv.py`.
- The bottleneck queue (373 packets) is about **one BDP**, a classic "rule of
  thumb" buffer. A loss-based algorithm can fill it and roughly **double the RTT**.

How Mininet applies these settings: each `TCLink` uses an HTB qdisc for the rate
limit and a netem qdisc for the delay and queue limit, on **both** interfaces of
the link.

**Addresses and interfaces** (Mininet assigns them in creation order):

- IPs: `source1` = 10.0.0.1, `sink1` = 10.0.0.2, `source2` = 10.0.0.3,
  `sink2` = 10.0.0.4, and so on.
- On `g1`, interfaces `g1-eth1` … `g1-ethk` face the sources, and
  **`g1-eth(k+1)` faces the bottleneck**. With `-k 1` that is `g1-eth2`; with
  `-k 2` it is `g1-eth3`. Confirm with the `net` command in the CLI.

---

## 3. Mininet CLI basics

Start the topology without `-a` to get the interactive CLI:

```bash
cd ~/comnetsemu/app/machine_learning_for_congestion_control
sudo python3 dumbbell.py -k 2
```

| Command | Purpose |
|---|---|
| `<node> <shell command>` | Run a command on that node, e.g. `source1 ping -c 3 sink1` (node names are replaced with their IPs) |
| `<node> <cmd> &` | Run in the background and keep using the CLI |
| `nodes`, `net`, `dump`, `links`, `intfs` | Inspect the topology |
| `pingall` | Connectivity check |
| `link g1 g2 down` / `up` | Fail or restore a link |
| `xterm source1` | Open a terminal on a node (needs X forwarding) |
| `sh <cmd>` | Run a command on the VM itself |
| `py <expr>` | Python against the live network, e.g. `py source1.IP()` |
| `exit` / Ctrl-D | Stop the network |

Notes:

- All nodes share the VM's filesystem, so output files written on any node end up
  in the current directory.
- Each host has its own network namespace. On the Ubuntu 20.04 kernel,
  `net.ipv4.tcp_congestion_control` is set per namespace, so you can give each host
  a different default. Kernel *modules* (e.g. `tcp_bbr`) are shared. Choosing the
  algorithm per connection (`iperf3 -C`) is the most explicit option.
- Switches `g1`/`g2` run in the VM's root namespace, so `g1 tc ...` shows the
  real bottleneck qdisc.
- If a run crashes, clean up with `sudo mn -c`.

---

## 4. Phase 1: TCP baselines

Start with kernel TCP. The tools are mature, so this phase tests the setup and
gives reference numbers to compare QUIC against later.

### 4.1 Single flow, one algorithm at a time

```
mininet> sink1 iperf3 -s -D
mininet> source1 iperf3 -c sink1 -t 30 -C cubic -i 1
```

Repeat with `-C reno` and `-C bbr`. Record:

- average throughput (should approach 24 Mbit/s)
- retransmissions (`Retr` column)

### 4.2 Watch the queue and the RTT

In a second terminal on the VM (or via `xterm`), while a flow is running:

```bash
# Bottleneck qdisc: backlog = queued bytes/packets, dropped = congestion losses
watch -n 0.5 'tc -s qdisc show dev g1-eth2'
```

And in the CLI:

```
mininet> source1 ss -tin dst 10.0.0.2      # cwnd, rtt, pacing rate, retrans
```

Expected behaviour:

- **CUBIC/Reno** fill the queue: backlog near 373 packets, RTT rising from 140 ms
  towards ~280 ms, periodic drops, sawtooth cwnd.
- **BBR** keeps the queue mostly empty: RTT close to 140 ms, few drops.

### 4.3 Log cwnd and RTT over time

`plot_tsv.py` plots files named `<name>_cwnd_data.tsv` and `<name>_rtt_data.tsv`.
Each line is `time<TAB>value`, with time in seconds from the start of the flow.
Producing the same format for TCP lets you reuse the plotting script.

Save this as `ss_logger.py` in the app directory:

```python
#!/usr/bin/env python3
"""Log TCP cwnd and RTT from `ss` in plot_tsv.py's format.

Usage (on a source host): python3 ss_logger.py <dst_ip> <name> <seconds>
"""
import re
import subprocess
import sys
import time

dst, name, duration = sys.argv[1], sys.argv[2], float(sys.argv[3])
start = time.time()
with open(f"{name}_cwnd_data.tsv", "w") as cf, open(f"{name}_rtt_data.tsv", "w") as rf:
    while (now := time.time()) - start < duration:
        out = subprocess.run(["ss", "-tin", "dst", dst],
                             capture_output=True, text=True).stdout
        # iperf3 opens a control connection too; keep the one with the largest cwnd
        cwnds = [int(c) for c in re.findall(r"cwnd:(\d+)", out)]
        rtts = [float(r) for r in re.findall(r"\brtt:([\d.]+)", out)]
        if cwnds:
            i = cwnds.index(max(cwnds))
            t = now - start
            cf.write(f"{t}\t{cwnds[i]}\n")
            rf.write(f"{t}\t{rtts[i] / 1000}\n")   # ms -> s, as source.py does
        time.sleep(0.05)
```

Run it next to the flow:

```
mininet> source1 python3 ss_logger.py 10.0.0.2 source1 30 &
mininet> source1 iperf3 -c sink1 -t 30 -C cubic
mininet> exit
$ python3 plot_tsv.py
```

Note that `plot_tsv.py` plots every `*cwnd*.tsv` in the directory, so move old
results into a subfolder between runs.

### 4.4 Competing flows (fairness)

```bash
sudo python3 dumbbell.py -k 2
```

```
mininet> sink1 iperf3 -s -D
mininet> sink2 iperf3 -s -D
mininet> source1 iperf3 -c sink1 -t 60 -C cubic --logfile cubic.log &
mininet> source2 iperf3 -c sink2 -t 60 -C bbr   --logfile bbr.log
```

Try these combinations:

| Flow 1 | Flow 2 | What it shows |
|---|---|---|
| CUBIC | CUBIC | Intra-protocol fairness (should be close to 50/50) |
| BBR | BBR | Intra-protocol fairness for BBR |
| CUBIC | BBR | Inter-protocol fairness (BBRv1 often takes more than its share with buffers around one BDP) |
| CUBIC, started 20 s late | CUBIC | Convergence time to the fair share |

For the late start, run `sleep 20; iperf3 ...` on the second source.

---

## 5. Phase 2: Add QUIC

### 5.1 Choose an implementation

| Implementation | Language | Strengths | Use it if… |
|---|---|---|---|
| **picoquic** | C | Research-oriented; many built-in CC algorithms (NewReno, CUBIC, BBR, Prague, …), selected with a flag; qlog support | you mainly want to **compare existing algorithms** |
| **aioquic** | Python | Small, readable code base; easy to change the CC; qlog support | you want to **write or modify an algorithm** |
| quiche / quic-go / msquic | Rust / Go / C | Production-grade | you want behaviour close to real deployments |

Recommendation: **picoquic** to compare algorithms, **aioquic** to build your own.
Both handle a 24 Mbit/s bottleneck without trouble. Python's speed only matters at
much higher rates.

Command-line flags differ between versions. Always check `--help` / `-h` for the
version you install. The commands below show the general shape.

### 5.2 Install (inside the VM)

**picoquic** (needs `cmake` and OpenSSL headers; picotls is fetched automatically):

```bash
sudo apt install -y cmake build-essential libssl-dev pkg-config
cd ~ && git clone https://github.com/private-octopus/picoquic.git
cd picoquic
cmake -DPICOQUIC_FETCH_PTLS=Y .
make -j"$(nproc)"
./picoquicdemo -h               # lists options, including the CC algorithms (-G)
```

**aioquic**:

```bash
pip3 install --user aioquic
cd ~ && git clone https://github.com/aiortc/aioquic.git   # for examples/ and test certs
```

The VM uses Python 3.8. If the newest aioquic release no longer supports 3.8,
install an older release that does (`pip3 install --user "aioquic==<version>"`).

### 5.3 Certificates

QUIC always uses TLS 1.3, so the server needs a certificate. Both projects include
test certificates (picoquic: `certs/`, aioquic: `tests/`). Or create your own:

```bash
openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
  -keyout key.pem -out cert.pem -subj "/CN=sink1"
```

Clients in these experiments can skip certificate verification (or use the test CA).

### 5.4 Run one QUIC flow across the dumbbell

**picoquic** (paths relative to the picoquic directory):

```
mininet> sink1 ~/picoquic/picoquicdemo -p 4443 -c ~/picoquic/certs/cert.pem -k ~/picoquic/certs/key.pem &
mininet> source1 ~/picoquic/picoquicdemo -G bbr -q qlogs 10.0.0.2 4443 /50000000
```

- `-G <algo>` selects the congestion control algorithm.
- `-q <dir>` writes qlog traces.
- `/50000000` asks the demo server for a 50 MB response. The scenario syntax is
  described in `picoquicdemo -h`.

**aioquic** (HTTP/3 example server and client):

```
mininet> sink1 python3 ~/aioquic/examples/http3_server.py --host 10.0.0.2 --port 4433 \
           --certificate cert.pem --private-key key.pem --quic-log qlogs &
mininet> source1 python3 ~/aioquic/examples/http3_client.py --insecure \
           --quic-log qlogs https://10.0.0.2:4433/50000000
```

Recent aioquic versions support Reno and CUBIC, with a configuration option or flag
to choose between them (see `http3_client.py --help`). The example server serves
`/<N>` as N bytes of data.

### 5.5 Observe QUIC

- `ss` does not show anything for QUIC, because cwnd lives in the application.
  Use **qlog** instead: it records `metrics_updated` (cwnd, bytes in flight,
  smoothed/min RTT), `packet_lost` and congestion-state events.
- Visualize qlogs at <https://qvis.quictools.info> (congestion graph view).
  Copy the files out of the VM first (e.g. into `/vagrant`, which is shared with
  the host).
- To reuse `plot_tsv.py`, write a small converter that reads the qlog
  (JSON / JSON-SEQ) and writes `<name>_cwnd_data.tsv` and `<name>_rtt_data.tsv`.
  Convert cwnd from bytes to segments (÷ 1000 or ÷ max datagram size) so it
  matches the BDP line.
- The bottleneck queue (`tc -s qdisc show dev g1-eth2`) works exactly as for TCP.

---

## 6. Phase 3: Comparison experiments

### 6.1 Experiment matrix

Run each of these with both TCP and QUIC where possible:

| # | Scenario | Flows | Variable |
|---|---|---|---|
| E1 | Single flow | 1 | Algorithm: Reno / CUBIC / BBR |
| E2 | Same algorithm, same transport | 2 | Fairness |
| E3 | Mixed algorithms | 2 | CUBIC vs. BBR |
| E4 | TCP vs. QUIC, same algorithm | 2 | Transport implementation (does userspace CUBIC behave like kernel CUBIC?) |
| E5 | Late-start flow | 2 | Convergence time |
| E6 | Buffer size | 1–2 | Queue = 0.25, 1, 4 × BDP (~95, 373, 1500 packets) |
| E7 | Random loss | 1 | `loss` = 0, 0.1, 1 % on the bottleneck |
| E8 | RTT unfairness | 2 | Different access-link delays for the two sources |

### 6.2 Make the topology configurable

Instead of editing `dumbbell.py`, copy it (e.g. to `cc_dumbbell.py`) and add
arguments for the bottleneck settings:

```python
parser.add_argument("--bw", type=float, default=24, help="bottleneck Mbit/s")
parser.add_argument("--delay", default="50ms", help="bottleneck one-way delay")
parser.add_argument("--queue", type=int, default=373, help="bottleneck queue (packets)")
parser.add_argument("--loss", type=float, default=0, help="bottleneck loss in %%")
...
net.addLink(g1, g2, bw=args.bw, delay=args.delay,
            max_queue_size=args.queue, loss=args.loss)
```

For E8, add a per-source `delay` on the `source ↔ g1` links.

### 6.3 Repetition

Run each configuration **at least 5 times** and report the mean and spread.
Single runs vary, especially for loss-based algorithms and late-start scenarios.

---

## 7. Phase 4: Automate

Typing CLI commands works for exploring, but real experiments should be scripted.
The plan is one script, `quic_dumbbell.py`, that:

1. Parses arguments: number of flows, algorithm and transport (tcp/quic) per flow,
   start offsets, duration, bottleneck settings, number of repetitions.
2. Builds the dumbbell (as in `dumbbell.py`).
3. For each flow, starts the server on `sinkN` with `sink.popen(...)` (rather than
   `cmd(... &)`, so you get a handle to stop it).
4. Starts `ss_logger.py` (TCP) and the client (TCP: `iperf3 -J` for JSON output;
   QUIC: client with qlog enabled) on `sourceN` after its start offset.
5. Polls `tc -s qdisc show dev g1-eth(k+1)` on `g1` throughout the run and logs
   backlog and drops.
6. Waits for all clients, stops the servers, calls `net.stop()`.
7. Moves all output into `results/<timestamp>_<config>/`, including a
   `config.json` describing the run.

A separate `analyze.py` then reads a results folder and produces the plots and
metrics from section 8.

---

## 8. Metrics and analysis

| Metric | How to compute it |
|---|---|
| Throughput per flow | iperf3 JSON (TCP); bytes received / time, or qlog (QUIC) |
| Link utilization | Sum of flow throughputs ÷ 24 Mbit/s |
| Queueing delay | RTT − min RTT (140 ms base); or qdisc backlog ÷ link rate |
| Loss / retransmissions | iperf3 `retransmits`; qlog `packet_lost`; qdisc `dropped` |
| Fairness | **Jain's index**: J = (Σxᵢ)² / (n · Σxᵢ²), where xᵢ is the throughput of flow *i*; 1.0 = perfectly fair, 1/n = one flow takes everything |
| Convergence time | Time after the late flow starts until both flows stay within ±10 % of the fair share |

Plots that work well:

- cwnd vs. time per flow, with the BDP line (`plot_tsv.py` style)
- RTT vs. time (shows queue build-up)
- Throughput vs. time per flow (shows fairness and convergence)
- Throughput–delay scatter, one point per algorithm/configuration

---

## 9. Phase 5 (optional): Write your own algorithm

With **aioquic**:

1. Find the congestion control code (`src/aioquic/quic/congestion/` in recent
   versions, `recovery.py` in older ones). Read how Reno is implemented: hooks for
   packets sent, acked, lost and RTT updates.
2. Copy Reno into a new class (e.g. a delay-based algorithm in the style of
   Vegas, or a simplified BBR) and register it under a new name.
3. Install your fork in editable mode: `pip3 install --user -e ~/aioquic`.
4. Run it through the same experiment matrix and compare with the built-in
   algorithms.

The existing `source.py` is another starting point: a minimal UDP sender with an
explicit cwnd, ACKs and RTT measurement. Its `Window` class and reward function
show how an RL agent can drive cwnd. You can replace the agent with a
hand-written rule to prototype an idea before porting it to QUIC.

---

## 10. Pitfalls and validity checks

- **CPU saturation**: all nodes share the VM's CPUs. If a CPU is at 100 %, you are
  measuring the emulator, not the algorithm. Watch `top` during runs and keep rates
  modest. Give the VM at least 2 vCPUs.
- **Offloads**: TSO/GSO/GRO on veth interfaces can merge packets and distort
  results. For packet-accurate experiments, turn them off on the hosts, e.g.
  `source1 ethtool -K source1-eth0 tso off gso off gro off` (and the same for the
  sinks).
- **Check the link before testing algorithms**: confirm `ping` RTT ≈ 140 ms and a
  single CUBIC flow reaches ≈ 24 Mbit/s. If not, fix the setup first.
- **Leftover state**: run `sudo mn -c` after crashes. Kill stray servers
  (`pkill iperf3`, `pkill picoquicdemo`) before the next run.
- **Old result files**: `plot_tsv.py` reads every matching `.tsv` in the current
  directory, so keep each run in its own folder.
- **Comparing transports fairly**: QUIC and TCP implementations differ in more than
  CC (pacing, ACK frequency, initial window, HyStart). Check those settings
  before attributing a difference to the algorithm itself.

---

## 11. Suggested order of work

1. [ ] Set up the VM and run `dumbbell.py` (section 1–3)
2. [ ] TCP single-flow baselines for Reno, CUBIC, BBR, with queue observation (4.1–4.2)
3. [ ] `ss_logger.py` + `plot_tsv.py` plots (4.3)
4. [ ] TCP competing flows (4.4)
5. [ ] Install picoquic (and/or aioquic), run one QUIC flow, view qlog in qvis (5)
6. [ ] Configurable topology (6.2)
7. [ ] Automation script + analysis script (7–8)
8. [ ] Full experiment matrix with repetitions (6.1, 6.3)
9. [ ] Optional: own algorithm in aioquic (9)
