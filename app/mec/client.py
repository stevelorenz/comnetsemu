import socket
import time
import json
import subprocess

# _ = subprocess.call("route add 10.255.255.255 dev client1-eth0", shell=True)
# _ = subprocess.call("route add 10.255.255.255 dev client1-eth1", shell=True)
# _ = subprocess.call("ifconfig client1-eth1 10.0.0.10 netmask 255.0.0.0 broadcast 10.255.255.255", shell=True)

tx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
rx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

tx_socket.bind(("", 8000))  # only to prevent icmp "not reachable"

rx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
rx_socket.connect(("10.255.255.255", 8004))


cnt = 0
loop = 0

while True:
    try:
        msg = json.dumps(
            [{"message": f"packet{loop}", "time": f"{time.time()}", "data": (1, 2, 3)}],
            sort_keys=True,
            # indent=4,
            separators=(",", ": "))
        rx_socket.sendall(msg.encode())
        if loop < 5:
            loop += 1
        else:
            loop = 0
        time.sleep(5)
    except Exception:
        cnt += 1
        if cnt > 5:
            print("abort client")
            break
