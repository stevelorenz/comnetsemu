#!/usr/bin/env bash
#
# About: All-in-one ComNetsEmu Installer
#        This is ONLY a basic all-in-one script installer for single vagrant VM setup.
#        It ONLY supports the latest Ubuntu LTS version (20.04).
#        Supporting multiple GNU/Linux distributions and versions is OUT OF SCOPE.
#
# TODO: Replace this imperative shell script to a declarative approach, e.g. Ansible
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
INSTALL="sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q install"
# REMOVE="sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q remove"
UPDATE="sudo apt-get update --fix-missing"

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

# Only use Python3
PYTHON=python3
PIP=pip3

# Check if required tools are already available in PATH.
NEEDED_CMDS=(
    "$PIP"
    "$PYTHON"
    git
    sed
    sudo
)
MISSING_CMDS=()

for cmd in "${NEEDED_CMDS[@]}"; do
    if ! command -v "$cmd" >/dev/null; then
        MISSING_CMDS+=("$cmd")
    fi
done

if [[ ${#MISSING_CMDS[@]} -gt 0 ]]; then
    error "[CMDS]" "Missing commands (${MISSING_CMDS[*]}) to run this script. Please install them with your package manager."
    exit 1
fi

####################
#  Main Installer  #
####################

# Get the directory containing comnetsemu source code folder
TOP_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
# The name of the comnetsemu source code folder
COMNETSEMU_SRC_DIR="comnetsemu"

# Directory containing external dependencies installed from source
# Dependencies are downloaded into another directory because the current directory is synced to the vagrant VM by default.
# Clone sources into this directory has privileges conflicts with host OS.
EXTERN_DEP_DIR="$TOP_DIR/comnetsemu_dependencies"
# Include the minimal dependencies (used in examples/applications and require potential updates from upstream)
DEPS_INSTALLED_FROM_SRC=(mininet)
# - Installed from source, versions are tags or branch names of dependencies
# For potential fast fixes, patches and extensions, a mirrrored/synced repo of Mininet is used.
MININET_GIT_URL="https://github.com/mininet/mininet.git"
# Note: The git URL issues are fixed with this commit (2.3.1b1 (#1124)), but it is not official released.
# So use this commit now can fix the install the issue, should use a release later.
MININET_VER="aa0176f"
DEPS_VERSIONS=("$MININET_VER")
DEP_INSTALL_FUNCS=(install_mininet_with_deps)

echo "*** ComNetsEmu Installer ***"

echo " - The path of the ComNetsEmu source code: $TOP_DIR/$COMNETSEMU_SRC_DIR"
echo " - The directory to download all dependencies that are installed from source: $EXTERN_DEP_DIR"

function usage() {
    printf '\nUsage: %s [-abcdhlnouvy]\n\n' "$(basename "$0")" >&2
    echo "Mark: Just use option -a if you want a out-of-box all-in-one environment."
    # Less options, less problems...
    echo "Options:"
    echo " -a: install ComNetsEmu and (A)ll its dependencies - good luck with your network connection !"
    echo " -h: print usage/(H)elp."
    echo " -n: only install Mi(N)inet with its minimal dependencies from source [$MININET_VER] (Python module, OpenvSwitch, Openflow reference implementation 1.0, Wireshark)"
    echo " -u: (U)pgrade ComNetsEmu and all its dependencies. "
    echo " -d: install dev tools for ComNetsEmu de(V)elopment (they are NOT installed with -a option)."
    exit 2
}

# Check if source and dependency directory exits
function check_comnetsemu_dirs() {
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

}

# ISSUE (Zuo): Mininet currently requires full root privilege...
# install.sh -n calls sudo inside and install Mininet in system Python path.
function install_mininet_with_deps() {
    check_comnetsemu_dirs

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

COMNETSEMU_APT_PKGS=(
    "$PYTHON-docker"
    "$PYTHON-pip"
    "$PYTHON-pyroute2"
    "$PYTHON-requests"
    "$PYTHON-ryu"
    docker.io
    linux-headers-"$(uname -r)"
    rt-tests
    stress-ng
    wireguard
)

# ISSUE (Zuo): Mininet currently requires full root privilege...
# Mininet is installed in the system Python path.
# ComNetsEmu is based on Mininet, so its dependencies and itself have to be installed into the system
# Python path as well. pip install --user can be used when Mininet does not require root privilege.
function install_comnetsemu() {
    check_comnetsemu_dirs

    echo "*** Install ComNetsEmu"
    echo "- Install all apt packages that ComNetsEmu depends on."
    $INSTALL "${COMNETSEMU_APT_PKGS[@]}"
    echo "- Install the ComNetsEmu Python package itself."
    cd "$TOP_DIR/comnetsemu" || exit 1
    sudo $PIP install .
    echo "- Build all test containers (required for unit tests and built-in examples)"
    cd "$TOP_DIR/$COMNETSEMU_SRC_DIR/test_containers" || exit
    sudo $PYTHON ./build.py
}

COMNETSEMU_DEV_APT_PKGS=(
    "$PYTHON-coverage"
    "$PYTHON-flake8"
    "$PYTHON-ipdb"
    "$PYTHON-pytest"
    black
    pylint
    shellcheck
)

function install_dev_tools() {
    echo "- Install all dev python packages."
    $INSTALL "${COMNETSEMU_DEV_APT_PKGS[@]}"

    echo "- Install (with pip) Python packages to build HTML documentation."
    cd "$TOP_DIR/$COMNETSEMU_SRC_DIR/doc" || exit
    # Pip must be used since many required packages are not in Ubuntu's repo.
    sudo $PIP install -r ./requirements.txt
}

function upgrade_comnetsemu() {
    check_comnetsemu_dirs

    local dep_name
    local installed_ver
    local req_ver
    warning "[Upgrade]" "Have you checked and merged latest updates of the remote repository? ([y]/n)"
    read -r -n 1
    if [[ ! $REPLY ]] || [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "*** Upgrade ComNetsEmu and all its dependencies"
        $UPDATE

        echo "- Upgrade special dependencies installed from source code"
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

        echo "- Upgrade ComNetsEmu itself and dependencies installed with package manager"
        install_comnetsemu
    else
        error "[Upgrade]" "Please check and merge remote updates before upgrading."
    fi
}

function all() {
    echo "*** Install ComNetsEmu and all dependencies"
    $UPDATE
    install_mininet_with_deps
    # Must install comnetsemu after installing all source dependencies !
    install_comnetsemu

    # Start and enable required daemons
    sudo systemctl start docker
    sudo systemctl enable docker
}

if [ $# -eq 0 ]; then
    usage
else
    while getopts 'adhnu' OPTION; do
        case $OPTION in
        a) all ;;
        d) install_dev_tools ;;
        h) usage ;;
        n) install_mininet_with_deps ;;
        u) upgrade_comnetsemu ;;
        *) usage ;;
        esac
    done
    shift "$((OPTIND - 1))"
fi
