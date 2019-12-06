import os
import time
import socket
import numpy as np
import argparse
import agents

class Window():
    high_window_nb = 0
    def __init__(self, cwnd, start_seq, action=None, payload_size=1000):
        self.start_time = time.time()
        self.end_time = None
        Window.high_window_nb += 1
        self.number = Window.high_window_nb
        self.action = action
        self.reward = 0
        self.rtts = []
        self.mean_rtt = None
        self.min_rtt = None
        self.max_throughput = 0
        self.cwnd = cwnd
        self.start_seq = start_seq
        self.sent_packets = 0
        self.received_acks = 0
        self.high_seq = 1
        self.done = False
        self.payload_size = payload_size
        self.throughput = 0
        self.tx_packet_list = []
        self.rx_packet_list = []
        vprint("Started window #" + str(self.number),
              "with action", action,
              "and cwnd", cwnd,
              "and start seq", start_seq)

    def get_observation(self, last_window):
        # dt = self.end_time - self.start_time
        # rtt_ratio = self.mean_rtt / self.min_rtt
        if last_window is not None:
            assert last_window.done
            self.rtt_deviation = (self.mean_rtt - last_window.mean_rtt) / last_window.mean_rtt
        else:
            self.rtt_deviation = 0
        if self.rtts:
            self.estimated_qdelay = self.mean_rtt - self.min_rtt
        else:
            self.estimated_qdelay = 0
        loss_rate = (self.sent_packets - self.received_acks) / self.sent_packets
        throughput_ratio = self.throughput / self.max_throughput
        # return (throughput_ratio, self.rtt_deviation, self.estimated_qdelay / self.min_rtt, loss_rate)
        return (self.rtt_deviation, self.estimated_qdelay / self.min_rtt, loss_rate)

    def get_reward(self):
        channel_capacity = 3e6
        throughput_ratio = self.throughput / channel_capacity
        rtt_ratio = self.mean_rtt / self.min_rtt
        beta = 10
        weights = np.array((4, -2, -4))
        rewards = np.array((throughput_ratio, rtt_ratio, self.loss_rate))
        reward = np.dot(weights, rewards) 
        return reward

    def summary(self):
        b = []
        b.append("Summary of window " + str(self.number))
        b.append("Packet " + str(self.start_seq) + " to " + str(self.high_seq))
        b.append("cwnd: " + str(self.cwnd))
        b.append("action: " + str(self.action))
        b.append("reward: " + str(self.reward))
        b.append("Sent packets: " + str(self.sent_packets))
        b.append("Received ACKs: " + str(self.received_acks))
        b.append("Throughput: " + str(self.throughput * 1e-6) + " MB/s")
        b.append("Max throughput: " + str(self.max_throughput * 1e-6) + " MB/s")
        lost_packets = self.sent_packets - self.received_acks
        try:
            loss_rate = lost_packets / self.sent_packets
        except ZeroDivisionError:
            loss_rate = float("inf")
        b.append("Lost packets: " + str(lost_packets) + ", (" + str(loss_rate * 100) + "%)")
        b.append("Mean RTT: " + str(self.mean_rtt))
        b.append(("Min  RTT: " + str(self.min_rtt)))
        b.append(("RTT deviation: " + str(self.rtt_deviation)))
        b.append("Estimated queuing delay: " + str(self.estimated_qdelay))
        # b.append("tx packet list: " + str(self.tx_packet_list))
        # b.append("rx packet list: " + str(self.rx_packet_list))
        b.append("\n")
        return "\n".join(b)

class UDPCCClient:
    verbose = bool(os.getenv("VERBOSE"))
    def __init__(self, ip="10.0.0.1", port=5005, dest_ip="10.0.0.2", dest_port=5006,
                 name="source", payload_size=1000, max_seq=10e8, max_time=30):
        self.dest_ip = dest_ip
        self.dest_port = dest_port
        self.payload_size = payload_size
        self.name = name
        self.max_time = max_time
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((ip, port))
        self.cwnd = 1
        self.next_tx_seq = 1
        self.next_rx_seq = 1
        self.max_seq = max_seq
        self.packets_in_flight = 0
        self.min_rtt = float("inf")
        self.max_throughput = 0
        self.windows = []
        self.observation_vector = []
        self.cwnd_data = []
        self.rtt_data = []
        self.slow_start = True
        self.socket.settimeout(1)
        self.end_loop = False
        Window.high_window_nb = 0

        vprint("")
        vprint("Client IP address:", ip + ", port:", port, "name:", self.name)
        vprint("Sending data to IP address:", dest_ip + ", port:", dest_port)
        vprint("")

    def get_tx_window(self):
        return self.windows[-1]

    def get_rx_window(self):
        if len(self.windows) > 1:
            return self.windows[-2]
        return self.windows[-1]

    def send_packet(self, seq):
        # Each message payload consists of two parts:
        # 1. Seq number
        # 2. Time stamp
        str_builder = [str(seq), str(time.time()), '\n']
        message = str.encode(" ".join(str_builder)).ljust(self.payload_size, b'\0')
        self.socket.sendto(message, (self.dest_ip, self.dest_port))
        # w = self.windows[-1]
        w = self.get_tx_window()
        w.sent_packets += 1
        w.tx_packet_list.append(seq)
        # print("tx win:", id(w), w.number, w.sent_packets)
        self.packets_in_flight += 1
        self.next_tx_seq += 1
        nr = str(w.number)
        dprint("Sent packet #" + str(seq) +
               ", window #" + nr + ", packets in flight:", self.packets_in_flight)

    def loop(self):
        while not self.end_loop:
            self.socket.setblocking(True)
            try:
                self.receive_ack(blocking=True)
            except socket.timeout:
                # A timeout occured to prevent a deadlock.
                print("Timeout... ending old window and starting new window with cwnd = 1 now.")
                self.packets_in_flight = 0
                self.end_window(self.get_rx_window())
                self.next_rx_seq = self.next_tx_seq
                self.cwnd = 1
                self.start_new_window(1)

            # Send and receive in an interleaved way, otherwise we miss the arrival of ACKs.
            w = self.get_tx_window()
            while self.next_tx_seq < self.max_seq and self.packets_in_flight < self.cwnd:
                w.high_seq = self.next_tx_seq
                try:
                    seq, rtt = self.receive_ack(blocking=False)
                except socket.error:
                    pass
                self.send_packet(self.next_tx_seq)

            # Receive all remaining ACKs until no data is available in the buffer.
            end_loop = False
            while end_loop:
                try:
                    seq, rtt = self.receive_ack(blocking=False)
                except socket.error:
                    end_loop = True

    def receive_ack(self, blocking=True):
        self.socket.setblocking(blocking)
        data, _ = self.socket.recvfrom(4096)
        parts = data.split()
        seq = int(parts[0].decode())
        time_stamp = float(parts[1].decode())
        now = time.time()
        rtt = now - time_stamp
        self.min_rtt = min(self.min_rtt, rtt)
        self.packets_in_flight -= (1 + seq - self.next_rx_seq)
        self.next_rx_seq = seq + 1

        # Check if first ACK of the current tx window arrived.
        # If so, start a new tx window.
        tx = self.get_tx_window()
        rx = self.get_rx_window()
        if self.slow_start:
            tx.cwnd += 1
            self.cwnd += 1
        if seq >= tx.start_seq:
            tx.high_seq = self.next_tx_seq - 1
            if not rx.done and tx != rx:
                self.end_window(rx)
            self.start_new_window(self.cwnd)

        w = self.get_rx_window()
        w.received_acks += 1
        w.rtts.append(rtt)
        w.rx_packet_list.append(seq)
        dprint("Received ack; seq:", seq, ", rtt:", rtt,
               ", packets in flight:", self.packets_in_flight)
        return seq, rtt

    def start_new_window(self, cwnd):
        if self.slow_start:
            action = None
            updated_cwnd = cwnd
        else:
            action = agents.get_action(0)
            updated_cwnd = update_cwnd(cwnd, action)
        self.cwnd = updated_cwnd
        w = Window(updated_cwnd, self.next_tx_seq, action)
        self.windows.append(w)

    def end_window(self, w):
        w.end_time = time.time()
        w.done = True
        if len(w.rtts) == 0:
            print(w.number)
            exit()
        w.mean_rtt = np.mean(w.rtts)
        w.min_rtt = self.min_rtt
        w.throughput = w.received_acks * self.payload_size / w.mean_rtt
        w.loss_rate = (w.sent_packets - w.received_acks) / w.sent_packets
        self.max_throughput = max(w.throughput, self.max_throughput)
        w.max_throughput = self.max_throughput
        last_window = self.get_window(w.number - 1)
        obs = w.get_observation(last_window)
        self.update_observation_vector(obs)
        w.reward = w.get_reward()
        vprint(w.summary())
        now = time.time()
        self.cwnd_data.append((now - self.start_time, self.cwnd))
        self.rtt_data.append((now - self.start_time, w.mean_rtt))
        if now - self.start_time > self.max_time:
            print("Finished sending for", self.max_time, "seconds")
            self.save_data("./{}_cwnd_data.tsv".format(self.name), self.cwnd_data)
            self.save_data("./{}_rtt_data.tsv".format(self.name), self.rtt_data)
            self.end_loop = True
        if not self.slow_start and w.action is not None:
            agents.change_recent_action(0, w.action)
            v = np.array(self.observation_vector).flatten()
            agents.step(0, w.reward, False, *v)
        if self.slow_start and w.number > 1 and w.loss_rate > 0:
            vprint("Exiting slow start, cwnd=", self.cwnd)
            self.cwnd_data.append((now - self.start_time, self.cwnd))
            self.cwnd = 0.5 * self.cwnd
            self.cwnd_data.append((now - self.start_time, self.cwnd))
            self.slow_start = False

    def get_window(self, number):
        for i in range(len(self.windows) - 1, -1, -1):
            if self.windows[i].number == number:
                return self.windows[i]
        vprint("Can not find window with number ", number)
        return None

    def update_observation_vector(self, observation):
        self.observation_vector.pop(0)
        self.observation_vector.append(observation)

    def save_data(self, path, data):
        with open(path, 'w') as f:
            for x, y in data:
                f.write(str(x) + "\t" + str(y) + "\n")

def vprint(*args):
    if os.getenv("VERBOSE"):
        print(*args)

def dprint(*args):
    if os.getenv("DEBUG"):
        print(*args)

def update_cwnd(cwnd, action):
    # cwnd(t+1) = b * cwnd(t) with b in {-0.5, -0.4, ..., 1.5}
    # number of actions: 11, action in {0, ..., 11}
    half = 5
    action -= half
    # action in {-5, ..., 5}
    half = 5
    if action == 0:
        return cwnd
    b = 0.25 * action / half
    if b > 0:
        new_cwnd = int((cwnd + max(1, b * cwnd)))
    else:
        new_cwnd = int((cwnd + min(-1, b * cwnd)))
    return max(1, new_cwnd)

def parse_args(parser):
    parser.add_argument("--train", action="store_true",
                        help="Train agent with epsilon greedy policy")
    parser.add_argument("--episodes", type=int, default=1,
                        help="Number of episodes to run")
    parser.add_argument("--client", type=str, default='10.0.0.1',
                        help="Client IP address")
    parser.add_argument("--server", type=str, default='10.0.0.2',
                        help="Server IP address")
    parser.add_argument("--node", "-n", type=str,
                        help="Node name used to store cwnd / RTT data")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print additional information")
    return parser.parse_args()

def run_episode(args, episode = 1):
    history_horizon = 10
    nb_observation_dim = 3
    max_time = 5 if args.train else 30
    client = UDPCCClient(ip=args.client, dest_ip=args.server,
                         name=args.node, max_time=max_time)
    for _ in range(history_horizon):
        client.observation_vector.append(nb_observation_dim * (0,))

    # UDP header is 8 bytes long.
    client.start_time = time.time()
    client.windows.append(Window(1, 1))
    client.send_packet(client.next_tx_seq)

    # Start send and receive processes.
    client.loop()
    client.socket.close()

def train_agent(args, episodes=500):
    for episode in range(1, episodes + 1):
        run_episode(args, episode)
        agents.reset(0, episode < episodes)
        time.sleep(0.5)
        if episode % 25 == 0:
            fname = time.strftime("./")
            agents.save_weights(0, fname) 


def main():
    name = "UDP Reinforcement Learning Congestion Control Client"
    parser = argparse.ArgumentParser(name)
    args = parse_args(parser)
    os.environ["EPISODES"] = str(args.episodes)
    if args.verbose:
        os.environ["VERBOSE"] = str(args.verbose)
    nb_observation_dim = 3
    history_horizon = 10
    nb_observation_space_dim = nb_observation_dim * history_horizon
    nb_actions = 11
    agents.create_agent(0, nb_observation_space_dim, nb_actions, args.train)
    agents.load_weights(0, "./", "weights.h5f")
    agents.reset(0, True)
    print("\n")

    if args.train:
        train_agent(args)
    else:
        run_episode(args)

if __name__ == '__main__':
    main()
