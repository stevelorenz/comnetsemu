#!/usr/bin/env bash
#
# About: ComNetsEmu Installer
# Email: zuo.xiang@tu-dresden.de
#

# Fail on error
set -e

# Fail on unset var usage
set -o nounset

msg() {
    printf '%b\n' "$1" >&2
}

warning(){
    declare _type=$1 text=$2
    msg "\033[33mWarning:\033[0m ${_type} ${text}"
}

error() {
    declare _type=$1 text=$2
    msg "\033[31m[✘]\033[0m ${_type} ${text}"
}

DIST=Unknown
ARCH=$(uname -m)
PYTHON=python3
PIP=pip3

if [[ "$ARCH" = "i686" ]]; then
    error "[ARCH]" "i386 is not supported."
fi

test -e /etc/debian_version && DIST="Debian"
grep Ubuntu /etc/lsb-release &> /dev/null && DIST="Ubuntu"
if [ "$DIST" = "Ubuntu" ] || [ "$DIST" = "Debian" ]; then
    # Truly non-interactive apt-get installation
    install='sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q install'
    remove='sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q remove'
    pkginst='sudo dpkg -i'
    update='sudo apt-get'
    addrepo='sudo add-apt-repository'
    # Prereqs for this script
    if ! lsb_release -v &> /dev/null; then
        $install lsb-release
    fi
else
    error "[DIST]" "The installer currently ONLY supports Debian/Ubuntu"
fi


echo "*** ComNetsEmu Installer ***"

DEFAULT_REMOTE="origin"

# Get the directory containing comnetsemu source code folder
COMNETSEMU_DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd -P )"
# The name of the comnetsemu source code folder
COMNETSEMU_SRC_DIR="comnetsemu"

# Directory containing dependencies installed from source
DEP_DIR="$HOME/comnetsemu_dependencies"
# Include the minimal dependencies (used in examples/applications and require potential updates from upstream)
DEPS_INSTALLED_FROM_SRC=(mininet ryu ovx)
# Tags/branch names of dependencies
COMNETSEMU_VER="master"
MININET_VER="de28f67"
RYU_VER="v4.32"
BCC_VER="v0.9.0"
OVX_VER="0.0-MAINT"
DOCKER_PY_VER="3.7.2"
DEPS_VERSIONS=("$MININET_VER" "$RYU_VER" "$OVX_VER")
DEP_INSTALL_FUNCS=(install_mininet install_ryu install_ovx)

echo " - The default git remote name: $DEFAULT_REMOTE"
echo " - The path of the ComNetsEmu source code: $COMNETSEMU_DIR/$COMNETSEMU_SRC_DIR"
echo " - The path to install all dependencies: $DEP_DIR"


function usage() {
    printf '\nUsage: %s [-abcdhlnoruvy]\n\n' "$(basename "$0")" >&2
    echo " - Dependencies are installed with package manager (apt, pip) or from sources (git clone)."
    echo " - [] in options are used to mark the version (git tags or branch)"

    echo ""
    echo "Options:"
    echo " -a: install ComNetsEmu and (A)ll dependencies - good luck!"
    echo " -b: install (B)PF Compiler Collection (BCC) [$BCC_VER]"
    echo " -c: install (C)omNetsEmu [master] python module. Docker-Py and Mininet MUST be ALREADY installed."
    echo " -d: install (D)ocker CE [stable] and Docker-Py [$DOCKER_PY_VER]"
    echo " -h: print usage"
    echo " -l: install ComNetsEmu and only (L)ight-weight dependencies."
    echo " -n: install minimal mi(N)inet from source [$MININET_VER] (Python module, OpenvSwitch, Openflow reference implementation 1.0)"
    echo " -o: install (O)penVirtex [$OVX_VER] from source. (OpenJDK7 is installed from deb packages as dependency)"
    echo " -r: try to (R)emove installed dependencies - good luck!"
    echo " -u: (U)pdate ComNetsEmu [master]"
    echo " -v: install de(V)elopment tools"
    echo " -y: install R(Y)u SDN controller [$RYU_VER]"
    exit 2
}

function install_docker() {
    $remove docker docker.io
    $install apt-transport-https ca-certificates curl software-properties-common python3-pip gnupg2

    if [ "$DIST" = "Ubuntu" ] || [ "$DIST" = "Debian" ]; then
        curl -fsSL https://download.docker.com/linux/"${DIST,,}"/gpg | sudo apt-key add -
        if [[ $(sudo apt-key fingerprint 9DC858229FC7DD38854AE2D88D81803C0EBFCD88) ]]; then
            echo "The fingerprint is correct"
        else
            echo "The fingerprint is wrong!"
            exit 1
        fi
        $addrepo \
            "deb [arch=amd64] https://download.docker.com/linux/${DIST,,}\
            $(lsb_release -cs) \
            stable"

    fi

    $update update
    $install docker-ce
    sudo -H $PIP install docker=="$DOCKER_PY_VER"

}

function install_mininet() {
    local mininet_dir="$DEP_DIR/mininet-$MININET_VER"
    mkdir -p "$mininet_dir"

    echo "*** Install Mininet"
    $install git
    cd "$mininet_dir" || exit
    git clone https://github.com/mininet/mininet.git
    cd mininet || exit
    git checkout -b dev $MININET_VER
    cd util || exit
    PYTHON=python3 ./install.sh -nfv
}

function install_comnetsemu() {
    echo "*** Install ComNetsEmu"
    warning "[INSTALL]" "The docker-py and Mininet MUST be already installed."
    $install python3
    cd "$COMNETSEMU_DIR/comnetsemu" || exit
    sudo PYTHON=python3 make install
}


function install_ryu() {
    local ryu_dir="$DEP_DIR/ryu-$RYU_VER"
    mkdir -p "$ryu_dir"

    echo "*** Install Ryu SDN controller"
    $install git gcc "$PYTHON-dev" libffi-dev libssl-dev libxml2-dev libxslt1-dev zlib1g-dev python3-pip
    git clone git://github.com/osrg/ryu.git "$ryu_dir/ryu"
    cd "$ryu_dir/ryu" || exit
    git checkout -b dev $RYU_VER
    sudo -H $PIP install .
}

function install_devs() {
    echo "*** Install tools for development"
    echo "- Install pytest for unit tests"
    $install gcc "$PYTHON-dev" libffi-dev libssl-dev libxml2-dev libxslt1-dev zlib1g-dev python3-pip
    sudo -H $PIP install pytest ipdb
}

function install_bcc() {
    local bcc_dir="$DEP_DIR/bcc-$BCC_VER"
    mkdir -p "$bcc_dir"

    echo "*** Install BPF Compiler Collection"
    $install bison build-essential cmake flex git libedit-dev libllvm6.0 llvm-6.0-dev libclang-6.0-dev python3 zlib1g-dev libelf-dev
    $install linux-headers-"$(uname -r)" python3-setuptools
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
    $install maven wget git
    cd "$ovx_dir" || exit
    echo "Install OpenJDK7 from deb packages"
    # MARK: Use the FTP server in Germany, students can change URL based on their location
    wget http://ftp.de.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jdk_7u161-2.6.12-1_amd64.deb
    wget http://ftp.de.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jre_7u161-2.6.12-1_amd64.deb
    wget http://ftp.de.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jre-headless_7u161-2.6.12-1_amd64.deb
    wget http://ftp.de.debian.org/debian/pool/main/libj/libjpeg-turbo/libjpeg62-turbo_1.5.2-2+b1_amd64.deb
    # ISSUE: Failed to exit due to dependency problems. Issues are fixed with
    # apt install -f. So force the error status to zero.
    $pkginst ./*.deb || true
    # Resolve potential dependency issues
    $install -f -y
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
    local dep_name
    local installed_ver
    local req_ver

    echo ""
    echo "*** Update ComNetsEmu"


    echo "[1] Update ComNetsEmu's Python module, examples and applications"
    cd "$COMNETSEMU_DIR/comnetsemu" || exit
    git pull "$DEFAULT_REMOTE" "$COMNETSEMU_VER"
    sudo PYTHON=python3 make install

    echo "[2] Update dependencies installed with package manager."
    install_docker

    echo "[3] Update dependencies installed from source"
    echo "  The update script checks the version flag (format tool_name-version) in $DEP_DIR"
    echo "  The installer will install new versions (defined as constant variables in this script) if the version flags are not match."

    for (( i = 0; i < ${#DEPS_INSTALLED_FROM_SRC[@]}; i++ )); do
        dep_name=${DEPS_INSTALLED_FROM_SRC[i]}
        echo "Step$i: Check and update ${DEPS_INSTALLED_FROM_SRC[i]}"
        # TODO: Replace ls | grep with glob or for loop
        installed_ver=$(ls "$DEP_DIR/" | grep "$dep_name-" | cut -d '-' -f 2-)
        req_ver=${DEPS_VERSIONS[i]}
        echo "Installed version: $installed_ver, requested version: ${req_ver}"
        if [[ "$installed_ver" != "$req_ver" ]]; then
            warning "[Update]" "Update $dep_name from $installed_ver to $req_ver"
            sudo rm -rf "$DEP_DIR/$dep_name-$installed_ver"
            ${DEP_INSTALL_FUNCS[i]}
        fi
        echo ""
    done
}

# TODO: Extend remove function for all installed packages
function remove_comnetsemu() {
    # ISSUE: pip uninstall does not uninstall all dependencies of the packages
    echo "*** Remove ComNetsEmu and its dependencies"
    warning "[REMOVE]" "Try its best to remove all packages and configuration files, not 100% clean."

    echo "Remove Docker and docker-py"
    $remove docker-ce
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

function install_lightweight() {
    echo "*** Install ComNetsEmu with only light weight dependencies"
    echo "To be installed dependencies: mininet ryu docker docker-py"
    $update update
    install_mininet
    install_ryu
    install_docker
    # MUST run at the end!
    install_comnetsemu
}

function all() {
    echo "*** Install ComNetsEmu and all dependencies"
    $update update
    install_mininet
    install_ryu
    install_docker
    install_ovx
    install_devs
    # MUST run at the end!
    install_comnetsemu
}

# Check if source and dependency directory exits
if [[ ! -d "$COMNETSEMU_DIR/$COMNETSEMU_SRC_DIR" ]]; then
    error "[PATH]" "The ComNetsEmu source directory does not exist."
    echo " The default path of the ComNetsEmu source code: $COMNETSEMU_DIR/$COMNETSEMU_SRC_DIR"
    echo " You can change the variable COMNETSEMU_SRC_DIR in the script to use customized directory name"
    exit 1
fi

if [[ ! -d "$DEP_DIR" ]]; then
    warning "[PATH]" "The default dependency directory does not exist."
    echo "Create the dependency directory : $DEP_DIR"
    mkdir -p "$DEP_DIR"
fi

if [ $# -eq 0 ]
then
    usage
else
    while getopts 'abcdhlnoruvy' OPTION
    do
        case $OPTION in
            a) all;;
            b) install_bcc;;
            c) install_comnetsemu;;
            d) install_docker;;
            h) usage;;
            l) install_lightweight;;
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
