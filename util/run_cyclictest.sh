#!/bin/bash
#
# About: Run cyclictest to evaluate the realtime performance of the system
#

if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo or as root."
    exit
fi

DURATION="1m"

echo "* Run stress-ng in background to generate workload for ${DURATION}"
stress-ng -c $(nproc) --cpu-method fft -t "${DURATION}" &

echo "* Run cyclictest for ${DURATION}"
# Check the proper configuration for NUMA node.
cyclictest \
    --smp \
    --mlockall \
    --priority=80 \
    --interval=1000 \
    --distance=0 \
    -D "${DURATION}"

echo "The Max value in the table shows the Maximum latency that was measured (in us)."
echo "This value can give an idea of the WORST CASE latency length in the evaluated situation!"

echo ""
echo "More information can be found in the following link:"
echo "https://wiki.linuxfoundation.org/realtime/documentation/howto/tools/cyclictest/start"
