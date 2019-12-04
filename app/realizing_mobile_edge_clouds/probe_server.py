import socket
import time
import json
import random
import cmath
from typing import List

rx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
rx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
rx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
rx_socket.bind(("", 8004))

rng = 100000
if random.randint(0, 1) == 1:
    rng = 500000

cnt = 0
loop = 0
print("starting server")
while True:
    try:
        if loop > 5:
            rng = 100000
            if random.randint(0, 1) == 1:
                rng = 500000
        data, addr = rx_socket.recvfrom(1024)
        _ = str(data.decode())
        data_json = json.loads(data)
        val = []
        for item in data_json:
            val = item["data"]
        # print(val)
        if val is not None or "None":
            pass
        # result = dft(val)
        # @TODO : fft with data, use numpy.fft() for this
        msg = json.dumps(
            [
                {
                    "message": f"result{random.randint(0, 100)}\n{rng}",
                    "time": f"{time.time()}",
                    "data": val,
                }
            ],
            sort_keys=True,
            # indent=4,
            separators=(",", ": "),
        )
        for i in range(0, rng):
            i += 1
        rx_socket.sendto(msg.encode(), (addr[0], 8000))
        loop += 1
    except Exception:
        cnt += 1
        if cnt > 5:
            print("abort server")
            break
