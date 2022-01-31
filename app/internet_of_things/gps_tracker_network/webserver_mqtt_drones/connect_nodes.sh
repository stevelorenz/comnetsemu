#!/bin/bash
#
ovs-ofctl add-flow s1 dl_dst="00:00:00:00:00:07",actions=output:1
ovs-ofctl add-flow s1 dl_dst="00:00:00:00:00:08",actions=output:2
ovs-ofctl add-flow s1 dl_dst="00:00:00:00:00:09",actions=output:3
ovs-ofctl add-flow s1 dl_type=0x806,nw_proto=1,actions=flood
#
ovs-ofctl add-flow s2 dl_dst="00:00:00:00:00:07",actions=output:1
ovs-ofctl add-flow s2 dl_src="00:00:00:00:00:07",dl_dst="00:00:00:00:00:01",actions=output:2
ovs-ofctl add-flow s2 dl_src="00:00:00:00:00:02",dl_dst="00:00:00:00:00:01",actions=output:2
ovs-ofctl add-flow s2 dl_src="00:00:00:00:00:03",dl_dst="00:00:00:00:00:01",actions=output:2
ovs-ofctl add-flow s2 dl_src="00:00:00:00:00:07",dl_dst="00:00:00:00:00:02",actions=output:3
ovs-ofctl add-flow s2 dl_src="00:00:00:00:00:01",dl_dst="00:00:00:00:00:02",actions=output:3
ovs-ofctl add-flow s2 dl_src="00:00:00:00:00:03",dl_dst="00:00:00:00:00:02",actions=output:3
ovs-ofctl add-flow s2 dl_src="00:00:00:00:00:07",dl_dst="00:00:00:00:00:03",actions=output:4
ovs-ofctl add-flow s2 dl_src="00:00:00:00:00:01",dl_dst="00:00:00:00:00:03",actions=output:4
ovs-ofctl add-flow s2 dl_src="00:00:00:00:00:02",dl_dst="00:00:00:00:00:03",actions=output:4
ovs-ofctl add-flow s2 dl_type=0x806,nw_proto=1,actions=flood
#
ovs-ofctl add-flow s3 dl_dst="00:00:00:00:00:07",actions=output:1
ovs-ofctl add-flow s3 dl_src="00:00:00:00:00:07",dl_dst="00:00:00:00:00:04",actions=output:2
ovs-ofctl add-flow s3 dl_src="00:00:00:00:00:05",dl_dst="00:00:00:00:00:04",actions=output:2
ovs-ofctl add-flow s3 dl_src="00:00:00:00:00:06",dl_dst="00:00:00:00:00:04",actions=output:2
ovs-ofctl add-flow s3 dl_src="00:00:00:00:00:07",dl_dst="00:00:00:00:00:05",actions=output:3
ovs-ofctl add-flow s3 dl_src="00:00:00:00:00:04",dl_dst="00:00:00:00:00:05",actions=output:3
ovs-ofctl add-flow s3 dl_src="00:00:00:00:00:06",dl_dst="00:00:00:00:00:05",actions=output:3
ovs-ofctl add-flow s3 dl_src="00:00:00:00:00:07",dl_dst="00:00:00:00:00:06",actions=output:4
ovs-ofctl add-flow s3 dl_src="00:00:00:00:00:04",dl_dst="00:00:00:00:00:06",actions=output:4
ovs-ofctl add-flow s3 dl_src="00:00:00:00:00:05",dl_dst="00:00:00:00:00:06",actions=output:4
ovs-ofctl add-flow s3 dl_type=0x806,nw_proto=1,actions=flood
#
ovs-ofctl add-flow s4 dl_dst="00:00:00:00:00:07",actions=output:1
ovs-ofctl add-flow s4 dl_src="00:00:00:00:00:07",dl_dst="00:00:00:00:00:08",actions=output:2
ovs-ofctl add-flow s4 dl_src="00:00:00:00:00:07",dl_dst="00:00:00:00:00:01",actions=output:3
ovs-ofctl add-flow s4 dl_src="00:00:00:00:00:07",dl_dst="00:00:00:00:00:02",actions=output:3
ovs-ofctl add-flow s4 dl_src="00:00:00:00:00:07",dl_dst="00:00:00:00:00:03",actions=output:3
ovs-ofctl add-flow s4 dl_src="00:00:00:00:00:07",dl_dst="00:00:00:00:00:04",actions=output:4
ovs-ofctl add-flow s4 dl_src="00:00:00:00:00:07",dl_dst="00:00:00:00:00:05",actions=output:4
ovs-ofctl add-flow s4 dl_src="00:00:00:00:00:07",dl_dst="00:00:00:00:00:06",actions=output:4
ovs-ofctl add-flow s4 dl_type=0x806,nw_proto=1,actions=flood