#!/bin/bash

# Start FlowVisor service
echo "Starting FlowVisor service..."
sudo /etc/init.d/flowvisor start

echo "Waiting for service to start..."
sleep 10
echo "Done."

# Get FlowVisor current config
echo "FlowVisor initial config:"
fvctl -f /etc/flowvisor/flowvisor.passwd get-config

# Get FlowVisor current defined slices
echo "FlowVisor initially defined slices:"
fvctl -f /etc/flowvisor/flowvisor.passwd list-slices

# Get FlowVisor current defined flowspaces
echo "FlowVisor initially defined flowspaces:"
fvctl -f /etc/flowvisor/flowvisor.passwd list-flowspace

# Get FlowVisor connected switches
echo "FlowVisor connected switches:"
fvctl -f /etc/flowvisor/flowvisor.passwd list-datapaths

# Get FlowVisor connected switches links up
echo "FlowVisor connected switches links:"
fvctl -f /etc/flowvisor/flowvisor.passwd list-links

# Define the FlowVisor slices
echo "Definition of FlowVisor slices..."
fvctl -f /etc/flowvisor/flowvisor.passwd add-slice video tcp:localhost:10001 admin@videoslice
fvctl -f /etc/flowvisor/flowvisor.passwd add-slice voip tcp:localhost:10002 admin@voipslice
fvctl -f /etc/flowvisor/flowvisor.passwd add-slice best-effort tcp:localhost:10003 admin@besteffortslice

# Check defined slices
echo "Check slices just defined:"
fvctl -f /etc/flowvisor/flowvisor.passwd list-slices

# Define flowspaces
echo "Definition of flowspaces..."

# switch lx edge
fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid1-port4-video-src 1 100 in_port=4,dl_type=0x0800,nw_proto=6,tp_src=9999 video=7
fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid1-port4-video-dst 1 100 in_port=4,dl_type=0x0800,nw_proto=6,tp_dst=9999 video=7

fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid1-port4-voip-src 1 100 in_port=4,dl_type=0x0800,nw_proto=17,tp_src=9998 voip=7
fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid1-port4-voip-dst 1 100 in_port=4,dl_type=0x0800,nw_proto=17,tp_dst=9998 voip=7

fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid1-port4-besteffort 1 1 in_port=4 best-effort=7


fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid1-port5-video-src 1 100 in_port=5,dl_type=0x0800,nw_proto=6,tp_src=9999 video=7
fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid1-port5-video-dst 1 100 in_port=5,dl_type=0x0800,nw_proto=6,tp_dst=9999 video=7

fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid1-port5-voip-src 1 100 in_port=5,dl_type=0x0800,nw_proto=17,tp_src=9998 voip=7
fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid1-port5-voip-dst 1 100 in_port=5,dl_type=0x0800,nw_proto=17,tp_dst=9998 voip=7

fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid1-port5-besteffort 1 1 in_port=5 best-effort=7


# switch rx edge
fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid5-port4-video-src 5 100 in_port=4,dl_type=0x0800,nw_proto=6,tp_src=9999 video=7
fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid5-port4-video-dst 5 100 in_port=4,dl_type=0x0800,nw_proto=6,tp_dst=9999 video=7

fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid5-port4-voip-src 5 100 in_port=4,dl_type=0x0800,nw_proto=17,tp_src=9998 voip=7
fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid5-port4-voip-dst 5 100 in_port=4,dl_type=0x0800,nw_proto=17,tp_dst=9998 voip=7

fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid5-port4-besteffort 5 1 in_port=4 best-effort=7


fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid5-port5-video-src 1 100 in_port=5,dl_type=0x0800,nw_proto=6,tp_src=9999 video=7
fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid5-port5-video-dst 1 100 in_port=5,dl_type=0x0800,nw_proto=6,tp_dst=9999 video=7

fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid5-port5-voip-src 1 100 in_port=5,dl_type=0x0800,nw_proto=17,tp_src=9998 voip=7
fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid5-port5-voip-dst 1 100 in_port=5,dl_type=0x0800,nw_proto=17,tp_dst=9998 voip=7

fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid5-port5-besteffort 1 1 in_port=5 best-effort=7


# internal switches
fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid1-port1-video 1 100 in_port=1 video=7
fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid1-port2-voip 1 100 in_port=2 voip=7
fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid1-port3-best-effort 1 100 in_port=3 best-effort=7


fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid2-video 2 100 any video=7

fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid3-voip 3 100 any voip=7

fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid4-best-effort 4 1 any best-effort=7


fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid5-port1-video 5 100 in_port=1 video=7
fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid5-port2-voip 5 100 in_port=2 voip=7
fvctl -f /etc/flowvisor/flowvisor.passwd add-flowspace dpid5-port3-best-effort 5 100 in_port=3 best-effort=7

# Check all the flowspaces added
echo "Check all flowspaces just defined:"
fvctl -f /etc/flowvisor/flowvisor.passwd list-flowspace
