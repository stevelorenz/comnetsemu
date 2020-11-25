#!/bin/bash
#
# About: Build steinwurf/kodo-rlnc library.
#        This is a private repository and you need a license to build it.
#

CUR_DIR=$PWD
KODO_DIR="$HOME/kodo-rlnc"

if [[ -e "$KODO_DIR" ]]; then
    echo "* Remove $KODO_DIR directory."
    rm -rf $KODO_DIR
fi

git clone git@github.com:steinwurf/kodo-rlnc.git "$KODO_DIR"

cd "$KODO_DIR" || exit
# Switch to a specific tag to avoid API changes.
echo "* Configure and build kodo-rlnc."
git reset --hard 16.1.1
python3 waf configure
python3 waf build
python3 waf install

echo "* Copy to be installed files."
cp -r "$KODO_DIR/kodo-rlnc_install" ./kodo-rlnc_install
