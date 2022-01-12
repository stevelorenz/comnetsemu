[![MIT Licensed](https://img.shields.io/github/license/stevelorenz/comnetsemu)](https://github.com/stevelorenz/comnetsemu/blob/master/LICENSE)
[![ComNetsEmu CI](https://github.com/stevelorenz/comnetsemu/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/stevelorenz/comnetsemu/actions/workflows/ci.yml)

ComNetsEmu
==========
*A virtual emulator/testbed designed for the book: [Computing in Communication Networks: From Theory to Practice](https://www.amazon.com/Computing-Communication-Networks-Theory-Practice-ebook/dp/B088ZS597R)*

This project has a online [Github page](https://stevelorenz.github.io/comnetsemu/) for Python API documentation and other useful documentation.
Please check it when you develop or use ComNetsEmu's Python APIs. 

**INFO: This project is currently still under development [beta]. Version 1.0.0 has not yet been released. We try to make it stable but breaking changes might happen.**

The repository is hosted both on the internal [Gitlab server of ComNets TUD](https://git.comnets.net/public-repo/comnetsemu) and
[Github](https://github.com/stevelorenz/comnetsemu).
The GitLab ComNets TUD is **read-only** for public users.
For all public users, if you have a question or want to contribute, please create an issue or send a pull request **on Github**.

## Table of Contents

<!-- vim-markdown-toc GitLab -->

* [Description](#description)
  * [Main Features](#main-features)
* [Installation](#installation)
* [Upgrade ComNetsEmu and Dependencies](#upgrade-comnetsemu-and-dependencies)
* [Run the Docker-in-Docker example](#run-the-docker-in-docker-example)
* [Project Structure](#project-structure)
* [Development Guide and API Documentation](#development-guide-and-api-documentation)
* [FAQ](#faq)
* [Contributing](#contributing)
* [Contact](#contact)

<!-- vim-markdown-toc -->

## Description

ComNetsEmu is a testbed and network emulator designed for the NFV/SDN teaching book ["Computing in Communication Networks: From Theory to Practice"](https://www.amazon.com/Computing-Communication-Networks-Theory-Practice-ebook/dp/B088ZS597R).
The design focuses on emulating all examples and applications on a single computer, for example on a laptop.
ComNetsEmu extends the famous [Mininet](http://mininet.org/) network emulator to support better emulation of versatile
**Computing In The Network (COIN) applications**.
It extends and puts forward the concepts and work in the [Containernet](https://containernet.github.io/) project.
It uses a slightly different approach to extend the Mininet compared to Containernet.
It's main focus is to use "sibling containers" to emulate network systems with **computing**.
See a more detailed comparison between upstream Mininet and Containernet [here](./doc/comparison.md).

Common facts about ComNetsEmu:

-   Emulation accuracy is highly considered, but it but can not be guaranteed for arbitrary topology. 
    All emulated nodes (processes) share the same underlying compute, storage and
    network resources when running it on a single system.
    ComNetsEmu is heavier than vanilla Mininet due to stricter node isolation. 
    Choosing a reasonable emulation parameters is required for correct simulation results. 
    [RT-Tests](https://wiki.linuxfoundation.org/realtime/documentation/howto/tools/rt-tests)
    is installed on the test VM.
    RT-Tests can be used to evaluate the real-time performance of the current emulation system.

-   ComNetsEmu is mainly developed with **Python3.8**.
    To reduce the complexity of dependencies (third-party packages, frameworks etc.), ComNetsEmu tries to leverage as much of the powerful Python standard library as possible, and prefers simple third-party dependencies when necessary.

-   Examples and applications in this repository are mainly developed with **high-level** script language for simplicity.
    These programs are **not** performance optimized.
    Please contact us if you want highly optimized implementation of the concepts introduced in this book.
    For example, we have [DPDK](https://www.dpdk.org/) accelerated version for low latency (sub-millisecond) Network Coding (NC) as a network function.

### Main Features

-   Use Docker hosts in Mininet topologies.

-   Manage application Docker containers deployed **inside** Docker hosts.
    "Docker-in-Docker" (sibling containers) is used as a lightweight emulation of nested virtualization.
    A Docker host with multiple **internal** Docker containers deployed is used to **mimic** an actual physical host running Docker containers (application containers).

-   A collection of application examples for "Computing In Communication Networks" with sample codes and
    detailed documentation.
    All examples can be easily reproduced and extended.

Check the [Roadmap](./doc/roadmap.md) for planed and WIP features.

## Installation

**Currently, only the latest Ubuntu 20.04 LTS is supported.**
**Supporting multiple Linux distributions is not the goal of this project.**

It is highly recommended to run ComNetsEmu **inside** a virtual machine.
**Root privileges** are required to run the ComNetsEmu/Mininet applications.
ComNetsEmu also uses privileged Docker containers by default.
It's also safer to play it inside a VM.
ComNetsEmu's [installation script](./util/install.sh) uses Mininet's install script to install Mininet natively from source.
As described in Mininet's doc, the install script is a bit **intrusive** and may possible **damage** your OS
and/or home directory.
ComNetsEmu runs smoothly in a VM with 2 vCPUs and 2GB RAM. (Host Physical CPU: Intel i7-7600U @ 2.80GHz).
Some more complex applications require more resources.
For example, the YOLO object detection application requires a minimum of 5GB of memory.

Firstly, clone the repository with `git`.
$TOP_DIR is the directory that you want to download the ComNetsEmu's source code.
In Vagrant VM, TOP_DIR="$HOME".
ComNetsEmu's installer (`BASH` scripts) assumes the name of the source directory is **comnetsemu** and will download external source dependencies in `$TOP_DIR/comnetsemu_dependencies`.

```bash
$ cd $TOP_DIR
$ git clone https://git.comnets.net/public-repo/comnetsemu.git comnetsemu
```

ComNetsEmu's [installer](./util/install.sh) tries to install dependencies with package manager (apt, pip etc.) if they are available.
Unavailable dependencies (e.g. latest stable Mininet) are installed from source code.
The source codes are downloaded into `"$TOP_DIR/comnetsemu_dependencies"` directory by default (It does not use a subdirectory inside the ComNetsEmu's source due to a file-permission issue of Vagrant (v2.2.5)).
The installer also checks the status of the dependency directory when upgrading is performed.
The ComNetsEmu's installer script is designed **mainly** for easy/simple setup/upgrade of the **Vagrant VM environment**.

**For users running Windows as the host OS:**

WARN: ComNetsEmu's main developer does not use Windows and does not have a Windows machine to test on.

1.  If you are using Windows, we recommend using [Mobaxterm](https://mobaxterm.mobatek.net/) as the console.
    This will solve problems opening `xterm` in the emulator.

The **recommended** way to install ComNetsEmu is to use Vagrant, please check
the installation guide [here](./doc/installation.md) (Use option 1 is recommend).

## Upgrade ComNetsEmu and Dependencies

ComNetsEmu's installer can only upgrade when ComNetsEmu's underlying Linux distribution is **not changed/upgraded**.
For example, you can use this upgrade function when Ubuntu 20.04 LTS is used as the base VM.
When the base VM is upgraded to the next LTS version, the upgrade function is not guaranteed to work since many packages are upgraded.
Therefore, it's suggested to `vagrant destroy` and `vagrant up` again when a new Ubuntu LTS is used as the base VM.
Thanks to Vagrant and Docker packaging, it should be not too difficult to re-create the environment after rebuild the VM.

Example screenshots for running the upgrade process in terminal:

![Screenshots for Running Upgrade Process](./doc/comnetsemu_upgrade.gif)

The **master** branch contains stable/tested sources for ComNetsEmu's python package, utility scripts, examples and applications.
It is **recommended** to upgraded to **latest** commit of the **master** branch or the latest tag published [here](https://git.comnets.net/public-repo/comnetsemu/-/tags).

The [installer script](./util/install.sh) has a function to upgrade ComNetsEmu automatically.
And the installer script also needs to be updated firstly.
Therefore, it takes **three** steps to upgrade everything.
It is assumed here the ComNetsEmu is installed using option 1 with Vagrant.

### Step 1: Upgrade source code of ComNetsEmu Python package, examples and applications on your host OS.

Use git to pull (or fetch+merge if you want to) the latest commit in master branch:

```bash
$ cd ~/comnetsemu
$ git checkout master
$ git pull origin master
```

### Step 2: Upgrade ComNetsEmu Python module and all dependencies automatically inside VM.

The [installer script](./util/install.sh) is used to perform this step.
This script **ONLY** works on supported distributions and has some default variables:

1. The ComNetsEmu's source files are located in "~/comnetsemu"
2. The dependencies installed from source are located in "~/comnetsemu_dependencies"

Run following command to upgrade automatically:

```bash
$ cd ~/comnetsemu/util
$ bash ./install.sh -u
```

The script may ask you to input yes or no several times, please read the terminal output for information.

### Step 3: Check if the upgrading is successful inside VM.

Run following commands to run tests:

```bash
$ cd ~/comnetsemu/
$ sudo make test && sudo make test-examples
```

If all tests pass without any errors or exceptions, the upgrading was successful.
Otherwise, it is recommended to redo the upgrade process or just rebuild the
Vagrant VM if the situation is too bad...

## Run the Docker-in-Docker example

```bash
$ cd $TOP_DIR/comnetsemu/examples/
$ sudo python3 ./dockerindocker.py
```

See the [README](./examples/README.md) to get information about all built-in examples.

## Project Structure

To keep the VMs small, Vagrantfile and test_containers contain only **minimal** dependencies to start the VMs and be able to run all the built-in examples.
Dependencies of specific applications (e.g. Python packages like numpy, scipy etc.) should be installed by the script or instructions provided in the corresponded application folder.
Therefore, the user need to install them **only if** she or he wants to run that application.

-   [app](./app/): All application programs are classified in this directory.
    Each subdirectory contains a brief introduction, source codes, Dockerfiles for internal containers and utility scripts of the application

-   [bin](./bin): Commands and binaries provided by ComNetsEmu

-   [comnetsemu](./comnetsemu/): Source codes of ComNetsEmu's Python packages

-   [doc](./doc): Markdown files and sources to generate ComNetsEmu Sphinx documentation

-   [examples](./examples/): Example programs for functionalities of the ComNetsEmu emulator

-   [patch](./patch/): Patches for external dependencies that are installed 
    from source code via [installer](./util/install.sh)

-   [test_containers](./test_containers/): Contains Dockerfiles for essential Docker images
    for tests and built-in examples

-   [utils](./util/): Utility and helper scripts

-   [Vagrantfile](./Vagrantfile): Vagrant file to setup development/experiment VM environment

## Development Guide and API Documentation

Please check the online [documentation page](https://stevelorenz.github.io/comnetsemu/).

## FAQ

Check [faq](./doc/faq.md)

## Contributing

This project exists thanks to all people who contribute.
[List](./CONTRIBUTORS) of known contributors.

For all public users, please create issues or send pull requests on 
[Github](https://github.com/stevelorenz/comnetsemu).

## Contact

Project main maintainers:

- Zuo Xiang: zuo.xiang@tu-dresden.de (office), xianglinks@gmail.com (personal)
