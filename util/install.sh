#!/usr/bin/env bash
#
# About: ComNetsEmu Installer
# Email: zuo.xiang@tu-dresden.de
#

# Fail on error
set -e

# Fail on unset var usage
set -o nounset

# Mininet's installer's default assumption.
if [[ $EUID -eq 0 ]]; then
    echo "Installer should be run as a user with sudo permissions, "
    echo "not root."
    exit 1
fi

# Set magic variables for current file & dir
# __dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# __file="${__dir}/$(basename "${BASH_SOURCE[0]}")"

####################
#  Util Functions  #
####################

msg() {
    printf '%b\n' "$1" >&2
}

warning() {
    declare _type=$1 text=$2
    msg "\033[33mWarning:\033[0m ${_type} ${text}"
}

error() {
    declare _type=$1 text=$2
    msg "\033[31m[✘]\033[0m ${_type} ${text}"
}

function no_dir_exit() {
    declare dir=$1
    if [ ! -d "$dir" ]; then
        error "[INSTALL]" "Directory: $dir does not exit! Exit."
        exit 1
    fi
}

function check_patch() {
    declare patch_path=$1
    declare prefix_num=$2

    if patch -p"$prefix_num" --dry-run <"$patch_path"; then
        patch -p"$prefix_num" <"$patch_path"
    else
        error "[PATCH]" "Failed to apply the path file: $patch_path ."
        exit 1
    fi
}

####################
#  Main Installer  #
####################

DIST=Unknown
ARCH=$(uname -m)
PYTHON=python3
PIP=pip3

if [[ "$ARCH" == "i686" ]]; then
    error "[ARCH]" "i386 is not supported."
    exit 1
fi

test -e /etc/debian_version && DIST="Debian"
grep Ubuntu /etc/lsb-release &>/dev/null && DIST="Ubuntu"
if [ "$DIST" = "Ubuntu" ] || [ "$DIST" = "Debian" ]; then
    # Truly non-interactive apt-get installation
    install='sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q install'
    remove='sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q remove'
    # pkginst='sudo dpkg -i'
    update='sudo apt-get'
    addrepo='sudo add-apt-repository'
    # Prereqs for this script
    if ! lsb_release -v &>/dev/null; then
        $install lsb-release
    fi
else
    error "[DIST]" "The installer currently ONLY supports Debian/Ubuntu"
    exit 1
fi

echo "*** ComNetsEmu Installer ***"

DEFAULT_REMOTE="origin"

# Get the directory containing comnetsemu source code folder
TOP_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
# The name of the comnetsemu source code folder
COMNETSEMU_SRC_DIR="comnetsemu"

# Directory containing external dependencies installed from source
# Dependencies are downloaded into another directory because the current directory is synced to the vagrant VM by default.
# Clone sources into this directory has privileges conflicts with host OS.
EXTERN_DEP_DIR="$TOP_DIR/comnetsemu_dependencies"
# Include the minimal dependencies (used in examples/applications and require potential updates from upstream)
DEPS_INSTALLED_FROM_SRC=(mininet ryu)
# - Installed from source, versions are tags or branch names of dependencies
# For potential fast fixes, patches and extensions, a mirrrored/synced repo of Mininet is used.
MININET_GIT_URL="https://git.comnets.net/public-repo/mininet.git"
MININET_VER="bfc42f6d028a9d5ac1bc121090ca4b3041829f86"
RYU_VER="v4.34"
BCC_VER="v0.9.0"
# ComNetsEmu's dependency python packages are listed in ./requirements.txt.

DEPS_VERSIONS=("$MININET_VER" "$RYU_VER")
DEP_INSTALL_FUNCS=(install_mininet_with_deps install_ryu)

echo " - The default git remote name: $DEFAULT_REMOTE"
echo " - The path of the ComNetsEmu source code: $TOP_DIR/$COMNETSEMU_SRC_DIR"
echo " - The directory to download all dependencies: $EXTERN_DEP_DIR"

function usage() {
    printf '\nUsage: %s [-abcdhlnouvy]\n\n' "$(basename "$0")" >&2
    echo " - Dependencies are installed with package manager (apt, pip) or from sources (git clone)."
    echo " - [] in options are used to mark the version (If the tool is installed from source, the version can be a Git commit, branch or tag.)"

    echo ""
    echo "Options:"
    echo " -a: install ComNetsEmu and (A)ll dependencies - good luck!"
    echo " -b: install (B)PF Compiler Collection (BCC) [$BCC_VER]."
    echo " -c: install (C)omNetsEmu Python module and dependency packages."
    echo " -d: install (D)ocker CE [stable]."
    echo " -h: print usage."
    echo " -k: install required Linux (K)ernel modules."
    echo " -l: install ComNetsEmu and only (L)ight-weight dependencies."
    echo " -n: install mi(N)inet with minimal dependencies from source [$MININET_VER] (Python module, OpenvSwitch, Openflow reference implementation 1.0)"
    echo " -r: (R)einstall all dependencies for ComNetsEmu."
    echo " -u: (U)pgrade ComNetsEmu's Python package and all dependencies. "
    echo " -v: install de(V)elopment tools."
    echo " -y: install R(Y)u SDN controller [$RYU_VER]."
    exit 2
}

function install_kernel_modules() {
    echo "Install wireguard kernel module"
    # It is now (07.10.2020) in the official repo.
    # sudo add-apt-repository -y ppa:wireguard/wireguard
    sudo apt-get update
    sudo apt-get install -y linux-headers-"$(uname -r)"
    sudo apt-get install -y wireguard
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

    # Enable docker experimental features
    sudo mkdir -p /etc/docker
    echo "{\"experimental\": true}" | sudo tee --append /etc/docker/daemon.json
    if pidof systemd; then
        sudo systemctl restart docker
    fi
}

function upgrade_docker() {
    $update update
    $install docker-ce
}

function upgrade_pip() {
    echo "*** Upgrade $PIP to the latest version."
    sudo -H $PIP install -U pip
}

function install_mininet_with_deps() {
    local mininet_dir="$EXTERN_DEP_DIR/mininet-$MININET_VER"
    local mininet_patch_dir="$TOP_DIR/comnetsemu/patch/mininet"

    no_dir_exit "$mininet_patch_dir"
    mkdir -p "$mininet_dir"

    echo "*** Install Mininet and its minimal dependencies."
    $install git net-tools
    cd "$mininet_dir" || exit
    git clone $MININET_GIT_URL
    cd mininet || exit
    git checkout -b $MININET_VER $MININET_VER
    cd util || exit
    if [[ $(lsb_release -rs) == "20.04" ]]; then
        echo "cgroups-bin is deprected and the new package is cgroups-tools in mininet install script."
        sed -i 's/cgroup-bin/cgroup-tools/g' ./install.sh
    else
        echo "cgroup-bin still supported in Ubuntu 18.04 and below."
    fi
    PYTHON=python3 ./install.sh -nfvw03
}

function install_comnetsemu() {
    echo "*** Install ComNetsEmu"
    $install python3 python3-pip
    echo "- Install ComNetsEmu dependency packages."
    cd "$TOP_DIR/comnetsemu/util" || exit
    sudo -H pip3 install -r ./requirements.txt
    echo "- Install ComNetsEmu Python package."
    cd "$TOP_DIR/comnetsemu" || exit
    sudo PYTHON=python3 make install
}

function upgrade_comnetsemu_deps_python_pkgs() {
    echo "- Upgrade ComNetsEmu dependency packages."
    cd "$TOP_DIR/comnetsemu/util" || exit
    sudo -H pip3 install -r ./requirements.txt
}

function install_ryu() {
    local ryu_dir="$EXTERN_DEP_DIR/ryu-$RYU_VER"
    mkdir -p "$ryu_dir"

    echo "*** Install Ryu SDN controller"
    $install git gcc "$PYTHON-dev" libffi-dev libssl-dev libxml2-dev libxslt1-dev zlib1g-dev python3-pip
    git clone git://github.com/osrg/ryu.git "$ryu_dir/ryu"
    cd "$ryu_dir/ryu" || exit
    git checkout -b $RYU_VER $RYU_VER
    upgrade_pip
    sudo -H $PIP install .
}

function install_devs() {
    echo "*** Install tools for development"
    $install shellcheck
    upgrade_pip
    echo "- Install dev python packages via PIP."
    sudo -H $PIP install pytest ipdb==0.13.2 coverage==5.1 flake8==3.7.9 flake8-bugbear==20.1.4 pylint==2.5.2 black==19.10b0 pytype==2020.6.1
    cd "$TOP_DIR/$COMNETSEMU_SRC_DIR/doc" || exit
    echo "- Install packages to build HTML documentation."
    sudo -H $PIP install -r ./requirements.txt
}

function install_bcc() {
    local bcc_dir="$EXTERN_DEP_DIR/bcc-$BCC_VER"
    mkdir -p "$bcc_dir"

    echo "*** Install BPF Compiler Collection"
    $install bison build-essential cmake flex git libedit-dev libllvm6.0 llvm-6.0-dev libclang-6.0-dev python3 zlib1g-dev libelf-dev
    $install linux-headers-"$(uname -r)" python3-setuptools
    git clone https://github.com/iovisor/bcc.git "$bcc_dir/bcc"
    cd "$bcc_dir/bcc" || exit
    git checkout -b $BCC_VER $BCC_VER
    mkdir -p build
    cd build
    cmake .. -DCMAKE_INSTALL_PREFIX=/usr -DPYTHON_CMD=python3
    make
    sudo make install
}

function upgrade_comnetsemu() {
    local dep_name
    local installed_ver
    local req_ver
    warning "[Upgrade]" "Have you checked and merged latest updates of the remote repository? ([y]/n)"
    read -r -n 1
    if [[ ! $REPLY ]] || [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "*** Upgrade ComNetsEmu dependencies, the ComNetsEmu's source repository and Python module are not upgraded."

        echo ""
        echo "- Upgrade dependencies installed with package manager."
        upgrade_docker
        install_devs
        upgrade_comnetsemu_deps_python_pkgs

        echo ""
        echo "- Upgrade dependencies installed from source"
        echo "  The upgrade script checks the version flag (format tool_name-version) in $EXTERN_DEP_DIR"
        echo "  The installer will install new versions (defined as constant variables in this script) if the version flags are not match."

        for ((i = 0; i < ${#DEPS_INSTALLED_FROM_SRC[@]}; i++)); do
            dep_name=${DEPS_INSTALLED_FROM_SRC[i]}
            echo "Step $i: Check and upgrade ${DEPS_INSTALLED_FROM_SRC[i]}"
            installed_ver=$(find "$EXTERN_DEP_DIR" -maxdepth 1 -type d -name "${dep_name}-*" | cut -d '-' -f 2-)
            req_ver=${DEPS_VERSIONS[i]}
            echo "Installed version: ${installed_ver}, requested version: ${req_ver}"
            if [[ "${installed_ver}" != "${req_ver}" ]]; then
                warning "[Upgrade]" "Upgrade ${dep_name} from ${installed_ver} to ${req_ver}"
                sudo rm -rf "$EXTERN_DEP_DIR/${dep_name}-${installed_ver}"
                ${DEP_INSTALL_FUNCS[i]}
            fi
            echo ""
        done

        echo "- Reinstall ComNetsEmu python package with develop mode."
        # Check here (https://stackoverflow.com/questions/19048732/python-setup-py-develop-vs-install)
        # for difference between install and develop
        cd "$TOP_DIR/$COMNETSEMU_SRC_DIR/" || exit
        sudo make develop

        echo "- Rebuild test containers if there are changes in their Dockerfiles."
        cd "$TOP_DIR/$COMNETSEMU_SRC_DIR/test_containers" || exit
        bash ./build.sh
        echo "- Run removing unused images. This can reduce the disk usage."
        docker image prune

    else
        error "[Upgrade]" "Please check and merge remote updates before upgrading."
    fi
}

function reinstall_comnetsemu_deps() {
    echo ""
    echo "*** Reinstall ComNetsEmu dependencies."
    sudo rm -r "$EXTERN_DEP_DIR"
    install_kernel_modules
    install_mininet_with_deps
    install_ryu
    install_docker
    install_devs
}

# TODO: Extend remove function for all installed packages
function remove_comnetsemu() {
    echo "*** Remove function currently under development"
    exit 0

    # ISSUE: pip uninstall does not uninstall all dependencies of the packages
    echo "*** Remove ComNetsEmu and its dependencies"
    warning "[REMOVE]" "Try its best to remove all packages and configuration files, not 100% clean."

    echo "Remove Docker and docker-py"
    $remove docker-ce
    sudo -H $PIP uninstall -y docker || true

    echo "Remove Mininet"
    sudo -H $PIP uninstall -y mininet || true

    echo "Remove ComNetsEmu"
    sudo -H $PIP uninstall -y comnetsemu || true

    echo "Remove Ryu SDN controller"
    sudo -H $PIP uninstall -y ryu || true

    echo "Remove OVS"
    mininet_dir="$EXTERN_DEP_DIR/mininet-$MININET_VER"
    mkdir -p "$mininet_dir"
    ./install.sh -r
    cd "$mininet_dir/mininet/util" || exit

    echo "Remove dependency folder"
    sudo rm -rf "$EXTERN_DEP_DIR"

}

function test_install() {
    echo "*** Test installation. Used by ../check_installer.sh script."
    install_mininet_with_deps
    install_ryu
    install_docker
    install_devs
    install_comnetsemu
}

function install_lightweight() {
    echo "*** Install ComNetsEmu with only light weight dependencies"
    $update update
    install_kernel_modules
    install_mininet_with_deps
    install_ryu
    install_docker
    # MUST run at the end!
    install_comnetsemu
}

function all() {
    echo "*** Install ComNetsEmu and all dependencies"
    $update update
    install_kernel_modules
    install_mininet_with_deps
    install_ryu
    install_docker
    install_devs
    # MUST run at the end!
    install_comnetsemu
}

# Check if source and dependency directory exits
if [[ ! -d "$TOP_DIR/$COMNETSEMU_SRC_DIR" ]]; then
    error "[PATH]" "The ComNetsEmu source directory does not exist."
    echo " The default path of the ComNetsEmu source code: $TOP_DIR/$COMNETSEMU_SRC_DIR"
    echo " You can change the variable COMNETSEMU_SRC_DIR in the script to use customized directory name"
    exit 1
fi

if [[ ! -d "$EXTERN_DEP_DIR" ]]; then
    warning "[PATH]" "The default dependency directory does not exist."
    echo "Create the dependency directory : $EXTERN_DEP_DIR"
    mkdir -p "$EXTERN_DEP_DIR"
fi

if [ $# -eq 0 ]; then
    usage
else
    while getopts 'abcdhklnrtuvy' OPTION; do
        case $OPTION in
        a) all ;;
        b) install_bcc ;;
        c) install_comnetsemu ;;
        d) install_docker ;;
        h) usage ;;
        k) install_kernel_modules ;;
        l) install_lightweight ;;
        n) install_mininet_with_deps ;;
        r) reinstall_comnetsemu_deps ;;
        t) test_install ;;
        u) upgrade_comnetsemu ;;
        v) install_devs ;;
        y) install_ryu ;;
        *) usage ;;
        esac
    done
    shift "$((OPTIND - 1))"
fi
