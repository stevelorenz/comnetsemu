import socket
import time
import json
import subprocess

# ip_list = ["10.0.0.20",
#            "10.0.0.21",
#            "10.0.0.22"]

# get proper route config
# time.sleep(2)

# _ = subprocess.call("route add 10.255.255.255 dev client1-eth0", shell=True)
# _ = subprocess.call("route add 10.255.255.255 dev client1-eth1", shell=True)
# _ = subprocess.call("ifconfig client1-eth1 10.0.0.10 netmask 255.0.0.0 broadcast 10.255.255.255", shell=True)

tx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# tx_socket2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# tx_socket3 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

rx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# rx_socket.bind(("10.0.0.10", 8000))  # only to prevent icmp "not reachable"

tx_socket.bind(("", 8000))  # only to prevent icmp "not reachable"

rx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
rx_socket.connect(("10.255.255.255", 8004))
# _ = np.random.rand(50, 1)
# msg = ""
#
# for item in _:
#     msg += str(100*item).replace("[", "").replace("]", "")
msg = json.dumps(
    [{"message": "msg", "time": f"{time.time()}", "data": (1, 2, 3)}],
    sort_keys=True,
    indent=4,
    separators=(",", ": "))

cnt = 0

while True:
    try:
        # tx_socket1.sendto(msg.encode(), (ip_list[0], 8004))
        # rx_socket.sendto(msg.encode(), ("10.0.0.20", 8004))
        rx_socket.sendall(msg.encode())
        # tx_socket2.sendto(msg.encode(), (ip_list[1], 8008))
        # tx_socket3.sendto(msg.encode(), (ip_list[2], 8016))
        time.sleep(3)
    except Exception:
        cnt += 1 
        if cnt > 5:
            print("abort client")
            break
