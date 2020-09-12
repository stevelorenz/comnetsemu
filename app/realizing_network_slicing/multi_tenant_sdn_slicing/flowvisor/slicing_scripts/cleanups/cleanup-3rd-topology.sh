#!/bin/bash

echo "Starting FlowVisor service..."
sudo /etc/init.d/flowvisor start

echo "Waiting for service to start..."
sleep 10
echo "Done."

echo "Cleaning FlowVisor from slices previously defined..."
fvctl -f /etc/flowvisor/flowvisor.passwd remove-slice video
fvctl -f /etc/flowvisor/flowvisor.passwd remove-slice voip
fvctl -f /etc/flowvisor/flowvisor.passwd remove-slice best-effort

echo "Check cleanup just performed:"
fvctl -f /etc/flowvisor/flowvisor.passwd list-slices
fvctl -f /etc/flowvisor/flowvisor.passwd list-flowspace
