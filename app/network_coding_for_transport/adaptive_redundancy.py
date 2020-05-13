#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Example of using Network Coding (NC) for transport with adaptive redundancy.
"""


import csv
import time
from shlex import split
from subprocess import check_output

from common import *
from comnetsemu.net import Containernet, VNFManager
from mininet.log import error, info, setLogLevel
from mininet.node import Controller, RemoteController
from mininet.link import TCLink
from mininet.term import makeTerm
from mininet.cli import CLI


def get_ofport(ifce):
    """Get the openflow port based on iterface name

    :param ifce (str): Name of the interface.
    """
    return check_output(split("ovs-vsctl get Interface {} ofport".format(ifce))).decode(
        "utf-8"
    )


def add_ovs_flows(net, switch_num):
    """Add OpenFlow rules for ARP/PING packets and other general traffic"""

    check_output(split('ovs-ofctl add-flow s1 "priority=1,in_port=1,actions=output=2"'))
    check_output(split('ovs-ofctl add-flow s2 "priority=1,in_port=2,actions=output=3"'))
    check_output(split('ovs-ofctl add-flow s3 "priority=1,in_port=2,actions=output=3"'))
    check_output(split('ovs-ofctl add-flow s4 "priority=1,in_port=2,actions=output=3"'))
    check_output(split('ovs-ofctl add-flow s5 "priority=1,in_port=2,actions=output=1"'))

    check_output(split('ovs-ofctl add-flow s1 "priority=1,in_port=2,actions=output=1"'))
    check_output(split('ovs-ofctl add-flow s2 "priority=1,in_port=3,actions=output=2"'))
    check_output(split('ovs-ofctl add-flow s3 "priority=1,in_port=3,actions=output=2"'))
    check_output(split('ovs-ofctl add-flow s4 "priority=1,in_port=3,actions=output=2"'))
    check_output(split('ovs-ofctl add-flow s5 "priority=1,in_port=1,actions=output=2"'))


def dump_ovs_flows(switch_num):
    """Dump OpenFlow rules of first switch_num switches"""
    for i in range(switch_num):
        ret = check_output(split("ovs-ofctl dump-flows s{}".format(i + 1)))
        info("### Flow table of the switch s{} after adding flows:\n".format(i + 1))
        print(ret.decode("utf-8"))


def disable_cksum_offload(switch_num):
    """Disable RX/TX checksum offloading"""
    for i in range(switch_num):
        ifce = "s%s-h%s" % (i + 1, i + 1)
        check_output(split("ethtool --offload %s rx off tx off" % ifce))


def deploy_coders(mgr, hosts):
    """Deploy en- and decoders on the multi-hop topology

    Since the tests run in a non-powerful VM for teaching purpose, the wait time
    is set to 3 seconds.

    :param mgr (VNFManager):
    :param hosts (list): List of hosts
    :param rec_st_idx (int): The index of the first recoder (start from 0)
    :param rec_num (int): Number of recoders
    :param action_map (list): Action maps of the recoders, can be forward or recode
    """

    info("*** Run NC decoder on host %s\n" % hosts[-2].name)
    decoder = mgr.addContainer(
        "decoder",
        hosts[-2].name,
        "nc_coder",
        "sudo python3 ./decoder.py h%d-s%d" % (len(hosts) - 1, len(hosts) - 1),
        wait=3,
        docker_args={},
    )
    info("*** Run NC encoder on host %s\n" % hosts[1].name)
    encoder = mgr.addContainer(
        "encoder",
        hosts[1].name,
        "nc_coder",
        "sudo python3 ./encoder.py h2-s2",
        wait=3,
        docker_args={},
    )

    return (encoder, decoder)


def remove_coders(mgr, coders):
    encoder, decoder = coders
    mgr.removeContainer(encoder.name)
    mgr.removeContainer(decoder.name)


def print_coders_log(coders, coder_log_conf):
    encoder, decoder = coders

    if coder_log_conf.get("decoder", None):
        info("*** Log of decoder: \n")
        print(decoder.dins.logs().decode("utf-8"))

    if coder_log_conf.get("encoder", None):
        info("*** Log of the encoder: \n")
        print(encoder.dins.logs().decode("utf-8"))


def run_iperf_test(h_clt, h_srv, proto, time=10, print_clt_log=False):
    """Run Iperf tests between h_clt and h_srv (DockerHost) and print the output
    of the Iperf server.

    :param proto (str):  Transport protocol, UDP or TCP
    :param time (int): Duration of the traffic flow
    :param print_clt_log (Bool): If true, print the log of the Iperf client
    """
    info(
        "Run Iperf test between {} (Client) and {} (Server), protocol: {}\n".format(
            h_clt.name, h_srv.name, proto
        )
    )
    iperf_client_para = {
        "server_ip": h_srv.IP(),
        "port": UDP_PORT_DATA,
        "bw": "200K",
        "time": time,
        "interval": 1,
        "length": str(SYMBOL_SIZE - META_DATA_LEN),
        "proto": "-u",
        "suffix": "> /dev/null 2>&1 &",
    }
    if proto == "UDP" or proto == "udp":
        iperf_client_para["proto"] = "-u"
        iperf_client_para["suffix"] = ""

    h_srv.cmd(
        "iperf -s -p {} -i 1 {} > /tmp/iperf_server.log 2>&1 &".format(
            UDP_PORT_DATA, iperf_client_para["proto"]
        )
    )

    iperf_clt_cmd = """iperf -c {server_ip} -p {port} -t {time} -i {interval} -b {bw} -l {length} {proto} {suffix}""".format(
        **iperf_client_para
    )
    print("Iperf client command: {}".format(iperf_clt_cmd))
    ret = h_clt.cmd(iperf_clt_cmd)

    info("*** Output of Iperf server:\n")
    print(h_srv.cmd("cat /tmp/iperf_server.log"))

    if print_clt_log:
        info("*** Output of Iperf client:\n")
        print(ret)


def create_topology(net, host_num):
    """Create the multi-hop topology

    :param net (Mininet):
    :param host_num (int): Number of hosts
    """

    hosts = list()

    try:
        info("*** Adding controller\n")
        net.addController("c0", controller=RemoteController, port=6653)

        info("*** Adding Docker hosts and switches in a multi-hop chain topo\n")
        last_sw = None
        # Connect hosts
        for i in range(host_num):
            # Each host gets 50%/n of system CPU
            host = net.addDockerHost(
                "h%s" % (i + 1),
                dimage="dev_test",
                ip="10.0.0.%s" % (i + 1),
                docker_args={"cpu_quota": int(50000 / host_num)},
            )
            hosts.append(host)
            switch = net.addSwitch("s%s" % (i + 1))
            # MARK: The losses are emulated via netemu of host's interface
            net.addLinkNamedIfce(switch, host, bw=10, delay="1ms", use_htb=True)
            if last_sw:
                # Connect switches
                if switch.name == "s4" and last_sw.name == "s3":
                    net.addLinkNamedIfce(
                        switch, last_sw, use_htb=True, bw=10, delay="1ms", loss=30
                    )
                    # info('Add losses between Switches: {} {}\n'.format(switch, last_sw))
                else:
                    net.addLinkNamedIfce(
                        switch, last_sw, use_htb=True, bw=10, delay="1ms"
                    )
            last_sw = switch

        return hosts

    except Exception as e:
        error(e)
        net.stop()


def run_adaptive_redundancy(host_num, coder_log_conf):
    """Run network application for multi-hop topology

    :param host_num (int): Number of hosts
    :param profile (int): To be tested profile
    :param coder_log_conf (dict): Configs for logs of coders
    """

    net = Containernet(controller=RemoteController, link=TCLink, autoStaticArp=True)
    mgr = VNFManager(net)
    hosts = create_topology(net, host_num)

    try:
        info("*** Starting network\n")
        net.start()
        # MARK: Use static ARP to avoid ping losses
        # info("*** Ping all to update ARP tables of each host\n")
        # net.pingAll()
        info("*** Adding OpenFlow rules\n")
        add_ovs_flows(net, host_num)
        info("*** Disable Checksum offloading\n")
        disable_cksum_offload(host_num)

        info("*** Deploy coders\n")
        coders = deploy_coders(mgr, hosts)
        # Wait for coders to be ready

        info("*** Starting Ryu controller\n")
        c0 = net.get("c0")
        makeTerm(c0, cmd="ryu-manager adaptive_rlnc_sdn_controller.py ; read")

        time.sleep(3)

        info("*** Run Iperf\n")
        run_iperf_test(hosts[0], hosts[-1], "udp", 30)
        print_coders_log(coders, coder_log_conf)
        remove_coders(mgr, coders)

        info("*** Emulation stops...")

    except Exception as e:
        error("*** Emulation has errors:")
        error(e)
    finally:
        info("*** Stopping network\n")
        net.stop()
        mgr.stop()


if __name__ == "__main__":

    setLogLevel("info")
    coder_log_conf = {"encoder": 1, "decoder": 1, "recoder": 1}

    run_adaptive_redundancy(5, coder_log_conf)
