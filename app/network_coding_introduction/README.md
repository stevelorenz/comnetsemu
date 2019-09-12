# Network Coding Introduction #

This application contains the files to set up the environment for the jupyter
notebooks used in the chapter of network coding. The idea is to present the
reader with the basic usage of Kodo (the network coding library) as well as some
guidance understanding the principles behind network coding.

This folder contains the following files:

1. Dockerfile: The dockerfile to build encoder, recoder and decoder VNF
   containers.

2. build_kodo_lib.sh: Script to build Kodo library on the system running the
   Testbed. Because Kodo requires a
   [Licence](http://steinwurf.com/license.html), the binaries can not be
   released. We must build the dynamic library file kodo.so and copy it into the
   docker images. This script will build the library (source are downloaded in
   "$HOME/kodo-python") and copy it to this directory. During the build process,
   you will be asked to input your github username and password several times
   (one time per private repository pulled)

3. notebooks/: This folder contains the jupyter notebooks used for teaching the
   basics on network coding.

You can set up the environment with the following commands:

```bash
$ bash ./build_kodo_lib.sh
$ docker build -t netcod .
$ docker run -p 8888:8888 netcod
```
Once you run the third command, in the console, you will see a link that you
must paste into a browser in order to access the jupyter notebooks.

**INFO**: If you build and run the container inside the VM managed by the Vagrant, it's better to access the notebooks
link in the browser running on your **host** system.
(By default, no web browser is installed in the VM.)
The VM is configured with forwarded port: all_guest_ip:8888 to 127.0.0.1:8888 on the host.
You can paste the link into the browser running on your host system.
