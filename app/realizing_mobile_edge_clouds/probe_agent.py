import socket
import time
import json

tx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
rx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

tx_socket.bind(("", 8000))  # only to prevent icmp "not reachable"

rx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
rx_socket.connect(("10.255.255.255", 8004))

cnt: int = 0
loop: int = 0

print(f"starting probing agent")
while True:
    try:
        msg = json.dumps(
            [
                {
                    "message": f"packet{loop}",
                    "type": "PROBE",
                    "time": f"{time.time()}",
                    "data": "None",
                }
            ],
            sort_keys=True,
            separators=(",", ": "),
        )
        rx_socket.sendall(msg.encode())

        if loop < 5:
            loop += 1
        else:
            loop = 0
        time.sleep(5)
    except Exception:
        cnt += 1
        if cnt > 5:
            print("abort probing agent")
            break
