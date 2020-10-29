# -*- mode: ruby -*-
# vi: set ft=ruby :
# About: Vagrant file for the development environment

###############
#  Variables  #
###############

CPUS = 2
# - 2GB RAM should be sufficient for most examples and applications.
# - Currently only YOLOv2 object detection application requires 4GB RAM to run smoothly.
# - Reduce the memory number (in MB) here if you physical machine does not have enough physical memory.
RAM = 4096

# Bento: Packer templates for building minimal Vagrant baseboxes
# The bento/ubuntu-18.04 is a small image of 500 MB, fast to download
BOX = "bento/ubuntu-18.04"
VM_NAME = "ubuntu-18.04-comnetsemu"

# Box for using libvirt as the provider, bento boxes do not support libvirt.
BOX_LIBVIRT = "generic/ubuntu1804"

######################
#  Provision Script  #
######################

# Common bootstrap
$bootstrap= <<-SCRIPT
# Install dependencies
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" upgrade

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

# Use v5.4 LTS, EOL: Dec, 2025
# For eBPF, XDP, AF_XDP, EROFS etc.
$install_kernel= <<-SCRIPT
# Install libssl1.1 from https://packages.ubuntu.com/bionic/amd64/libssl1.1/download
echo "deb http://cz.archive.ubuntu.com/ubuntu bionic main" | tee -a /etc/apt/sources.list > /dev/null
apt update
apt install -y libssl1.1
cd /tmp || exit
wget -c https://kernel.ubuntu.com/~kernel-ppa/mainline/v5.4.70/amd64/linux-headers-5.4.70-050470_5.4.70-050470.202010070732_all.deb
wget -c https://kernel.ubuntu.com/~kernel-ppa/mainline/v5.4.70/amd64/linux-headers-5.4.70-050470-generic_5.4.70-050470.202010070732_amd64.deb
wget -c https://kernel.ubuntu.com/~kernel-ppa/mainline/v5.4.70/amd64/linux-image-unsigned-5.4.70-050470-generic_5.4.70-050470.202010070732_amd64.deb
wget -c https://kernel.ubuntu.com/~kernel-ppa/mainline/v5.4.70/amd64/linux-modules-5.4.70-050470-generic_5.4.70-050470.202010070732_amd64.deb
dpkg -i *.deb
update-initramfs -u -k 5.4.70-050470-generic
update-grub
SCRIPT

$post_installation= <<-SCRIPT
# Allow vagrant user to use Docker without sudo
usermod -aG docker vagrant
if [ -d /home/vagrant/.docker ]; then
  chown -R vagrant:vagrant /home/vagrant/.docker
fi
SCRIPT

####################
#  Vagrant Config  #
####################

require 'optparse'

# Parse the provider argument
def get_provider
  ret = nil
  opt_parser = OptionParser.new do |opts|
    opts.on("--provider provider") do |provider|
      ret = provider
    end
  end
  opt_parser.parse!(ARGV)
  ret
end
provider = get_provider || "virtualbox"


Vagrant.configure("2") do |config|

  if Vagrant.has_plugin?("vagrant-vbguest")
    config.vbguest.auto_update = false
  end

  config.vm.define "comnetsemu" do |comnetsemu|

    # VirtualBox-specific configuration
    comnetsemu.vm.provider "virtualbox" do |vb|
      vb.name = VM_NAME
      vb.cpus = CPUS
      vb.memory = RAM
      # MARK: The CPU should enable SSE3 or SSE4 to compile DPDK applications.
      vb.customize ["setextradata", :id, "VBoxInternal/CPUM/SSE4.1", "1"]
      vb.customize ["setextradata", :id, "VBoxInternal/CPUM/SSE4.2", "1"]
    end

    comnetsemu.vm.provider "libvirt" do |libvirt|
      libvirt.driver = "kvm"
      libvirt.cpus = CPUS
      libvirt.memory = RAM
    end

    if provider == "virtualbox"
      comnetsemu.vm.box = BOX
      # Sync ./ to home dir of vagrant to simplify the install script
      comnetsemu.vm.synced_folder ".", "/vagrant", disabled: true
      comnetsemu.vm.synced_folder ".", "/home/vagrant/comnetsemu", type: 'virtualbox'
    elsif provider == "libvirt"
      comnetsemu.vm.box = BOX_LIBVIRT
      comnetsemu.vm.synced_folder ".", "/vagrant", disabled: true
      # Rync is used for simplicity, it's unidirectional (host -> guest).
      # It does NOT run $ vagrant rsync-auto by default.
      # More options here: https://github.com/vagrant-libvirt/vagrant-libvirt#synced-folders
      comnetsemu.vm.synced_folder ".", "/home/vagrant/comnetsemu", type: 'rsync'
    end


    comnetsemu.vm.hostname = "comnetsemu"
    comnetsemu.vm.box_check_update = true
    comnetsemu.vm.post_up_message = '
VM already started! Run "$ vagrant ssh comnetsemu" to ssh into the runnung VM.

**IMPORTANT!!!**: For all ComNetsEmu users and developers:

**Please** run the upgrade process described [here](https://git.comnets.net/public-repo/comnetsemu#upgrade-comnetsemu-and-dependencies) when there is a new release
published [here](https://git.comnets.net/public-repo/comnetsemu/-/tags).
New features, fixes and other improvements require run the upgrade script **manually**.
But the script will check and perform upgrade automatically and it does not take much time if you have a good network connection.
    '

    comnetsemu.vm.provision :shell, inline: $bootstrap, privileged: true
    comnetsemu.vm.provision :shell, inline: $install_kernel, privileged: true
    comnetsemu.vm.provision :shell, inline: $setup_x11_server, privileged: true

    if provider == "virtualbox"
      # Workaround for vbguest plugin issue
      comnetsemu.vm.provision "shell", run: "always", inline: <<-WORKAROUND
      modprobe vboxsf || true
      WORKAROUND
      # Make the maketerm of Mininet work in VirtualBox.
      comnetsemu.vm.provision :shell, privileged: true, run: "always", inline: <<-SHELL
        sed -i 's/X11UseLocalhost no/X11UseLocalhost yes/g' /etc/ssh/sshd_config
        systemctl restart sshd.service
      SHELL
    end

    if provider == "libvirt"
      # Make the maketerm of Mininet work in KVM.
      comnetsemu.vm.provision :shell, privileged: true, run: "always", inline: <<-SHELL
        sed -i 's/#X11UseLocalhost yes/X11UseLocalhost no/g' /etc/ssh/sshd_config
        systemctl restart sshd.service
      SHELL
    end

    comnetsemu.vm.provision "shell", privileged: false, inline: <<-SHELL
      # Apply Xterm profile, looks nicer.
      cp /home/vagrant/comnetsemu/util/Xresources /home/vagrant/.Xresources
      # xrdb can not run directly during vagrant up. Auto-works after reboot.
      xrdb -merge /home/vagrant/.Xresources

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
      sudo bash ./build.sh

      # Run the customization shell script (for distribution $BOX) if it exits.
      cd /home/vagrant/comnetsemu/util || exit
      if [ -f "./vm_customize.sh" ]; then
        echo "*** Run VM customization script."
        bash ./vm_customize.sh
      fi
    SHELL

    comnetsemu.vm.provision :shell, inline: $post_installation, privileged: true

    # Always run this when use `vagrant up`
    # - Check to update all dependencies
    # ISSUE: The VM need to have Internet connection to boot up...
    #comnetsemu.vm.provision :shell, privileged: true, run: "always", inline: <<-SHELL
    #  cd /home/vagrant/comnetsemu/util || exit
    #  PYTHON=python3 ./install.sh -u
    #SHELL

    # VM networking
    comnetsemu.vm.network "forwarded_port", guest: 8888, host: 8888, host_ip: "127.0.0.1"
    comnetsemu.vm.network "forwarded_port", guest: 8082, host: 8082
    comnetsemu.vm.network "forwarded_port", guest: 8083, host: 8083
    comnetsemu.vm.network "forwarded_port", guest: 8084, host: 8084
    # - Uncomment the underlying line to add a private network to the VM.
    #   If VirtualBox is used as the hypervisor, this means adding or using (if already created) a host-only interface to the VM.
    # comnetsemu.vm.network "private_network", ip: "192.168.0.2"

    # Enable X11 forwarding
    comnetsemu.ssh.forward_agent = true
    comnetsemu.ssh.forward_x11 = true
  end
end
