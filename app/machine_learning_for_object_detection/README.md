# Machine Learning for Object Detection #

This example demonstrates how to deploy and test a distributed object detection application using [You Only Look Once
(YOLO) version 2](https://pjreddie.com/darknet/yolov2/).
YOLOv2 is a deep learning based method and uses Convolutional Neutral Network (CNN) to detect multiple objects in a
image.  To goal of this example is to show that the object detection latency can be reduced by offloading a part of CNN
processing on the network edge. 

[Tensorflow](https://www.tensorflow.org/) is used in this example as the deep learning framework.
In order to accelerate the training and inference speed purely on CPU (Assume that not all devices on the network edge
have powerful built-in GPUs available).
The Tensorflow version with [Intel optimization](https://software.intel.com/en-us/articles/intel-optimization-for-tensorflow-installation-guide) is
installed.
A significant acceleration for inference can be detected if this example run bare-mental or inside a para-virtualization
enabled VM on a physical machine with Intel CPUs.
Sine [this project](https://github.com/zrbzrb1106/yolov2) started as a full development environment for deep learning
algorithms, the built Docker image size is relative big.
It can be reduced with target-specific customization or multi-stage build.
Please check the Dockerfile for detailed packages information.
Thanks for your understanding.

The test topology described in [topology.py](./topology.py) is a simple chain with three nodes connected directly to a
single switch:

```text
Client --- VNF --- Server
```

The folder contains following files:

1. Dockerfile.yolov2:  Dockerfile to build YOLOv2 environment used by client and server.

2. preprocessor.py: Program to send the [test image](./pedestrain.jpg) to the remote server for object detection
service. It has two running modes: 0: Send the raw image (in bytes) to remote server without processing. 1:
Pre-process the raw image and sent the middle results to the remote server.

3. server.py: Program to receive the image data from client, get detection results and send them back to the client.

4. vnf.py: Program to forward packets between client and server.

Before running tests in each node's terminal (Xterm by default). Run following commands to build the YOLOv2 image and
start the network with CLI mode. 10GB disk space is required to build the YOLOv2 image and minimal 4GB RAM is required
to run all tests smoothly. If the memory space is not enough, the detection program (using Tensorflow) will terminate
(be killed by the OOM) automatically.

```bash
# This step takes much time, many packages are downloaded and installed.
$ sudo bash ./build_docker_images.sh
$ sudo python3 ./topology.py
```

Since the `xterms=True` is used in the topology.py, five terminals (one xterm for one node) will be created when the
network topology is created.
Two Xterms with prompt `root@comnetsemu` are for virtual switch node and the reference SDN controller (In the root namespace).
These two Xterms can be closed.
The other three Xterms with prompt `root@client`, `root@vnf` and `root@server` are for client, vnf and server (In their own Docker container).
Following steps are marked with a "(node prompt name 1, node prompt name 2, ...) description" format.
The commands of each step should be executed **inside the corresponded terminal(s) with the marked prompt name**.

## Test 1: The VNF can forward infinite packets ##

In this test, the VNF can forward infinite packets. The client runs the preprocessor.py firstly in raw mode and then in
processed mode.

1. (`root@vnf`) Run VNF program with default arguments.

```bash
$ python ./vnf.py

*** Maximal forwarding number: -1 (-1: infinite)
*** Packet socket is bind, enter forwarding loop
```

2. (`root@server`) Run server.py and wait for it to be ready.

```bash
$ python ./server.py

... Logs of tensorflow
*** Wait for data from client.
```

3. (`root@client`) Run preprocessor.py with raw image mode (mode 0).

```bash
$ python ./preprocessor.py 0

*** Processing delay: 0.52 s, receive timeout:14.48 s
*** Get response from server, response: [{"object": "person", "score": 0.8786484003067017, "position": [164, 121, 257,
416]}, {"object": "person", "score": 0.803264856338501, "position": [145, 138, 185, 345]}, {"object": "backpack",
"score": 0.5143964886665344, "position": [223, 185, 246, 280]}]
*** Total time used: 11.43 s
```

The client can get the detection result from the server and the total delay (including transmission and image processing
for detection) is 11.43 second.

4. (`root@client`) Run preprocessor.py with pre-processed mode (mode 1). The server.py should still keep running on the
   server side. Restart it if the program crashes.

```bash
$ python ./preprocessor.py 1

*** Processing delay: 1.05 s, receive timeout:13.95 s
*** Get response from server, response: [{"object": "person", "score": 0.9002497792243958, "position": [165, 120, 256,
416]}, {"object": "person", "score": 0.8104279637336731, "position": [145, 140, 185, 343]}]
*** Total time used: 5.56 s
```

The client can get the detection result from the server and the total delay (including transmission and image processing
for detection) is 5.56 second.

## Test 2: The VNF can forward maximal 200 packets ##

In this test, the VNF can forward maximal 200 packets. The client runs the preprocessor.py firstly in raw mode and then
in processed mode. The 200 is chosen based on the required number of data packets to send to the server in two modes
(raw image: 235, pre-processed mode: 137). When the VNF can forward maximal 200 packets, the last 35 packets in raw
image mode will be lost.

1. (`root@vnf`) Run VNF program with maximal 200 packets.

```bash
$ python ./vnf.py --max 200

*** Maximal forwarding number: 200 (-1: infinite)
*** Packet socket is bind, enter forwarding loop
```

2. (`root@server`) Run server program on server node like step 2 in Test 1.

3. (`root@client`) Run preprocessor program with raw mode like step 3 in Test 1.

```bash
# The VNF program terminates
Reach maximal forwarding number, exits

# Both client and server will trigger timeout
# Output of client's terminal
*** Processing delay: 0.51 s, receive timeout:14.49 s
*** Failed to get response from server.
*** Total time used: 15.02 s
# Output of server's terminal
Server recv timeout! exist.
```

4. (`root@vnf`, `root@server`) Restart VNF and server program with step 1 and 2.

5. (`root@client`) Run preprocessor program with pre-processed mode (mode 1).

```bash
$ python ./preprocessor.py 1

*** Processing delay: 1.00 s, receive timeout:14.00 s
*** Get response from server, response: [{"object": "person", "score": 0.9002497792243958, "position": [165, 120, 256,
416]}, {"object": "person", "score": 0.8104279637336731, "position": [145, 140, 185, 343]}]
*** Total time used: 5.41 s
```

The pre-processing can reduce the required number of packets for transmission. This reduction can avoid potential buffer
overflow of VNFs in the middle (emulated by maximal forwarding number).
