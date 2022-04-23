# -*- mode: ruby -*-
# vi: set ft=ruby :
# About: Vagrant file for the development environment

###############
#  Variables  #
###############

CPUS = 2
# - 2GB RAM SHOULD be sufficient for most examples and applications.
# - Currently only YOLOv2 object detection application requires 4GB RAM to run smoothly.
# - Reduce the memory number (in MB) here if you physical machine does not have enough physical memory.
RAM = 4096

# Bento: Packer templates for building minimal Vagrant baseboxes
# The bento/ubuntu-XX.XX is a small image of about 500 MB, fast to download
BOX = "bento/ubuntu-20.04"
VM_NAME = "ubuntu-20.04-comnetsemu"

# When using libvirt as the provider, use this box, bento boxes do not support libvirt.
BOX_LIBVIRT = "generic/ubuntu2004"

######################
#  Provision Script  #
######################

# Common bootstrap
$bootstrap= <<-SCRIPT
DEBIAN_FRONTEND=noninteractive apt-get update
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

APT_PKGS=(
  ansible
  bash-completion
  dfc
  gdb
  git
  htop
  iperf
  iperf3
  make
  pkg-config
  python3
  python3-dev
  python3-pip
  sudo
  tmux
)
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${APT_PKGS[@]}"
SCRIPT

$setup_x11_server= <<-SCRIPT
APT_PKGS=(
  openbox
  xauth
  xorg
  xterm
)
DEBIAN_FRONTEND=noninteractive apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y "${APT_PKGS[@]}"
SCRIPT

$setup_comnetsemu= <<-SCRIPT
# Apply a custom Xterm profile that looks better than the default.
cp /home/vagrant/comnetsemu/util/Xresources /home/vagrant/.Xresources
# xrdb can not run directly during vagrant up. Auto-works after reboot.
xrdb -merge /home/vagrant/.Xresources

cd /home/vagrant/comnetsemu/util || exit
bash ./install.sh -a

# Run the custom shell script, if it exists.
cd /home/vagrant/comnetsemu/util || exit
if [ -f "./vm_customize.sh" ]; then
  echo "*** Run VM customization script."
  bash ./vm_customize.sh
fi
SCRIPT

$post_installation= <<-SCRIPT
# Allow the vagrant user to use Docker without sudo.
usermod -aG docker vagrant
if [ -d /home/vagrant/.docker ]; then
  chown -R vagrant:vagrant /home/vagrant/.docker
fi
DEBIAN_FRONTEND=noninteractive apt-get autoclean -y
DEBIAN_FRONTEND=noninteractive apt-get autoremove -y
SCRIPT

$setup_libvirt_vm_always= <<-SCRIPT
# Configure the SSH server to allow X11 forwarding with sudo
# This is needed to use the Xterm feature of ComNetsEmu with libvirt/KVM
cp /home/vagrant/comnetsemu/util/sshd_config /etc/ssh/sshd_config
systemctl restart sshd.service
SCRIPT

####################
#  Vagrant Config  #
####################

Vagrant.configure("2") do |config|

  config.vm.define "comnetsemu" do |comnetsemu|
    comnetsemu.vm.box = BOX
    # Sync ./ to home directory of vagrant to simplify the install script
    comnetsemu.vm.synced_folder ".", "/vagrant", disabled: true
    comnetsemu.vm.synced_folder ".", "/home/vagrant/comnetsemu"

    # For Virtualbox provider
    comnetsemu.vm.provider "virtualbox" do |vb|
      vb.name = VM_NAME
      vb.cpus = CPUS
      vb.memory = RAM
      # MARK: The vCPUs should have SSE4 to compile DPDK applications.
      vb.customize ["setextradata", :id, "VBoxInternal/CPUM/SSE4.1", "1"]
      vb.customize ["setextradata", :id, "VBoxInternal/CPUM/SSE4.2", "1"]
    end

    # For libvirt provider
    comnetsemu.vm.provider "libvirt" do |libvirt, override|
      # Overrides are used to modify default options that do not work for libvirt provider.
      override.vm.box = BOX_LIBVIRT
      override.vm.synced_folder ".", "/home/vagrant/comnetsemu", type: "nfs", nfs_version: 4

      libvirt.driver = "kvm"
      libvirt.cpus = CPUS
      libvirt.memory = RAM
    end

    comnetsemu.vm.hostname = "comnetsemu"
    comnetsemu.vm.box_check_update = true
    comnetsemu.vm.post_up_message = '
The VM is up! Run "$ vagrant ssh comnetsemu" to ssh into the running VM.

IMPORTANT! For all ComNetsEmu users and developers:

When a new version is released (https://git.comnets.net/public-repo/comnetsemu/-/tags),
please run the upgrade process described [here](https://git.comnets.net/public-repo/comnetsemu#upgrade-comnetsemu-and-dependencies).
New features, fixes and other improvements require **manually** running the upgrade script.
But the script will automatically check and perform the upgrade, and if you have a good internet connection,
it will not take much time.
    '

    comnetsemu.vm.provision :shell, inline: $bootstrap, privileged: true
    comnetsemu.vm.provision :shell, inline: $setup_x11_server, privileged: true
    comnetsemu.vm.provision :shell, inline: $setup_comnetsemu, privileged: false
    comnetsemu.vm.provision :shell, inline: $post_installation, privileged: true

    comnetsemu.vm.provider "libvirt" do |libvirt, override|
      override.vm.provision :shell, inline: $setup_libvirt_vm_always, privileged: true, run: "always"
    end
    comnetsemu.vm.provision :shell, privileged:false, run: "always", path: "./util/echo_banner.sh"

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
