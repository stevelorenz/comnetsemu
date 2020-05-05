import socket
import argparse
import random

class UDPCCServer:
    def __init__(self, ip="10.0.0.2", port=5006, payload_size=4000):
        self.payload_size = payload_size
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((ip, port))
        self.rx_count = 0
        print("Server IP address:", ip + ", port:", port)
        print()

    def receive_data(self):
        while True:
            data, addr = self.socket.recvfrom(1024)
            ip, port = addr
            parts = data.split(b"\n\0")[0].split()
            seq_nr = int(parts[0].decode())
            time_stamp = parts[1].decode()
            self.rx_count += 1
            # print("received packet #" + str(self.rx_count),
                  # "seq nr:", seq_nr,
                  # "timestamp: ", time_stamp,
                  # "length:", len(data))
            # if seq_nr % 50 == 0:
            #     print("Simulating packet drop!")
            #     continue
            # print("Sending ACK")
            ack = str.encode(str(seq_nr) + " " + time_stamp)
            self.socket.sendto(ack, (ip, port))

def parse_args(parser):
    parser.add_argument("--client", type=str, default='10.0.0.1',
                        help="Client IP address")
    parser.add_argument("--server", type=str, default='10.0.0.2',
                        help="Server IP address")
    return parser.parse_args()

def main():
    name = "UDP Reinforcement Learning Congestion Control Server"
    parser = argparse.ArgumentParser(name)
    args = parse_args(parser)
    server = UDPCCServer(ip=args.server)
    server.receive_data()

if __name__ == '__main__':
    main()
