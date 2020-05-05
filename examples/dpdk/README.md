# Run DPDK Application inside Docker Container on ComNetsEmu #

This example shows a basic example to run [DPDK's L2 Forwarding Application](https://doc.dpdk.org/guides-19.08/sample_app_ug/l2_forward_real_virtual.html)
on ComNetsEmu without requirement of specific hardware support.
Instead of using specific [NIC Poll Mode Driver](https://doc.dpdk.org/guides-19.08/nics/index.html) for hardware NIC,
the application uses the [AF_Packet PMD](https://doc.dpdk.org/guides-19.08/nics/af_packet.html?highlight=af_packet)
which can work with Linux kernel veth interfaces.

**WARN**: This example is not performance-oriented. It uses AF_Packet PMD which can not avoid the context switch and
data-copying between kernel and user spaces.
The DPDK is compiled also with customized [configuration](./config).
Most hardware PMDs and kernel related features are disabled to make the image kernel-version independent and has a
relative small size (around 386MB). Multi-stage build is used in Dockerfile.
This is used to teach/test DPDK applications on the ComNetsEmu emulator, the PMD should be replaced for real
application.

The test topology described in [chain.py](./chain.py) is a simple chain with three nodes connected directly to a single
switch:

```text
Client --- Relay --- Server
```

The DPDK L2FWD application will run on the relay with parameters coded in chain.py.
The [Sockperf](https://github.com/Mellanox/sockperf) tool installed in the *network_measurement* image (is by default
created by ComNetsEmu installer) is used to measure the latency of **each discrete packet** with under-load mode and minimal
UDP/TCP payload size (14 bytes).

1.  Run setup script for DPDK runtime environment:
For example, DPDK application requires allocated hugepages. This must be allocated on the OS running Docker container.
Run following command inside the Vagrant VM:

```bash
$ sudo bash ./dpdk_setup.sh
```

It should show output like this:

```bash
* Setup hugepages when OS is already booted.
- Default hugepages size: 512 MB
AnonHugePages:         0 kB
ShmemHugePages:        0 kB
HugePages_Total:     256
HugePages_Free:      256
HugePages_Rsvd:        0
HugePages_Surp:        0
Hugepagesize:       2048 kB
Hugetlb:          524288 kB
```

1.  Build the DPDK Docker image (Version 19.08)


```bash
$ bash ./build_docker_image.sh
```

1.  Test the packet latency (with percentiles) between client and server without relay:

```bash
$ sudo python3 ./chain.py --no_relay
```

The output of Sockperf: 

```bash
*** client : ('sockperf under-load  -i 10.0.0.200 -t 10 --mps 50 --reply-every 1',)
sockperf[CLIENT] send on:sockperf: using recvfrom() to block on socket(s)

[ 0] IP = 10.0.0.200      PORT = 11111 # UDP
sockperf: Warmup stage (sending a few dummy messages)...
sockperf: Starting test...
sockperf: Test end (interrupted by timer)
sockperf: Test ended
sockperf: [Total Run] RunTime=10.005 sec; Warm up time=400 msec; SentMessages=501; ReceivedMessages=490
sockperf: ========= Printing statistics for Server No: 0
sockperf: [Valid Duration] RunTime=9.580 sec; SentMessages=469; ReceivedMessages=469
sockperf: ====> avg-latency=110178.188 (std-dev=4568.209)
sockperf: # dropped messages = 8; # duplicated messages = 0; # out-of-order messages = 0
sockperf: Summary: Latency is 110178.188 usec
sockperf: Total 469 observations; each percentile contains 4.69 observations
sockperf: ---> <MAX> observation = 120228.998
sockperf: ---> percentile 99.999 = 120228.998
sockperf: ---> percentile 99.990 = 120228.998
sockperf: ---> percentile 99.900 = 120228.998
sockperf: ---> percentile 99.000 = 120024.251
sockperf: ---> percentile 90.000 = 116536.503
sockperf: ---> percentile 75.000 = 113568.095
sockperf: ---> percentile 50.000 = 109809.731
sockperf: ---> percentile 25.000 = 106935.998
sockperf: ---> <MIN> observation = 100491.296
```

1.  Test the packet latency (with percentiles) between client and server with relay running DPDK L2FWD:

```bash
*** client : ('sockperf under-load  -i 10.0.0.200 -t 10 --mps 50 --reply-every 1',)
sockperf[CLIENT] send on:sockperf: using recvfrom() to block on socket(s)
[ 0] IP = 10.0.0.200      PORT = 11111 # UDP
sockperf: Warmup stage (sending a few dummy messages)...
sockperf: Starting test...
sockperf: Test end (interrupted by timer)
sockperf: Test ended
sockperf: [Total Run] RunTime=10.002 sec; Warm up time=400 msec; SentMessages=501; ReceivedMessages=490
sockperf: ========= Printing statistics for Server No: 0
sockperf: [Valid Duration] RunTime=9.590 sec; SentMessages=470; ReceivedMessages=470
sockperf: ====> avg-latency=110356.515 (std-dev=8561.256)
sockperf: # dropped messages = 8; # duplicated messages = 0; # out-of-order messages = 0
sockperf: Summary: Latency is 110356.515 usec
sockperf: Total 470 observations; each percentile contains 4.70 observations
sockperf: ---> <MAX> observation = 134299.685
sockperf: ---> percentile 99.999 = 134299.685
sockperf: ---> percentile 99.990 = 134299.685
sockperf: ---> percentile 99.900 = 134299.685
sockperf: ---> percentile 99.000 = 130073.130
sockperf: ---> percentile 90.000 = 122755.251
sockperf: ---> percentile 75.000 = 118129.449
sockperf: ---> percentile 50.000 = 107252.826
sockperf: ---> percentile 25.000 = 102618.944
sockperf: ---> <MIN> observation = 100145.177
```
