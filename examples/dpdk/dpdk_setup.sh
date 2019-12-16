#!/bin/bash
#
# dpdk_setup.sh
#

HUGEPAGE_NUM_2048=256

echo "* Setup hugepages when OS is already booted."
echo "- Default hugepages size: $((HUGEPAGE_NUM_2048 * 2)) MB"

mkdir -p /mnt/huge
(mount | grep hugetlbfs) >/dev/null || mount -t hugetlbfs nodev /mnt/huge
for i in {0..7}; do
    if [[ -e "/sys/devices/system/node/node$i" ]]; then
        echo $HUGEPAGE_NUM_2048 >/sys/devices/system/node/node$i/hugepages/hugepages-2048kB/nr_hugepages
    fi
done

grep 'Huge' /proc/meminfo
