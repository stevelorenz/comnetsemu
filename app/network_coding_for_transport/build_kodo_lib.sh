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
git checkout -b dev 5fae21d9e038a54ca9c14845ce7b3a9806b87f4d
python3 waf configure
python3 waf build

cp ./build/linux/kodo*.so "$CUR_DIR/kodo.so"
