# Network Coding Introduction #

This application contains the files to set up the environment for the Jupyter
notebooks used in the chapter of network coding. The idea is to present the
reader with the basic usage of Kodo (the network coding library) as well as some
guidance understanding the principles behind network coding.

This folder contains the following files:

1. Dockerfile: The dockerfile to build encoder, recoder and decoder VNF
   containers.

2. build_kodo_lib.sh: Script to build Kodo library on the system running the
   Testbed. Because Kodo requires [Licence](http://steinwurf.com/license.html),
   the binaries can not be released. The dynamic library file kodo.so must be
   built firstly and located in this directory to run the emulation. This script
   will build the library (source are downloaded in "$HOME/kodo-python") and
   copy it to this directory.

3. notebooks/: This folder contains the Jupyter notebooks used for teaching the
   basics on network coding.

You can set up the environment with the following commands:

```bash
$ bash ./build_kodo_lib.sh
$ docker build -t netcod .
$ docker run -p 8888:8888 netcod
```
Once you run the third command, in the console, you will see a link that you
must paste into a browser in order to access the Jupyter notebooks.