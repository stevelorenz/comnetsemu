# Installation

## Option 1: Install in a Vagrant managed VM (Highly Recommended)

The comfortable way to setup the test and development environment is to run a
pre-configured VM managed by [Vagrant](https://www.vagrantup.com/).
Vagrant supports multiple providers including Virtualbox and [Libvirt](https://libvirt.org/) (With [vagrant-libvirt plugin](https://github.com/vagrant-libvirt/vagrant-libvirt)).
Most examples and applications included in this repository can run on
Virtualbox which is cross-platform. Therefore, you host OS can be any OS that
supports Virtualbox (GNU/Linux, Windows and Mac OS etc.).

Mainly due to the performance and special feature requirements, some examples
and applications can run **only** on VM with
[KVM](https://en.wikipedia.org/wiki/Kernel-based_Virtual_Machine) as the
hypervisor:

1.  machine_learning_for_routing
1.  machine_learning_for_congestion_control

In order to run these programs, your host OS must use [Linux kernel](https://en.wikipedia.org/wiki/Linux_kernel).
You can install a GNU/Linux distribution on your physical machine.
WARN: Two providers can not be used at the same time.
Same VM can be created either by Virtualbox or KVM.

Recommended and tested setup:

-   Vagrant: >= v2.2.5 ([Download Link](https://www.vagrantup.com/downloads.html))
-   Virtualbox: >= v6.0 ([Download Link](https://www.virtualbox.org/wiki/Downloads))
-   (Optional) Libvirt: >= v6.0 ([Download Link](https://libvirt.org/downloads.html))
-   (Optional) Vagrant Libvirt Provider: >= v0.7.0 ([Download Link](https://github.com/vagrant-libvirt/vagrant-libvirt#installation))

A customized Vagrantfile is provided in this repository to manage the VM.
Both Virtualbox and Libvirt can be used to create the VM.
The default provider is Virtualbox.
Different providers uses different base boxes, please check the Vagrantfile for details.
You can choose the provider with `--provider` option of the `vagrant up` command.

*   Some Known Issues

Please follow the documentation to setup the VM with proper resource allocation.
If the `vagrant up` command fails to setup the VM fully correct which you can
test by running the basic *Docker-in-Docker* example.
Please firstly check the [known VM setup issues](./vm_setup_issues.md) for potential solutions.

*   VM Resource Allocation (**Important**)

By default, this VM is allocated with **2** vCPUs and **4GB** RAM to run all
examples and applications smoothly.
If you machine does not have enough resources, you need to change the variable
*CPUS* and *RAM* in the Vagrantfile **before** created the VM.

*   Use Virtualbox as Provider

To manage the Virtualbox VM, please open a terminal on your host OS and change
the working directory to the directory containing the ComNetsEmu's source code.
Use following commands to manage the VM.

```bash
# This will create the VM at the first time (takes around 20 minutes)
$ vagrant up comnetsemu

# SSH into the VM
$ vagrant ssh comnetsemu

# Power off the VM
$ vagrant halt comnetsemu

# Remove/Delete the VM
$ vagrant destroy comnetsemu
```

*   Use Libvirt as Provider

To create the VM with Libvirt provider, check the [guide](https://github.com/vagrant-libvirt/vagrant-libvirt#installation) to install the plugin.

After successful installation, run the following command in the ComNetsEmu's source directory:

```bash
$ vagrant up --provider libvirt comnetsemu
# Remove the VM managed by libvirt, the default provider is Virtualbox. 
# Use VAGRANT_DEFAULT_PROVIDER to force vagrant to use libvirt.
$ VAGRANT_DEFAULT_PROVIDER=libvirt vagrant destroy comnetsemu
```

*   Customization Shell Script

A customization shell script (should be located in `./util/vm_customize.sh`) is executed at the end of the provision process.
The script is executed by the `vagrant` user, who can run the sudo command without a password.
This script can be used to add your customization to the ComNetsEmu VM.

Example of `vm_customize.sh`:

```bash
sudo apt install -y zsh
# Install oh-my-zsh framework
sh -c "$(wget -O- https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"
```

As configured in `./Vagrantfile`, source code folder on the host OS is synced to the `/home/vagrant/comnetsemu` folder in the VM.
So you can work on emulators or application code in your host OS and run/test them in the VM.

Warning: Installation with option 1 is already finished here.
You can SSH into the VM to run examples and applications.
The option 2 is **only** for users who want to install it on their own customized VM or bare metal.

## Option 2: Install on user's custom VM or directly on host OS

As described above, installation on user's custom VM or directly on the host OS has several disadvantages.
It is not convenient to manage the test environment compared to the option 1.
For this option, it is recommended to install Ubuntu **20.04 LTS** **freshly**
inside the VM or as the host OS to avoid potential package conflicts.
Currently, this option is not well-tested compared to the option 1.

- Install essential packages required by the installer from your package management systems:

```bash
$ sudo apt update
$ sudo apt upgrade
$ sudo apt install git iperf iperf3 make pkg-config python3 python3-dev python3-pip sudo
```

- Install ComNetsEmu with all dependencies:

```bash
$ cd $TOP_DIR/comnetsemu/util
$ bash ./install.sh -a
```

## Option 3: Download the pre-built VM image

Only if the previous option does not suit you, please use this option.
Because the VM image may not be updated frequently and you need to manually
configure the VM for e.g. port forwarding, folder synchronization.

The VM image (comnetsemu.ova) for Virtualbox is uploaded to the [Google cloud
drive](https://drive.google.com/drive/folders/1FP5Bx2DHp7oV57Ja38_x01ABiw3wK11M?usp=sharing).
Please verify the sha512sum with the given files in the folder.

The default account and password for the VM are both `vagrant`.
There is no pre-configured root password.
The `vagrant` user can run `sudo` command without password, so root password
can be configured via `sudo passwd` if required.

For KVM user, you can convert the ova file to qcow2 file with following
commands (Assume the file has the name some\_name):

```bash
$ tar -xvf some_name.ova
$ qemu-img convert some_name.vmdk some_name.qcow2 -O qcow2
```

## Post-Installation

**MARK**: ComNetsEmu is developed with Python3 (3.8).
Please use `python3` command to run examples or applications.
Because the current master branch is still under heavy development, therefore
this `python3` package can be only installed from source using setuptools.

ComNetsEmu uses Docker containers to emulate network nodes.
Some images are used to run hosts and app containers in examples and also applications.
The Dockerfiles for external Docker hosts are located in `./test_containers`.

These Docker images are built automatically when the Vagrant VM is created.
The upgrade script of ComNetsEmu also rebuild them automatically.

If there is an error related to the test Docker images, they can be created also manually:

```bash
$ cd ./test_containers
# This script also removes all dangling images after build.
$ python ./build.py
```
