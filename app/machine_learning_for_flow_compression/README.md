# Machine Learning for Flow Compression #

To use the interactive environment of O2SC first build the O2SC docker container:

```sh
docker build -t o2sc .
```

Running the O2SC compressor in the dummy interface mode can be done with:

```sh
docker run -it o2sc -Du
```

To run the container with the ComNetsEmu, execute the following inside the emulator environment:

```sh
sudo python3 start_cne.py
```

Once running, all of the network nodes will provide command line interfaces in separate windows. It is recommended to switch to bash right away. To start compression, just run the node.py with python3 in the root home directory by specifying a source behaviour on  the source_1, source_2, etc., nodes and at least a compressor on the compressor node. The appropriate configuration of the script can be found out by querying its help with the -h flag.

Currently the -n [NUM] flag specifies a source behaviour with stream numbers 1, 2, 3, etc. To execute the compressor, just run the script without flags.

As an example:

compressor executes:
```sh
$ bash
$ sudo python3 node.py
```

Then configure the compressor intuitively via the GUI:

![alt text](https://cn.ifn.et.tu-dresden.de/wp-content/uploads/2019/08/printscreen.png)

Once configured, go inside the "Send" menu to "Listen for packets". This will start the reception of compressible streams which are sent by the sources as seen below as an example:

source_1 executes:
```sh
$ bash
$ sudo python3 node.py -n 1
```

source_2 executes:
```sh
$ bash
$ sudo python3 node.py -n 2
```

source_3 executes:
```sh
$ bash
$ sudo python3 node.py -n 3
```

Make sure that at least one of the streams are started within 60 seconds, otherwise the compressor will time out and stops listening for packets.
