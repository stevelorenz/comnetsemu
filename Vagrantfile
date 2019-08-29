# -*- mode: ruby -*-
# vi: set ft=ruby :
# About: Vagrant file for the development environment

###############
#  Variables  #
###############

CPUS = 2
# - YOLOv2 object detection application requires 4GB RAM to run smoothly
RAM = 4096

# Bento: Packer templates for building minimal Vagrant baseboxes
# The bento/ubuntu-18.04 is a small image of 500 MB, fast to download
BOX = "bento/ubuntu-18.04"
BOX_VER = "201906.18.0"
VM_NAME = "ubuntu-18.04-comnetsemu"

######################
#  Provision Script  #
######################

# Common bootstrap
$bootstrap= <<-SCRIPT
# Install dependencies
apt-get update
apt-get upgrade -y
# Essential packages used by ./util/install.sh
apt-get install -y git make pkg-config sudo python3 libpython3-dev python3-dev python3-pip software-properties-common
# Test/Development utilities
apt-get install -y bash-completion htop dfc gdb tmux
apt-get install -y iperf iperf3
SCRIPT

$setup_x11_server= <<-SCRIPT
apt-get install -y xorg
apt-get install -y openbox
SCRIPT

# Use v4.19 LTS, EOL: Dec, 2020
# For AF_XDP, EROFS etc.
$install_kernel= <<-SCRIPT
# Install libssl1.1 from https://packages.ubuntu.com/bionic/amd64/libssl1.1/download
echo "deb http://cz.archive.ubuntu.com/ubuntu bionic main" | tee -a /etc/apt/sources.list > /dev/null
apt update
apt install -y libssl1.1
cd /tmp || exit
wget -c http://kernel.ubuntu.com/~kernel-ppa/mainline/v4.19/linux-headers-4.19.0-041900_4.19.0-041900.201810221809_all.deb
wget -c http://kernel.ubuntu.com/~kernel-ppa/mainline/v4.19/linux-headers-4.19.0-041900-generic_4.19.0-041900.201810221809_amd64.deb
wget -c http://kernel.ubuntu.com/~kernel-ppa/mainline/v4.19/linux-image-unsigned-4.19.0-041900-generic_4.19.0-041900.201810221809_amd64.deb
wget -c http://kernel.ubuntu.com/~kernel-ppa/mainline/v4.19/linux-modules-4.19.0-041900-generic_4.19.0-041900.201810221809_amd64.deb
dpkg -i *.deb
update-initramfs -u -k 4.19.0-041900-generic
update-grub
SCRIPT

####################
#  Vagrant Config  #
####################

#if Vagrant.has_plugin?("vagrant-vbguest")
#  config.vbguest.auto_update = false
#end


Vagrant.configure("2") do |config|

  if Vagrant.has_plugin?("vagrant-vbguest")
    config.vbguest.auto_update = false
  end

  config.vm.define "comnetsemu" do |comnetsemu|

    comnetsemu.vm.hostname = "comnetsemu"
    comnetsemu.vm.box = BOX
    comnetsemu.vm.box_version = BOX_VER
    comnetsemu.vm.box_check_update = true

    comnetsemu.vm.post_up_message = '
VM started! Run "vagrant ssh <vmname>" to connect.

INFO !!! For all developers:

If there are any new commits in the dev branch in the remote repository, Please do following steps to upgrade dependencies:

- [On the host system] Fetch and merge new commits from upstream dev branch and solve potential conflicts.
  By default, ComNetsEmu Python module is installed using develop mode inside VM, so the updates of the module should be applied automatically inside VM. No re-install is required.

- [Inside Vagrant VM] Change current path to "/home/vagrant/comnetsemu/util" and run "$ PYTHON=python3 ./install.sh -u" to check and upgrade all dependencies when required.

- [Inside Vagrant VM] Rebuild the containers in "test_containers" with "build.sh" (The dockerfile may be modified in the latest updates)

- [On the host system] If the Vagrant file is modified in the lastest updates. run "$ vagrant provision" to re-provision the created VM.
    '

    # Sync ./ to home dir of vagrant to simplify the install script
    comnetsemu.vm.synced_folder ".", "/vagrant", disabled: true
    comnetsemu.vm.synced_folder ".", "/home/vagrant/comnetsemu"

    # Workaround for vbguest plugin issue
    comnetsemu.vm.provision "shell", run: "always", inline: <<-WORKAROUND
    modprobe vboxsf || true
    WORKAROUND

    comnetsemu.vm.provision :shell, inline: $bootstrap, privileged: true
    comnetsemu.vm.provision :shell, inline: $install_kernel, privileged: true
    comnetsemu.vm.provision :shell, inline: $setup_x11_server, privileged: true

    comnetsemu.vm.provision "shell", privileged: false, inline: <<-SHELL
      cd /home/vagrant/comnetsemu/util || exit
      PYTHON=python3 ./install.sh -a

      cd /home/vagrant/comnetsemu/ || exit
      # setup.py develop installs the package (typically just a source folder)
      # in a way that allows you to conveniently edit your code after it is
      # installed to the (virtual) environment, and have the changes take
      # effect immediately. Convinient for development
      sudo make develop

      # Build images for Docker hosts
      cd /home/vagrant/comnetsemu/test_containers || exit
      bash ./build.sh

      # Run the customization shell script (for distribution $BOX) if it exits.
      cd /home/vagrant/comnetsemu/util || exit
      if [ -f "./vm_customize.sh" ]; then
        echo "*** Run VM customization script."
        bash ./vm_customize.sh
      fi
    SHELL

    # Always run this when use `vagrant up`
    # - Check to update all dependencies
    # ISSUE: The VM need to have Internet connection to boot up...
    #comnetsemu.vm.provision :shell, privileged: true, run: "always", inline: <<-SHELL
    #  cd /home/vagrant/comnetsemu/util || exit
    #  PYTHON=python3 ./install.sh -u
    #SHELL

    # Enable X11 forwarding
    comnetsemu.ssh.forward_agent = true
    comnetsemu.ssh.forward_x11 = true

    # VirtualBox-specific configuration
    comnetsemu.vm.provider "virtualbox" do |vb|
      vb.name = VM_NAME
      vb.memory = RAM
      vb.cpus = CPUS
      # MARK: The CPU should enable SSE3 or SSE4 to compile DPDK
      vb.customize ["setextradata", :id, "VBoxInternal/CPUM/SSE4.1", "1"]
      vb.customize ["setextradata", :id, "VBoxInternal/CPUM/SSE4.2", "1"]
    end
  end

  # INFO: This VM is **ONLY** used to test the installation and configuration of the emulation environment.
  # It is used to avoid destroying the comnetsemu VM that can contain several already built Docker images.
  # Currently the CI pipeline of the project is not finshed, this VM is used for developers to make sure the installer works for Vagrant VM.
  config.vm.define "vm2testinstall" do |vm2testinstall|

    vm2testinstall.vm.hostname = "vm2testinstall"
    vm2testinstall.vm.box = BOX
    vm2testinstall.vm.box_version = BOX_VER
    vm2testinstall.vm.box_check_update = true

    vm2testinstall.vm.provision "shell", run: "always", inline: <<-WORKAROUND
    modprobe vboxsf || true
    WORKAROUND

    vm2testinstall.vm.provision :shell, inline: $bootstrap, privileged: true
    vm2testinstall.vm.provision :shell, inline: $install_kernel, privileged: true
    vm2testinstall.vm.provision :shell, inline: $setup_x11_server, privileged: true

    vm2testinstall.vm.provision "shell", privileged: false, inline: <<-SHELL
      # Used to export the latest modified VM from virtualbox for sharing
      cp -r /vagrant /home/vagrant/comnetsemu

      cd /home/vagrant/comnetsemu/util || exit
      PYTHON=python3 ./install.sh -a

      cd /home/vagrant/comnetsemu/ || exit
      rm -rf .git* .coverage .pytest_cache/ .pytype/ .vagrant/
      sudo make develop

      cd /home/vagrant/comnetsemu/test_containers || exit
      bash ./build.sh
    SHELL

    vm2testinstall.ssh.forward_agent = true
    vm2testinstall.ssh.forward_x11 = true

    vm2testinstall.vm.provider "virtualbox" do |vb|
      vb.name = "comnetsemu-vm2testinstall"
      vb.memory = RAM
      vb.cpus = CPUS
      vb.customize ["setextradata", :id, "VBoxInternal/CPUM/SSE4.1", "1"]
      vb.customize ["setextradata", :id, "VBoxInternal/CPUM/SSE4.2", "1"]
    end
  end

end
