# Service Migration Example #

This example shows a simple service migration using ComNetsEmu.
The following figure depicts the setup:

```text
H1 --------- H2
      |
      |----- H3
```

While the client application is deployed on h1, the service application is firstly deployed on host h2.
The client application simply sends dummy UDP packets to the service address: 10.0.0.12:8888 every second and waits for
the response from the service application.
The service application simply perform a counting operation and return the number of packets received from the client.
The service application will be migrated between h2 and h3.
The state of the latest value of the counter is transmitted between h2 and h3 via their internal data network, which is
in a different subnet from the service address: 192.168.0.0/24.
So h2 and h3 has two interfaces up: one for service traffic and another one for state traffic between them.
Please check `./topology.py` for details.

## Run the emulation

Please first build the Docker image named `service_migration` with:

```bash
$ sudo ./build_docker_images.sh
```
Then the emulation script can be executed with:

```bash
$ sudo python3 ./topology.py
```

An example of the output:

```bash
- Internal IP of h2: 192.168.0.12
- Internal IP of h3: 192.168.0.13
PING 10.0.0.12 (10.0.0.12): 56 data bytes
64 bytes from 10.0.0.12: seq=0 ttl=64 time=204.414 ms
64 bytes from 10.0.0.12: seq=1 ttl=64 time=47.904 ms
64 bytes from 10.0.0.12: seq=2 ttl=64 time=40.560 ms

--- 10.0.0.12 ping statistics ---
3 packets transmitted, 3 packets received, 0% packet loss
round-trip min/avg/max = 40.560/97.626/204.414 ms


*** Setup1: Current log of the client: 
2020-06-16T19:42:01.159265128Z Current counter: 1
2020-06-16T19:42:02.427236720Z Current counter: 2
2020-06-16T19:42:03.575836874Z Current counter: 3
2020-06-16T19:42:04.649414447Z Current counter: 4
2020-06-16T19:42:05.729810284Z Current counter: 5
2020-06-16T19:42:06.868402696Z Current counter: 6
2020-06-16T19:42:08.020400935Z Current counter: 7
2020-06-16T19:42:09.231398774Z Current counter: 8
2020-06-16T19:42:10.419174716Z Current counter: 9


*** Setup2: Current log of the client: 
2020-06-16T19:42:01.159265128Z Current counter: 1
2020-06-16T19:42:02.427236720Z Current counter: 2
2020-06-16T19:42:03.575836874Z Current counter: 3
2020-06-16T19:42:04.649414447Z Current counter: 4
2020-06-16T19:42:05.729810284Z Current counter: 5
2020-06-16T19:42:06.868402696Z Current counter: 6
2020-06-16T19:42:08.020400935Z Current counter: 7
2020-06-16T19:42:09.231398774Z Current counter: 8
2020-06-16T19:42:10.419174716Z Current counter: 9
2020-06-16T19:42:11.470505370Z Current counter: 10
2020-06-16T19:42:12.832284709Z Current counter: 11
2020-06-16T19:42:13.886770602Z Current counter: 12
2020-06-16T19:42:14.931565808Z Current counter: 13
2020-06-16T19:42:15.973464801Z Current counter: 14
2020-06-16T19:42:17.015291447Z Current counter: 15
2020-06-16T19:42:18.056888966Z Current counter: 16
2020-06-16T19:42:19.098543492Z Current counter: 17
2020-06-16T19:42:20.140110212Z Current counter: 18
2020-06-16T19:42:21.181807849Z Current counter: 19

The PID of the old service: 22389

*** Setup3: Current log of the client: 
2020-06-16T19:42:01.159265128Z Current counter: 1
2020-06-16T19:42:02.427236720Z Current counter: 2
2020-06-16T19:42:03.575836874Z Current counter: 3
2020-06-16T19:42:04.649414447Z Current counter: 4
2020-06-16T19:42:05.729810284Z Current counter: 5
2020-06-16T19:42:06.868402696Z Current counter: 6
2020-06-16T19:42:08.020400935Z Current counter: 7
2020-06-16T19:42:09.231398774Z Current counter: 8
2020-06-16T19:42:10.419174716Z Current counter: 9
2020-06-16T19:42:11.470505370Z Current counter: 10
2020-06-16T19:42:12.832284709Z Current counter: 11
2020-06-16T19:42:13.886770602Z Current counter: 12
2020-06-16T19:42:14.931565808Z Current counter: 13
2020-06-16T19:42:15.973464801Z Current counter: 14
2020-06-16T19:42:17.015291447Z Current counter: 15
2020-06-16T19:42:18.056888966Z Current counter: 16
2020-06-16T19:42:19.098543492Z Current counter: 17
2020-06-16T19:42:20.140110212Z Current counter: 18
2020-06-16T19:42:21.181807849Z Current counter: 19
2020-06-16T19:42:22.223770331Z Current counter: 20
2020-06-16T19:42:23.431841620Z Current counter: 21
2020-06-16T19:42:24.500341806Z Current counter: 22
2020-06-16T19:42:25.618693327Z Current counter: 23
2020-06-16T19:42:26.741078337Z Current counter: 24
2020-06-16T19:42:27.835002743Z Current counter: 25
2020-06-16T19:42:28.966631359Z Current counter: 26
2020-06-16T19:42:30.216317879Z Current counter: 27
2020-06-16T19:42:31.481871814Z Current counter: 28
2020-06-16T19:42:32.625274454Z Current counter: 29

mininet> 
```
