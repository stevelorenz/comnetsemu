ComNetsEmu
==========

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
application requires **root privilege**, hacking it inside a VM is also safer.

**MARK**: ComNetsEmu is developed with Python3 (3.6). Please use python3 command to run examples or applications.
Because the current master branch is still under heavy development, therefore this python3 module can be only installed
from source using setuptools. Pip package will be created for stable releases later.

ComNetsEmu uses Docker containers to emulate network nodes. Some images are used to run hosts and app containers in
examples and also applications. The Dockerfiles are located in ./test_containers

Please **build** them after the installation and **re-build** them after updates by running the script:

```bash
cd ./test_containers  || exit 0
bash ./build.sh
```

#### Install inside a VM

For development and using it as a playground, it is recommended to run ComNetsEmu INSIDE a VM. Run ComNetsEmu/Mininet
application requires root privilege, hacking it inside a VM is also safer. The pre-configured VM can be easily created
and managed with [Vagrant](https://www.vagrantup.com/). If the Vagrant and the VM hypervisor (
[Virtualbox](https://www.virtualbox.org/wiki/Downloads) is used in the ./Vagrantfile ) is installed properly. You can
create the VM with: `vagrant up comnetsemu`

The creation takes around 15 minutes. Then you can SSH into the VM with `vagrant ssh comnetsemu`, the directory of the
examples is in `/home/vagrant/comnetsemu/examples`.

#### (**Not Recommended!**) Install on the host OS (Currently **only** Ubuntu 18.04 is supported and tested)

- Install setup tools

    ```bash
    sudo apt update
    sudo apt install -y python3 libpython3-dev python3-dev git python3-pip
    ```

- Install ComNetsEmu with all components

    `PYTHON=python3 bash ./util/install.sh -a`

### Update ComNetsEmu Python Module

#### Install with python3 ./setup.py develop

You can update the package by fetching and merging the latest commit in the master branch.

```bash
git fetch origin master:master
git merge origin/master
```

#### Install with python3 ./setup.py install

Fetch and merge the last commit in the master branch like the first case.

Then the package must be re-installed with: `python3 ./setup.py install`

### Run examples

#### Run Docker-in-Docker example

The dockerindocker.py in the example fold show the basic functionality of running Docker container inside a Mininet
host(the host itself also uses Docker container). In order to run it, a Docker image with Docker installed must be
built. The Dockerfile for this can be found in ./test_containersDockerfile.dev_test The default image name used in
dockerindocker.py is dev_test.

```
cd ./test_containers || exit
sudo docker build -t dev_test -f Dockerfile.dev_test .
```

### Run multi-hop network coding example

The network coding example requires the licence of Kodo library from [Steiwurf](www.steinwurf.com). Contact them for
licence before running the example. Once you have the licence, run following commands:

```
cd ./app/nc/ || exit
bash ./build_kodo_lib.sh  # Build Kodo-python library on your host system to get the kodo.so shared library.
bash ./build_docker_images.sh  # Build the Docker image for encoders, recoders and docoders.
sudo python3 ./multihop_topo.py  # Run the NC emulation
```

#### Development Guide

- To build the API documentation (in HTML and PDF version), install doxygen and help2man packages and run `make doc`.

- In order to enable Docker-Docker setup, following modules are added in comnetemu:

  - comnetemu/node.py: Two sub-classes are added here to enable docker-in-docker setup:

      - DockerHost: Class of external containers. Its instances have the same methods of default Mininet host.

      - DockerContainer: Class of the internal container. To make it simple, currently there are no private methods
          implemented in this sub-class.

  - comnetemu/net.py: Two classes are added here to manage internal and external Docker hosts:

      - Containernet: Management of the external containers. Example of its APIs can be found [here](./examples/containernet_example.py).

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
