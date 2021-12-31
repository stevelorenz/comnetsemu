#!/usr/bin/env bash
#
# About: All-in-one ComNetsEmu Installer
#        This is ONLY a basic all-in-one script installer for single vagrant VM setup.
#        It ONLY supports the latest Ubuntu LTS version ().
#        Supporting multiple GNU/Linux distributions and versions is OUT OF SCOPE.
#

# Fail on error
set -e

# Fail on unset var usage
set -o nounset

# Avoid conflicts with custom grep options
unset GREP_OPTIONS

# Use en_US locale
unset LANG
unset LANGUAGE
LC_ALL=en_US.utf8
export LC_ALL

######################
#  Helper Functions  #
######################

function print_stderr() {
    printf '%b\n' "$1" >&2
}

function warning() {
    declare _type=$1 text=$2
    print_stderr "\033[33mWarning:\033[0m ${_type} ${text}"
}

function error() {
    declare _type=$1 text=$2
    print_stderr "\033[31m[✘]\033[0m ${_type} ${text}"
}

function no_dir_exit() {
    declare dir=$1
    if [ ! -d "$dir" ]; then
        error "[INSTALL]" "Directory: $dir does not exit! Exit."
        exit 1
    fi
}

# TODO (Zuo): Patch Mininet source directly instead of using Python runtime
# monkey-patching, when there's a new Mininet release.
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
#  Sanity Checks   #
####################

# Mininet's installer's default assumption.
if [[ $EUID -eq 0 ]]; then
	error "[USER]" "Do not run this script through sudo or as root user."
    echo "This installer script should be run as a regular user with sudo permissions, "
    echo "not root (Avoid running all commands in the script with root privilege) !"
	echo "The script will call sudo when needed."
    echo "Please use bash ./install.sh instead of sudo bash ./install.sh"
    exit 1
fi

ARCH=$(uname -m)
if [[ "$ARCH" == "i686" ]]; then
    error "[ARCH]" "i386 is not supported. Please use X86_64."
    exit 1
fi

# Check if the latest Ubuntu LTS is used.
UBUNTU_RELEASE="20.04"
# Truly non-interactive apt-get installation
INSTALL='sudo DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends -q install'
REMOVE='sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q remove'
UPDATE='sudo apt-get update'

DIST=Unknown
grep Ubuntu /etc/lsb-release &>/dev/null && DIST="Ubuntu"
if [ "$DIST" = "Ubuntu" ]; then
    if ! lsb_release -v &>/dev/null; then
        $INSTALL lsb-release
    fi
    if [[ $(lsb_release -rs) != "$UBUNTU_RELEASE" ]]; then
		error "[DIST]" "This installer ONLY supports Ubuntu $UBUNTU_RELEASE LTS."

		echo "If you have already created the VM with the older LTS version (e.g. 18.04), please just re-create the VM to upgrade the base OS and packages."
		echo "If vagrant is used. You can simply destroy the VM and re-up the ComNetsEmu VM after you pulling the latest Vagrantfile."
		echo "You can re-build all container images when the new VM is created."
		exit 1
	fi
else
    error "[DIST]" "This installer ONLY supports Ubuntu $UBUNTU_RELEASE LTS."
    exit 1
fi

####################
#  Main Installer  #
####################

# Use Python3 packages by default
PYTHON=python3
PIP=pip3

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
MININET_GIT_URL="https://github.com/mininet/mininet.git"
MININET_VER="2.3.0"
RYU_VER="v4.34"
# ComNetsEmu's dependency python packages are listed in ./requirements.txt.

DEPS_VERSIONS=("$MININET_VER" "$RYU_VER")
DEP_INSTALL_FUNCS=(install_mininet_with_deps install_ryu)

echo "*** ComNetsEmu Installer ***"

echo " - The default git remote name: $DEFAULT_REMOTE"
echo " - The path of the ComNetsEmu source code: $TOP_DIR/$COMNETSEMU_SRC_DIR"
echo " - The directory to download all dependencies: $EXTERN_DEP_DIR"

function usage() {
    printf '\nUsage: %s [-abcdhlnouvy]\n\n' "$(basename "$0")" >&2
    echo " - Dependencies are installed with package manager (apt, pip) or from sources (git clone)."
    echo " - [VERSION] in options are used to mark/print the version (If the tool is installed from source, the version can be a Git commit, branch or tag.)"

    echo ""
    echo "Options:"
    echo " -a: install ComNetsEmu and (A)ll dependencies - good luck!"
    echo " -c: install (C)omNetsEmu Python module and all its Python dependency packages."
    echo " -d: install (D)ocker CE [stable]."
	echo " -h: print usage/(H)elp."
    echo " -k: install required Linux (K)ernel modules."
    echo " -n: install mi(N)inet with minimal dependencies from source [$MININET_VER] (Python module, OpenvSwitch, Openflow reference implementation 1.0, Wireshark)"
    echo " -u: (U)pgrade ComNetsEmu's Python package and all dependencies. "
    echo " -v: install de(V)elopment tools."
    echo " -y: install R(Y)u SDN controller [$RYU_VER]."
    exit 2
}

function install_kernel_modules() {
    echo "Install wireguard kernel module"
	local wg_apt_pkgs=(
		linux-headers-"$(uname -r)"
		wireguard
	)
	$UPDATE
	$INSTALL "${wg_apt_pkgs[@]}"
}

function install_docker() {
    $UPDATE
	# Avoid conflicts and old versions. Maybe wrong here.
    $REMOVE docker.io containerd runc
    $INSTALL docker.io
    sudo systemctl start docker
    sudo systemctl enable docker
}

function upgrade_docker() {
    $UPDATE
    $INSTALL docker.io
}

function upgrade_pip() {
    echo "*** Upgrade $PIP itself to the latest version."
    sudo $PIP install -U pip
}

# ISSUE (Zuo): Mininet currently requires full root privilege...
# install.sh -n calls sudo inside and install Mininet in system Python path.
function install_mininet_with_deps() {
    local mininet_dir="$EXTERN_DEP_DIR/mininet-$MININET_VER"
    local mininet_patch_dir="$TOP_DIR/comnetsemu/patch/mininet"

    no_dir_exit "$mininet_patch_dir"
    mkdir -p "$mininet_dir"

    echo "*** Install Mininet and its minimal dependencies."
    $INSTALL git net-tools
    cd "$mininet_dir" || exit
    git clone $MININET_GIT_URL
    cd mininet || exit
    git checkout -b $MININET_VER $MININET_VER
    cd util || exit
	# MARK: Use cgroup-tools to replace the deprecated cgroup-bin
	sed -i 's/cgroup-bin/cgroup-tools/g' ./install.sh
    PYTHON=python3 ./install.sh -nfvw
}

# ISSUE (Zuo): Mininet currently requires full root privilege...
# Mininet is installed in the system Python path.
# ComNetsEmu is based on Mininet, so its dependencies and itself have to be installed into the system
# Python path as well. pip install --user can be used when Mininet does not require root privilege.
function install_comnetsemu() {
    echo "*** Install ComNetsEmu"
    $INSTALL python3 python3-pip
    echo "- Install Python packages that ComNetsEmu depends on."
    cd "$TOP_DIR/comnetsemu/util" || exit
    sudo $PIP install -r ./requirements.txt
    echo "- Install the ComNetsEmu Python package."
    cd "$TOP_DIR/comnetsemu" || exit
    sudo PYTHON=python3 make install
}

function upgrade_comnetsemu_deps_python_pkgs() {
    echo "- Upgrade Python packages that ComNetsEmu depends on."
    cd "$TOP_DIR/comnetsemu/util" || exit
    sudo $PIP install -r ./requirements.txt
}

function install_ryu() {
    local ryu_dir="$EXTERN_DEP_DIR/ryu-$RYU_VER"
    mkdir -p "$ryu_dir"

    echo "*** Install Ryu SDN controller"
    $INSTALL git gcc "$PYTHON-dev" libffi-dev libssl-dev libxml2-dev libxslt1-dev zlib1g-dev python3-pip
    git clone git://github.com/osrg/ryu.git "$ryu_dir/ryu"
    cd "$ryu_dir/ryu" || exit
    git checkout -b $RYU_VER $RYU_VER
    upgrade_pip
    sudo $PIP install .
}

function install_devs() {
    echo "*** Install tools for development"
    $INSTALL shellcheck
    upgrade_pip
    echo "- Install dev python packages via PIP."
	local pip_pkgs=(
		black
		coverage
		flake8
		flake8-bugbear
		ipdb
		pylint
		pytest
	)
    $PIP install --user "${pip_pkgs[@]}"
    cd "$TOP_DIR/$COMNETSEMU_SRC_DIR/doc" || exit
    echo "- Install packages to build HTML documentation."
    $PIP install --user -r ./requirements.txt
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
		echo "- Upgrade dependencies installed with package managers (apt, pip)."
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

function remove_all() {
    echo "*** Remove function currently under development"
    exit 0

    # ISSUE: pip uninstall does not uninstall all dependencies of the packages
    echo "*** Remove ComNetsEmu and all dependencies"
    warning "[REMOVE]" "Try to remove all packages and configuration files, but this method is not 100% clean."

    echo "- Remove Docker and docker-py"
    $REMOVE docker.io
    $PIP uninstall -y docker || true

    echo "- Remove Mininet"
    $PIP uninstall -y mininet || true

    echo "- Remove ComNetsEmu"
    $PIP uninstall -y comnetsemu || true

    echo "Remove Ryu SDN controller"
    $PIP uninstall -y ryu || true

    echo "Remove OVS"
    mininet_dir="$EXTERN_DEP_DIR/mininet-$MININET_VER"
    cd "$mininet_dir/mininet/util" || exit
    ./install.sh -r

    echo "Remove dependency folder"
    sudo rm -rf "$EXTERN_DEP_DIR"
}

function all() {
    echo "*** Install ComNetsEmu and all dependencies"
    $UPDATE
    install_kernel_modules
    install_mininet_with_deps
    install_ryu
    install_docker

	# Must install comnetsemu after installing all dependencies !
    install_comnetsemu

    install_devs
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
        c) install_comnetsemu ;;
        d) install_docker ;;
        h) usage ;;
        k) install_kernel_modules ;;
        n) install_mininet_with_deps ;;
        u) upgrade_comnetsemu ;;
        v) install_devs ;;
        y) install_ryu ;;
        *) usage ;;
        esac
    done
    shift "$((OPTIND - 1))"
fi
