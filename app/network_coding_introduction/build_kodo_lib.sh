#! /bin/bash
#
# About: Build kodo python library
#

CUR_DIR=$PWD
KODO_DIR="$HOME/kodo-python"

sudo apt-get update
sudo apt-get install -y python3 build-essential libpython3-dev python3-dev git

git clone https://github.com/steinwurf/kodo-python.git "$KODO_DIR"

cd "$KODO_DIR" || exit
# Switch to the tested commit to avoid API changes
git checkout -b dev 8c62434ec1b02cf7a33ddcfb9f1bca551f64cd37
python3 waf configure
python3 waf build

cp ./build/linux/kodo*.so "$CUR_DIR/kodo.so"
