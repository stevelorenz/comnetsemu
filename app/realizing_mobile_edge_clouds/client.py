import socket
import time
import json
import random

# import subprocess

# _ = subprocess.call("route add 10.255.255.255 dev client1-eth0", shell=True)
# _ = subprocess.call("route add 10.255.255.255 dev client1-eth1", shell=True)
# _ = subprocess.call("ifconfig client1-eth1 10.0.0.10 netmask 255.0.0.0 broadcast 10.255.255.255", shell=True)

tx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
rx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

tx_socket.bind(("", 8008))  # only to prevent icmp "not reachable"

rx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
rx_socket.connect(("10.255.255.255", 8016))
# rx_socket.connect(("127.0.0.1", 8004))

cnt: int = 0
loop: int = 0
data = []
for i in range(0, 20):
    data.append(random.randint(a=0, b=1000))
_: str = ""
file = None

# try:
#     file = open("/tmp/log/client.LOG", "w")
#     file.write(f"Client started at {time.time()}")
#     _ = "logfile found"
# except Exception:
#     _ = "no logfile"
#     pass

print(f"starting client, {_}")
while True:
    try:
        msg = json.dumps(
            [
                {
                    "message": f"packet{loop}",
                    "type": "DATA",
                    "time": f"{time.time()}",
                    "data": data,
                }
            ],
            sort_keys=True,
            # indent=4,
            separators=(",", ": "),
        )
        rx_socket.sendall(msg.encode())

        # try:
        #     file = open("/tmp/log/client.txt", "w")
        #     file.write(f"sent msg, time : {time.time()}")
        #     file.close()
        # except Exception:
        #     pass

        if loop < 5:
            loop += 1
        else:
            loop = 0
        # data, addr = tx_socket.recvfrom(4096)  # use select.select() or sock.timeout() to only wait for recv time X
        # print(data)

        # try:
        #     file = open("/tmp/log/client.txt", "w")
        #     file.write(f"received msg : {data} from {addr}, time : {time.time()}")
        #     file.close()
        # except Exception:
        #     pass

        time.sleep(5)
    except Exception:
        # file.close()
        cnt += 1
        if cnt > 5:
            print("abort client")
            break
