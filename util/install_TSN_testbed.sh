#!/bin/bash

sudo apt-get install -y git
cd ~/ || exit
git clone https://github.com/ulbricht-inr/TASim.git
cd TASim || exit
./setup.sh 1
