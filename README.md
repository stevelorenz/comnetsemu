ComNetsEmu
==========
*A holistic testbed/emulator for the book: Computing in Communication Networks: From Theory to Practice*


**This project is currently under heavy development [beta]**.

This project is currently hosted both on [Bitbucket](https://bitbucket.org/comnets/comnetsemu/src/master/) and [Comnets
Gitlab](https://git.comnets.net/book/comnetsemu) (on the server of [The Telekom Chair of Communication
Networks](https://cn.ifn.et.tu-dresden.de/)).  The master and dev branches are synchronized. The **master** branch
contains latest stable sources, the **dev** branch is used as blessed branch for development.

Issues and pull requests can be created on **both** repositories. Please create an issues if there are any problems or
feature requirement of the tested. It will be answered more quickly than Emails.

### Description

ComNetsEmu is a tested and network emulator designed for the NFV/SDN teaching book "Computing in Communication Networks:
From Theory to Practice".  The design focus on emulating all examples and applications on a single computer, e.g. on a
single laptop. ComNetsEmu extends the famous [Mininet](http://mininet.org/) emulator to support better emulation of
versatile NFV/SDN network **applications**.
See the comparison between upstream Mininet [here](./doc/comparison.md).

Common facts about ComNetsEmu:

- Emulation performance is considered but not the main focus. All emulated nodes (processes) share the same underlying
    compute, storage and network resources when running it on a single system. ComNetsEmu is heavier than vanilla
    Mininet due to complete host isolation. Chose a reasonable performance limitation is recommended for better
    emulation results. For example, use e.g. 100ms as link delay instead of 1ms for large scale topology.

- ComNetsEmu is developed with **Python3.6**.

#### Main Features

- Use Docker hosts in Mininet topologies.

- Manage application Docker containers deployed INSIDE Docker hosts. Docker-in-Docker(dind) is used by ComNetsEmu as an
    lightweight emulation for nested-virtualization. The Docker host with internal Docker containers deployed is used to
    **mimic** an actual physical host that runs Docker containers.

### Installation

For development and using it as a playground, it is recommended to run ComNetsEmu INSIDE a VM. Run ComNetsEmu/Mininet
application requires **root privilege**, hacking it inside a VM is also safer. ComNetsEmu's [install
script](./util/install.sh) uses Mininet's install script to install Mininet natively from source. As described in
Mininet's doc, the install script is a bit **intrusive** and may possible **damage** your OS and/or home directory. It
is recommended to trying and installing ComNetsEmu in a VM. It runs smoothly in a VM with 2 vCPUs and 2GB RAM. (Physical
CPU: Intel i7-7600U @ 2.80GHz).

**MARK**: ComNetsEmu is developed with Python3 (3.6). Please use `python3` command to run examples or applications.
Because the current master branch is still under heavy development, therefore this `python3` module can be only
installed from source using setuptools. Pip package will be created for stable releases later.

ComNetsEmu uses Docker containers to emulate network nodes. Some images are used to run hosts and app containers in
examples and also applications. The Dockerfiles for external Docker hosts are located in ./test_containers.

Please **build** them after the installation and **re-build** them after updates by running the script:

```bash
$ cd ./test_containers
# This script removes all dangling images after build.
$ bash ./build.sh
```

[Here](./doc/dependencies.md) is a list of dependencies required by ComNetsEmu, these tools can be installed and updated by
ComNetsEmu's [installer](./util/install.sh).

#### Option 1: Install in a Vagrant managed VM (Highly Recommended)

The comfortable way to setup the test and development environment is to run a pre-configured VM managed by [Vagrant](https://www.vagrantup.com/).
It supports different VM hypervisor and [Virtualbox](https://www.virtualbox.org/) is used in project's [Vagrantfile](./Vagrantfile).

Recommended setup:

- Vagrant: v2.2.5 and beyond ([Download Link](https://www.vagrantup.com/downloads.html))
- Virtualbox: v6.0 and beyond ([Download Link](https://www.virtualbox.org/wiki/Downloads))

You can create and manage the VM with (cd to the same directory of the [Vagrantfile](./Vagrantfile)):

```bash
# This will create the VM at the first time (takes around 20 minutes)
$ vagrant up comnetsemu

# SSH into the VM
$ vagrant ssh comnetsemu

# Poweroff the VM
$ vagrant halt comnetsemu

# Remove/Delete the VM
$ vagrant destory comnetsemu
```

A customization shell script (should be located in `./util/vm_customize.sh`) is executed at the end of the provision
process.  This script can be used to add your customized tools (e.g. ZSH, Desktop environment etc) and
configuration to the ComNetsEmu VM. Since the vagrant VM uses Ubuntu LTS, apt should be used to manage the packages.

Example of `vm_customize.sh`:
```bash
sudo apt install -y zsh
# Install oh-my-zsh framework
sh -c "$(wget -O- https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"
```

The `vagrant up` should run correctly. If there are some "apt" or "dpkg" related error messages (like some packages can
not be found or installed) during the `vagrant up`, it might due to the box you used to build the VM is outdated. It is
configured in current ./Vagrantfile that the vagrant will check if there are any updates to the box used in the current
environment.  It can be checked manually with `vagrant box update`. You need to destroy the already built VM and
recreate it to acquire the new updates in the box with:

```bash
$ vagrant box update
$ vagrant destory comnetsemu
# This will create the VM at the first time (takes around 15 minutes)
$ vagrant up comnetsemu
```

As configured in ./Vagrantfile, current source code folder on the host OS is synced to the `/home/vagrant/comnetsemu`
folder in the VM. And the emulator's Python modules are installed in development mode. So you can work on the emulator
or application codes in your host OS and run/test them in the VM.

#### Option 2: Install on Ubuntu (Only tested on Ubuntu Server 18.04 LTS (Bionic Beaver))

INFO: Currently, the installer **ONLY** supports Ubuntu-based Linux distributions. Support for more distributions is in
the TODO list.

- Install essential packages required by the installer from your package management systems:

```bash
$ sudo apt update
$ sudo apt upgrade
$ sudo apt install git make pkg-config sudo python3 libpython3-dev python3-dev python3-pip software-properties-common
```

- Install ComNetsEmu with all dependencies:

```bash
$ cd $HOME/comnetsemu/util
$ PYTHON=python3 bash ./install.sh -a
```

### Upgrade ComNetsEmu and Dependencies

The **master** branch contains stable/tested sources for ComNetsEmu's python module, utility scripts, examples and
applications. It is recommended to upgraded to latest commit of the master branch.

The [installer script](./util/install.sh) has a function to ONLY upgrade ComNetsEmu's dependencies software
automatically. This script **ONLY** supports Ubuntu (Tested on Ubuntu 18.04 LTS) and has some default variables:

1. The ComNetsEmu's source files are located in "$HOME/comnetsemu"
2. The dependencies installed from source are located in "$HOME/comnetsemu_dependencies"

You can modify these variables in the installer script for your customized installation.

**WARNING**: The upgrade function does not re-install(upgrade) the Python module of ComNetsEmu. If the Vagrant VM is
used, the develop mode and sync folder are used to apply changes automatically. Otherwise, the module should be
re-installed manually.

Before running the upgrade function, the source code repository (by default, "$HOME/comnetsemu") should be updated to the latest
commit in master branch via git (fix conflicts if required):

```bash
$ cd $HOME/comnetsemu
$ git checkout master
$ git pull origin master
```

Then run following commands to upgrade automatically (good luck ^_^):

```bash
$ cd $HOME/comnetsemu/util
$ bash ./install.sh -u
```

### Run the Docker-in-Docker example

```bash
$ cd $HOME/comnetsemu/examples/
$ sudo python3 .dockerindocker.py
```

See the [README](./examples/README.md) to get information about all built-in examples.

### Catalog

- [app](./app/): All application programs are classified in this directory. Each subdirectory contains a brief
    introduction, source codes, Dockerfiles for internal containers and utility scripts of the application.

- [comnetsemu](./comnetsemu/): Source codes of ComNetsEmu's Python modules.

- [examples](./examples/): Example programs for functionalities of the ComNetsEmu emulator.

- [test_containers](./test_containers/): Contains Dockerfiles and dependency files for external Docker containers (Docker host).

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

### [Q&A](./doc/q_and_a.md)

### [Useful Links](./doc/ref_links.md)

### Maintainers

- Zuo Xiang (zuo.xiang@tu-dresden.de)
- Carl Collmann (carl.collmann@mailbox.tu-dresden.de)
