ComNetsEmu
==========
*A holistic testbed/emulator for the book: Computing in Communication Networks: From Theory to Practice*


**This project is currently under heavy development [beta]**.

This project is currently hosted both on [Bitbucket](https://bitbucket.org/comnets/comnetsemu/src/master/) and
[Comnets Gitlab](https://git.comnets.net/book/comnetsemu) (on the server of [The Telekom Chair of Communication Networks](https://cn.ifn.et.tu-dresden.de/)).
The master and dev branches are synchronized. The **master** branch contains latest stable sources, the **dev** branch
is used as blessed branch for development.

Issues and pull requests can be created on **both** repositories.

### Description

ComNetsEmu is a tested and network emulator designed for the NFV/SDN teaching book "Computing in Communication Networks:
From Theory to Practice".  The design focus on emulating all examples and applications on a single physical machine,
e.g. on a single laptop. ComNetsEmu, SDN controller programs and emulated applications are mainly developed with
**Python3**(3.6).

#### What is Mininet and What's the main difference ?

Check the homepage of [Mininet](http://mininet.org/) for this great network emulator. The main difference of this fork
is: This version allows developer to deploy Docker containers *INSIDE* Mininet's hosts (Instead of Mininet's default
Host or CPULimitedHost, ComNetsEmu uses Docker containers for hosts), which is beneficial to emulate many practical
compute  and network setups. By default all Mininet's hosts share the host file system and PID space. And it is
non-trivial to let the application containers to share the networking stack of the Mininet's host. So in ComNetsEmu, the
Mininet's hosts are also Docker containers. New (heavyweight but more isolated/practical) host/node types are also
listed as potential enhancements to Mininet in [Mininet's official hackathon](https://github.com/acmsigcomm18hackathon/hackathonprojects/wiki/Mininet#enhancements-to-mininet).
ComNetsEmu aims at adding **essential** features/enhancements to Mininet for better emulations for SDN/NFV applications.

A simple example is given with a [sketch](./doc/figures/NFV_SDN_Testbed.png) for the emulation scenario: Assume Alice wants to
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
This is currently not supported in the Mininet's default host, therefore I replace it with Docker host (by integrating
codes from [Containernet](https://github.com/containernet/containernet)) to have a Docker-In-Docker setup. The internal
dockers are like PODs of the K8s and the external(outside) docker is the compute node of the Kubernetes.
Please check [Q&A](#### Q&A) section for why these decisions are made.

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
examples and also applications. The Dockerfiles for external Docker hosts are located in ./test_containers.

Please **build** them after the installation and **re-build** them after updates by running the script:

```bash
$ cd ./test_containers
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

#### Install on Ubuntu (Only tested on Ubuntu Server 18.04 LTS)

- Install required packages from your package management systems

    ```bash
    $ sudo apt update
    $ sudo apt install python3 libpython3-dev python3-dev git python3-pip make git sudo
    ```

- Install ComNetsEmu with all dependencies

    ```bash
    $ cd $HOME/comnetsemu/util
    $ PYTHON=python3 bash ./install.sh -a
    ```

### Update ComNetsEmu and  Dependencies

The master branch contains stable/tested sources for ComNetsEmu's python module, utility scripts, examples and
applications. It is recommended to update to latest commit of master branch.

The [installer script](./util/install.sh) has a function to update ComNetsEmu's python modules and dependencies software
automatically. This script **ONLY** supports Ubuntu/Debian (Tested on Ubuntu 18.04 LTS) and has some default variables:

1. The default remote name is origin and should linked to a fetch-0able Repository with latest updates. e.g. https://bitbucket.org/comnets/comnetsemu.git
2. The ComNetsEmu's source files are located in "$HOME/comnetsemu"
3. The dependencies installed from source are located in "$HOME/comnetsemu_dependencies"

You can modify these variables in the installer script for your customized installation.

Before run the update program, the source code directly (by default, "$HOME/comnetsemu") should be updated to the latest
commit in master branch via git:

```bash
$ cd $HOME/comnetsemu
$ git checkout master
$ git pull origin master
```

Then run following commands to update automatically (good luck ^_^):

```bash
$ cd $HOME/comnetsemu/util
$ bash ./install.sh -u
```

### Run basic examples

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
licence before running the example. Once you have the licence, check this
[guide](./app/network_coding_transport/README.md) to run this application.


### Catalog

- [app](./app/): All application programs are classified in this directory. Each subdirectory contains a brief
    introduction, source codes, Dockerfiles for internal containers and utility scripts of the application.

- [comnetsemu](./comnetsemu/): Source codes of ComNetsEmu's Python modules.

- [examples](./examples/): Example programs for functionalities of the emulator. Including all examples in upstream
    Mininet and additional examples of ComNetsEmu.

- [test_containers](./test_containers/): Contains Dockerfiles for external Docker containers (Docker host).

- [utils](./util/): Utility and helper scripts.

- [Vagrantfile](./Vagrantfile): Vagrant file to setup development/experiment VM environment.

### Development Guide and API Documentation

ComNetsEmu's documentation is generated by the same tool of Mininet: [doxygen](http://www.doxygen.nl/). Please install
doxygen and help2man before building the documentation. The built documentation has the same style of upstream Mininet's
[API documentation](http://mininet.org/api/hierarchy.html).

- Build and open HTML documentation in browser:

    ```bash
    $ make doc
    $ xdg-open ./doc/html/index.html
    ```

- To build PDF documentation with Latex, the `GENERATE_LATEX` flag in ./doc/Doxyfile should be set to `YES`.


#### Q&A

##### Ques: Why not default Mininet ?

Ans: Default Mininet (the latest version) does not support running Docker containers applications directly inside
Mininet Host with sufficient isolation. So I have to replace Mininet Host with Docker Host and add internal docker
functions on top of this modified version.

##### Ques: Why not Containernet ?

Ans: Containernet did a hard fork (hold all source codes of Mininet in its own Repo) of the Mininet. New features and
fixes from upstream Mininet can not be **merged** into Containernet **directly**. For example, while Mininet has already
updated to support Python3, Containernet still only supports Python2.7. Our ComNetsEmu is only an extension of the
upstream Mininet:

- Mininet's python modules are installed with its built-in installer.

- ComNetsEmu's python modules only create sub-classes of **essential and minimal** classes of Mininet to add its
    features. So Mininet must be installed before installing ComNetsEmu.

- With this development profile, upstream's commits can be updated easily by running the [installer's](./util/install.sh) update function.

- ComNetsEmu tries its best to keep the comparability with upstream Mininet. All examples, CLI commands of Mininet
    should also work on ComNetsEmu.

##### Ques: Why not Kubernetes(K8s)?

Ans: For teaching, K8s is too heavy and complex. We can emulate typical K8s setup with more lightweight virtualisation.
And thanks to Mininet, all links on the data plane can be configured with different bandwidth, link losses or transport
delay (Use Linux TC utility). It is great for teaching.


#### Useful Links

- [README](https://github.com/mininet/mininet) of upstream Mininet.
- [Mininet's Salk through Tutorial](http://mininet.org/walkthrough/)
- [Mininet's Python API Reference](http://mininet.org/api/hierarchy.html)
- [Docker Get Started Tutorial](https://docs.docker.com/get-started/)
- [Mininet SIGCOMM/Hackathon 2018](https://github.com/acmsigcomm18hackathon/hackathonprojects/wiki/Mininet#enhancements-to-mininet)

#### Maintainers

- Zuo Xiang (zuo.xiang@tu-dresden.de)
- Carl Collmann (carl.collmann@mailbox.tu-dresden.de)
