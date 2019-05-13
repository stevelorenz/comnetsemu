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

function usage() {
    printf '\nUsage: %s [-andy]\n\n' "$(basename "$0")" >&2
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
    echo "*** Install Mininet"
    mininet_dir="$DEP_DIR/mininet-$MININET_VER"
    mkdir -p "$mininet_dir"
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
    echo "*** Install Ryu SDN controller"
    sudo apt update
    sudo apt install -y gcc "$PYTHON-dev" libffi-dev libssl-dev libxml2-dev libxslt1-dev zlib1g-dev
    ryu_dir="$DEP_DIR/ryu-$RYU_VER"
    mkdir -p "$ryu_dir"
    git clone git://github.com/osrg/ryu.git "$ryu_dir/ryu"
    cd "$ryu_dir/ryu" || exit
    sudo -H $PIP install .
}

function install_devs() {
    echo "*** Install tools for development"
    echo "- Install pytest for unit tests"
    sudo -H $PIP install pytest
}

function remove() {
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
    all
else
    while getopts 'acdhnrvy' OPTION
    do
        case $OPTION in
            a) all;;
            c) install_comnetsemu;;
            d) install_docker;;
            h) usage;;
            n) install_mininet;;
            v) install_devs;;
            y) install_ryu;;
            r) remove;;
            *) usage;;
        esac
    done
    shift $(($OPTIND - 1))
fi
