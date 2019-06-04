ComNetsEmu
==========

This project is currently **under heavy development**.

### Description

ComNetsEmu is a tested and network emulator designed for the NFV/SDN teaching book.  The design focus on emulating all
applications on a single physical machine, e.g. on a single laptop. ComNetsEmu, SDN controller programs and emulated
applications are developed with **Python3**(3.6).

#### What is Mininet and What's the main difference ?

Check the homepage of [Mininet](http://mininet.org/) for this great network emulator. The main difference of this fork
is: This version allows developer to deploy Docker containers *INSIDE* Mininet hosts (also use Docker instead of the
default Mininet light process-based isolation), which is beneficial to emulate many practical scenarios.

A simple example is given with a [sketch](./doc/NFV_SDN_Testbed.png) for the emulation scenario: Assume Alice wants to
send packets to Bob with random linear network coding. Packet has to be transmitted through two switches S1 and S2. Link
losses (It is not true in the wired domain, however, we just want to simulate the channel losses, packets are dropped in
the queue of the switch manually.) exit in each link on the data plane. In order to mitigate the channel losses, the
recoding should be performed. According to the Service Function Chain proposed in [RFC
7665](https://datatracker.ietf.org/doc/rfc7665/), instead of directly forwarding packets to S2, the S1 can redirect the
packets to a host on which multiple network functions are running. Recoding can be deployed as a virtualized network
function (VNF) on NF1 or NF2 based on the channel loss rates. The recoding VNF can also migrate between NF1 and NF2 and
be adaptive to the dynamics of the channel loss rates. For teaching purpose, We want the students can emulate all
practical and real-world scenarios on NFV/SDN deployment on a single laptop.  It should be as lightweight as possible.
So in our Testbed, the physical machines (Alice, Bob, NFs) are emulated with Mininet Hosts. They have long-and-alive
PIPEs open (stdin, stdout and stderr) that can be used by the Mininet manager to e.g. run arbitrary commands during the
emulation. The VNFs or cloud applications are encapsulated in Docker containers and deployed inside each Mininet Host.
In order to emulate this, the application containers (a.k.a internal containers) should be isolated: It should inherent
from the resource isolation of corresponded Mininet Host and also inherent the network namespace of its Mininet Host.
This is currently not supported in the Mininet's default host, therefore I replace it with Docker host to have a
Docker-In-Docker setup. The internal dockers are like PODs of the K8s and the external(outside) docker is the compute
node of the Kubernetes.

### Installation

For development and using it as a playground, it is recommended to run ComNetsEmu INSIDE a VM. Run ComNetsEmu/Mininet
application requires **root privilege**, hacking it inside a VM is also safer. ComNetsEmu's [install
script](./util/install.sh) uses Mininet's install script to install Mininet natively from source. As described in
Mininet's doc, the install script is a bit **intrusive** and may possible **damage** your OS and/or home directory. It
is recommended to trying and installing ComNetsEmu in a VM. It runs smoothly in a VM with 2 vCPUs and 2GB RAM. (Physical
CPU: Intel i7-7600U @ 2.80GHz).

**MARK**: ComNetsEmu is developed with Python3 (3.6). Please use python3 command to run examples or applications.
Because the current master branch is still under heavy development, therefore this python3 module can be only installed
from source using setuptools. Pip package will be created for stable releases later.

ComNetsEmu uses Docker containers to emulate network nodes. Some images are used to run hosts and app containers in
examples and also applications. The Dockerfiles are located in ./test_containers

Please **build** them after the installation and **re-build** them after updates by running the script:

```bash
$ cd ./test_containers  || exit 0
$ bash ./build.sh
```

#### Install in a Vagrant managed VM for Development

For example and application developers, the comfortable way to setup the development environment is to run a
pre-configured VM managed by [Vagrant](https://www.vagrantup.com/). If the Vagrant and the VM hypervisor (
[Virtualbox](https://www.virtualbox.org/wiki/Downloads) is used in the ./Vagrantfile ) are installed properly. You can
manage the VM with (cd to the same directory of the Vagrantfile):

```bash
# This will create the VM at the first time (takes around 15 minutes)
$ vagrant up comnetsemu

# SSH into the VM
$ vagrant ssh comnetsemu

# Poweroff the VM
$ vagrant halt comnetsemu

# Remove the VM
$ vagrant destory comnetsemu
```

As configured in ./Vagrantfile, current source code folder on the host OS is synced to the `/home/vagrant/comnetsemu`
folder in the VM. And the emulator's Python modules are installed in development mode. So you can work on the emulator
or application codes in your host OS and run/test them in the VM.

#### Install on Ubuntu (Tested on Ubuntu Server 18.04 LTS)

The install script currently only supports Debian/Ubuntu.

- Install required packages from your package management systems

    ```bash
    $ sudo apt update
    $ sudo apt install python3 libpython3-dev python3-dev git python3-pip
    ```

- Install ComNetsEmu with all components

    `$ PYTHON=python3 bash ./util/install.sh -a`

### Update ComNetsEmu From Source

The master branch contains stable/tested sources.

#### Update examples and application source codes

You can update them by fetching and merging the latest commit in the master branch:

```bash
$ git fetch origin master:master
$ git merge origin/master
```

#### Update ComNetsEmu emulator

You can use the installer script to update installed ComNetsEmu python modules, examples, application sources and
required dependencies (WARN: this script is only tested on Ubuntu 18.04 LTS). The script has some default variables:

1. The default remote name is origin and should linked to a fetch-0able Repository with latest updates. e.g. https://bitbucket.org/comnets/comnetsemu.git
2. The ComNetsEmu's source files are located in "$HOME/comnetsemu"
3. The dependencies installed from source are located in "$HOME/comnetsemu_dependencies"


Run following commands to update (good luck ^_^):

```bash
$ cd $HOME/comnetsemu
$ git checkout master
$ git pull origin master
$ cd ./util/
$ bash ./install.sh -u
```


### Run examples

In order to run examples, the Docker image described in ./test_containers/Dockerfile.dev_test must be built with
./test_containers/build.sh .

#### Run Docker host example

./examples/dockerhost.py shows the management of Docker hosts (external containers) in ComNetsEmu. It shows how to
create a network with Docker hosts, switches and connect them with configurable (bandwidth, delay and loss rate) links.
It also shows how to change the loss rate of a host's interface (with Linux NetEm) at runtime.

#### Run Docker-in-Docker example

The dockerindocker.py in the example fold show the basic functionality of running Docker container inside a Mininet
host(the host itself also uses Docker container). It shows how to add/remove internal containers on running Docker hosts
and also change the resource limitation of Docker hosts at runtime.

### Run network coding for transport application example

The network coding example requires the licence of Kodo library from [Steiwurf](www.steinwurf.com). Contact them for
licence before running the example. Once you have the licence, run following commands:

```
$ cd ./app/network_coding_transport/ || exit
$ bash ./build_kodo_lib.sh  # Build Kodo-python library on your host system to get the kodo.so shared library.
$ bash ./build_docker_images.sh  # Build the Docker image for encoders, recoders and docoders.
$ sudo python3 ./multihop_topo.py  # Run the emulation of multi-hop topology
```

#### Development Guide

- To build the API documentation (in HTML and PDF version), install doxygen and help2man packages and run `make doc`.

- In order to enable Docker-Docker setup, following modules are added in comnetsemu:

  - comnetsemu/node.py: Two sub-classes are added here to enable docker-in-docker setup:

      - DockerHost: Class of external containers. Its instances have the same methods of default Mininet host.

      - DockerContainer: Class of the internal container. To make it simple, currently there are no private methods
          implemented in this sub-class.

  - comnetsemu/net.py: Two classes are added here to manage internal and external Docker hosts:

      - Containernet: Management of the external containers. Example of its APIs can be found [here](./examples/dockerhost.py).

      - VNFManager: Management of the internal containers. To make it simple, currently there are only create, delete and
          the cleanup methods are implemented. More methods will be added depending on to be deployed applications.


#### Q&A

##### Ques: Why not default Mininet ?

Ans: Default Mininet (the latest version) does not support running Docker containers applications directly inside
Mininet Host with sufficient isolation. So I have to replace Mininet Host with Docker Host and add internal docker
functions on top of this modified version.

##### Ques: Why not Kubernetes(K8s)?

Ans: For teaching, K8s is too heavy and complex. We can emulate typical K8s setup with more lightweight virtualisation.
And thanks to Mininet, all links on the data plane can be configured with different bandwidth, link losses or transport
delay (Use Linux TC utility). It is great for teaching.


#### MISC

- [README](https://github.com/mininet/mininet) of upstream Mininet.

#### Maintainers

- Zuo Xiang (zuo.xiang@tu-dresden.de)
- Carl Collmann (carl.collmann@mailbox.tu-dresden.de)
