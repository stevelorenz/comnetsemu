#!/bin/bash

ansible-playbook -v \
    --connection=local \
    --inventory 127.0.0.1, \
    --limit 127.0.0.1 ./install_comnetsemu.yml
