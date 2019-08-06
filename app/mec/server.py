import socket
import time
import json
import random
# import select

rx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
rx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
rx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
rx_socket.bind(("", 8004))

rng = 100000
if random.randint(0, 1) == 1:
    rng = 1000000

cnt = 0
print("starting server")
while True:
    try:
        data, addr = rx_socket.recvfrom(1024)
        _ = str(data.decode())
        #@TODO : fft with data, use numpy.fft() for this
        msg = json.dumps(
            [{"message": f"result{random.randint(0, 100)}\n{rng}", "time": f"{time.time()}", "data": (1, 2, 3)}],
            sort_keys=True,
            # indent=4,
            separators=(",", ": "))
        for i in range(0, rng):
            i += 1
        rx_socket.sendto(msg.encode(), (addr[0], 8000))
    except Exception:
        cnt += 1 
        if cnt > 5:
            print("abort server")
            break
