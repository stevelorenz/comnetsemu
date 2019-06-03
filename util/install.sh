#! /bin/bash
#
# About: Install ComNetsEmu
#

# Fail on error
set -e

# Fail on unset var usage
set -o nounset

PYTHON=python3
PIP=pip3

echo "ComNetsEmu Installer"

COMNETSEMU_DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd -P )"
DEP_DIR="$HOME/comnetsemu_dependencies"

MININET_VER="e20380"
RYU_VER="v4.32"
BCC_VER="v0.9.0"
OVX_VER="0.0-MAINT"

function usage() {
    printf '\nUsage: %s [-abcdhnoruvy]\n\n' "$(basename "$0")" >&2
    echo 'options:'
    echo " -a: install (A)ll packages - good luck!"
    echo " -b: install (B)PF Compiler Collection (BCC) [$BCC_VER]"
    echo " -c: install (C)omNetsEmu [master] python module"
    echo " -d: install (D)ocker CE"
    echo " -h: print usage"
    echo " -n: install minimal mi(N)inet from source [$MININET_VER] (Python module, OpenvSwitch, Openflow reference implementation 1.0)"
    echo " -o: install (O)penVirtex [$OVX_VER] from source. (OpenJDK7 is installed from deb packages as dependency)"
    echo " -r: try to (R)emove installed packages - good luck!"
    echo " -u: (U)pdate ComNetsEmu [master]"
    echo " -v: install de(V)elopment tools"
    echo " -y: install R(Y)u SDN controller [$RYU_VER]"
    exit 2
}

function install_docker() {
    sudo apt-get remove -y docker docker-engine docker.io
    sudo apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        software-properties-common

    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    if [[ $(sudo apt-key fingerprint 9DC858229FC7DD38854AE2D88D81803C0EBFCD88) ]]; then
        echo "The fingerprint is correct"
    else
        echo "The fingerprint is wrong!"
        exit 1
    fi

    sudo add-apt-repository \
        "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) \
        stable"

    sudo apt-get update
    sudo apt-get install -y docker-ce
    sudo -H $PIP install docker==3.7.2

}

function install_mininet() {
    local mininet_dir="$DEP_DIR/mininet-$MININET_VER"
    mkdir -p "$mininet_dir"

    echo "*** Install Mininet"
    cd "$mininet_dir" || exit
    git clone https://github.com/mininet/mininet.git
    cd mininet || exit
    git checkout -b dev $MININET_VER
    cd util || exit
    PYTHON=python3 ./install.sh -nfv
}

function install_comnetsemu() {
    echo "*** Install ComNetsEmu"
    cd "$COMNETSEMU_DIR/comnetsemu" || exit
    sudo PYTHON=python3 make install
}


function install_ryu() {
    local ryu_dir="$DEP_DIR/ryu-$RYU_VER"
    mkdir -p "$ryu_dir"

    echo "*** Install Ryu SDN controller"
    sudo apt update
    sudo apt install -y gcc "$PYTHON-dev" libffi-dev libssl-dev libxml2-dev libxslt1-dev zlib1g-dev
    git clone git://github.com/osrg/ryu.git "$ryu_dir/ryu"
    cd "$ryu_dir/ryu" || exit
    git checkout -b dev $RYU_VER
    sudo -H $PIP install .
}

function install_devs() {
    echo "*** Install tools for development"
    echo "- Install pytest for unit tests"
    sudo -H $PIP install pytest
}

function install_bcc() {
    local bcc_dir="$DEP_DIR/bcc-$BCC_VER"
    mkdir -p "$bcc_dir"

    echo "*** Install BPF Compiler Collection"
    sudo apt-get -y install bison build-essential cmake flex git libedit-dev libllvm6.0 llvm-6.0-dev libclang-6.0-dev python3 zlib1g-dev libelf-dev
    sudo apt-get -y install linux-headers-"$(uname -r)"
    git clone https://github.com/iovisor/bcc.git "$bcc_dir/bcc"
    cd "$bcc_dir/bcc" || exit
    git checkout -b dev $BCC_VER
    mkdir -p build; cd build
    cmake .. -DCMAKE_INSTALL_PREFIX=/usr -DPYTHON_CMD=python3
    make
    sudo make install
}

function install_ovx() {
    local ovx_dir="$DEP_DIR/ovx-$OVX_VER"
    mkdir -p "$ovx_dir"

    echo "*** Install OpenVirtex"
    echo "Install Apache Maven"
    sudo apt update
    sudo apt install -y maven
    cd "$ovx_dir" || exit
    echo "Install OpenJDK7 from deb packages"
    # MARK: Use the FTP server in Germany, students can change URL based on their location
    wget http://ftp.de.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jdk_7u161-2.6.12-1_amd64.deb
    wget http://ftp.de.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jre_7u161-2.6.12-1_amd64.deb
    wget http://ftp.de.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jre-headless_7u161-2.6.12-1_amd64.deb
    wget http://ftp.de.debian.org/debian/pool/main/libj/libjpeg-turbo/libjpeg62-turbo_1.5.2-2+b1_amd64.deb
    sudo dpkg -i ./*.deb
    # Resolve potential dependency issues
    sudo apt install -f
    # Update java alternatives
    # - IcedTeaPlugin.so plugin is unavailable
    sudo update-java-alternatives -s java-1.7.0-openjdk-amd64
    echo "Clone OpenVirteX source code"
    git clone https://github.com/os-libera/OpenVirteX
    cd OpenVirteX || exit
    git checkout -b "$OVX_VER"
    echo "*** OpenVirtex's dependencies installed finished."
    echo "*** Please run: 'sh $ovx_dir/OpenVirteX/scripts/ovx.sh' to start OpenVirtex"
}

function update_comnetsemu() {
    echo "*** Update ComNetsEmu"
    echo "- Update Python module, examples and applications"
    cd "$COMNETSEMU_DIR/comnetsemu" || exit
    git pull origin master
    sudo PYTHON=python3 make install
}

# TODO: Extend remove function for all installed packages
function remove_comnetsemu() {
    # ISSUE: pip uninstall does not uninstall all dependencies of the packages
    echo "*** Remove ComNetsEmu and its dependencies"

    echo "Remove Docker and docker-py"
    sudo apt purge -y docker-ce
    sudo -H $PIP uninstall -y docker  || true

    echo "Remove Mininet"
    sudo -H $PIP uninstall -y mininet || true

    echo "Remove ComNetsEmu"
    sudo -H $PIP uninstall -y comnetsemu || true

    echo "Remove Ryu SDN controller"
    sudo -H $PIP uninstall -y ryu || true

    echo "Remove OVS"
    mininet_dir="$DEP_DIR/mininet-$MININET_VER"
    mkdir -p "$mininet_dir"
    cd "$mininet_dir/mininet/util" || exit
    ./install.sh -r

    # TODO: Remove BCC properly

    echo "Remove dependency folder"
    sudo rm -rf "$DEP_DIR"

}

function all() {
    echo "*** Install all dependencies"
    install_mininet
    install_ryu
    install_docker
    install_devs
    # Should run at the end!
    install_comnetsemu
}

if [ $# -eq 0 ]
then
    usage
else
    while getopts 'abcdhnoruvy' OPTION
    do
        case $OPTION in
            a) all;;
            b) install_bcc;;
            c) install_comnetsemu;;
            d) install_docker;;
            h) usage;;
            n) install_mininet;;
            o) install_ovx;;
            u) update_comnetsemu;;
            v) install_devs;;
            y) install_ryu;;
            r) remove_comnetsemu;;
            *) usage;;
        esac
    done
    shift $(($OPTIND - 1))
fi
