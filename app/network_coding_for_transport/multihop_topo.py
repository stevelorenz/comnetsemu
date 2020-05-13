#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Example of using Network Coding (NC) for transport on a multi-hop topology.
"""


import time
from shlex import split
from subprocess import check_output

from common import SYMBOL_SIZE, META_DATA_LEN
from comnetsemu.net import Containernet, VNFManager
from mininet.link import TCLink
from mininet.log import error, info, setLogLevel
from mininet.node import Controller


def get_ofport(ifce: str):
    """Get the openflow port based on iterface name

    :param ifce (str): Name of the interface.
    """
    return (
        check_output(split("ovs-vsctl get Interface {} ofport".format(ifce)))
        .decode("utf-8")
        .strip()
    )


def config_ipv6(action: str):
    value = 0
    if action == "disable":
        value = 1
    check_output(split(f"sysctl -w net.ipv6.conf.all.disable_ipv6={value}"))
    check_output(split(f"sysctl -w net.ipv6.conf.default.disable_ipv6={value}"))


def add_forward_flow(switch_name, in_port, out_port, proto):
    """Add one forwarding flow."""
    add_flow_cmd = (
        'ovs-ofctl add-flow {sw} "{proto},in_port={in_port},actions={out_port}"'
    )
    check_output(
        split(
            add_flow_cmd.format(
                **{
                    "sw": switch_name,
                    "in_port": in_port,
                    "out_port": out_port,
                    "proto": proto,
                }
            )
        )
    )


def add_ovs_flows(net, switch_num):
    """Add OpenFlow rules for UDP traffic redirection.
    Since the topology and redirection rules in this example are static,
    ovs-ofctl is used to add them statically. Dynamic scenario requires using a
    SDN controller.
    """

    proto_list = ["udp"]
    for proto in proto_list:
        # Add forwards redirection
        for i in range(switch_num - 1):
            check_output(split("ovs-ofctl del-flows s{}".format(i + 1)))
            in_port = get_ofport("s{}-h{}".format((i + 1), (i + 1)))
            out_port = get_ofport("s{}-s{}".format((i + 1), (i + 2)))
            add_forward_flow(f"s{i+1}", in_port, out_port, proto)
            if i == 0:
                continue
            in_port = get_ofport("s{}-s{}".format((i + 1), i))
            out_port = get_ofport("s{}-h{}".format((i + 1), (i + 1)))
            add_forward_flow(f"s{i+1}", in_port, out_port, proto)
    in_port = get_ofport("s{}-s{}".format(switch_num, switch_num - 1))
    out_port = get_ofport("s{}-h{}".format(switch_num, switch_num))
    add_forward_flow(f"s{switch_num}", in_port, out_port, proto)
    # dump_ovs_flows(switch_num)


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


def deploy_coders(mgr, hosts, rec_st_idx, relay_num, action_map):
    """Deploy en-, re- and decoders on the multi-hop topology.

    Since tests run in a non-powerful VM for teaching purpose, the wait time is
    set to 3 seconds.

    :param mgr (VNFManager): Manager instance for all coders.
    :param hosts (list): List of hosts
    :param rec_st_idx (int): The index of the first recoder (start from 0)
    :param relay_num (int): Number of recoders
    :param action_map (list): Action maps of the recoders, can be forward or recode
    """
    recoders = list()

    info(
        "*** Run NC recoder(s) in the middle, on hosts %s...\n"
        % (", ".join([x.name for x in hosts[rec_st_idx : rec_st_idx + relay_num]]))
    )
    for i in range(rec_st_idx, rec_st_idx + relay_num):
        name = "recoder_on_h%d" % (i + 1)
        rec_cli = "h{}-s{} --action {}".format(i + 1, i + 1, action_map[i - 2])
        recoder = mgr.addContainer(
            name,
            hosts[i].name,
            "nc_coder",
            " ".join(("sudo python3 ./recoder.py", rec_cli)),
            wait=3,
            docker_args={},
        )
        recoders.append(recoder)
    time.sleep(relay_num)
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
        "sudo python3 ./encoder.py h2-s2 --disable_systematic",
        wait=3,
        docker_args={},
    )

    return (encoder, decoder, recoders)


def remove_coders(mgr, coders):
    encoder, decoder, recoders = coders
    mgr.removeContainer(encoder.name)
    mgr.removeContainer(decoder.name)
    for r in recoders:
        mgr.removeContainer(r.name)


def print_coders_log(coders, coder_log_conf):
    """Print the logs of coders based on values in coder_log_conf."""
    encoder, decoder, recoders = coders
    if coder_log_conf.get("recoder", None):
        info("*** Log of recoders: \n")
        for r in recoders:
            print(r.getLogs())

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
        "Run Iperf test between {} (Client) and {}(Server), protocol: {},"
        "target bandwith: {}, duration: {} seconds.\n".format(
            h_clt.name, h_srv.name, proto, IPERF_BANDWIDTH, IPERF_TEST_DURATION
        )
    )
    iperf_client_para = {
        "server_ip": h_srv.IP(),
        "port": 9999,
        "bw": IPERF_BANDWIDTH,
        "time": time,
        "interval": IPERF_TEST_DURATION,
        "length": str(SYMBOL_SIZE - META_DATA_LEN),
        "proto": "-u",
        "suffix": "> /dev/null 2>&1 &",
    }
    if proto == "UDP" or proto == "udp":
        iperf_client_para["proto"] = "-u"
        iperf_client_para["suffix"] = ""

    h_srv.cmd(
        "iperf -s -p 9999 -i {} {} > /tmp/iperf_server.log 2>&1 &".format(
            iperf_client_para["interval"], iperf_client_para["proto"]
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

    h_srv.cmd("killall iperf")


def create_topology(net, host_num):
    """Create the multi-hop topology

    :param net (Mininet):
    :param host_num (int): Number of hosts
    """

    hosts = list()

    if host_num < 5:
        raise RuntimeError("Require at least 5 hosts")
    try:
        info("*** Adding controller\n")
        net.addController("c0")

        info("*** Adding Docker hosts and switches in a multi-hop chain topo\n")
        last_sw = None
        # Connect hosts
        for i in range(host_num):
            # Let kernel schedule all hosts based on their workload.
            # The recoder needs more computational resources than en- and decoder.
            # Hard-coded cfs quota can cause different results on machines with
            # different performance.
            host = net.addDockerHost(
                "h%s" % (i + 1),
                dimage="dev_test",
                ip="10.0.0.%s" % (i + 1),
                docker_args={"hostname": "h%s" % (i + 1)},
            )
            hosts.append(host)
            switch = net.addSwitch("s%s" % (i + 1))
            # No losses between each host-switch pair, this link is used to
            # transmit OAM packet.
            # Losses are emulated with links between switches.
            net.addLinkNamedIfce(switch, host, delay="20ms")
            if last_sw:
                if last_sw == "s1" or switch == f"s{host_num}":
                    net.addLinkNamedIfce(switch, last_sw, delay="20ms", loss=0)
                else:
                    net.addLinkNamedIfce(
                        switch, last_sw, delay="20ms", loss=RELAY_LINK_LOSS
                    )
            last_sw = switch

        return hosts

    except Exception as e:
        error(e)
        net.stop()


def run_multihop_nc_test(host_num, profile, coder_log_conf):

    config_ipv6(action="disable")
    net = Containernet(controller=Controller, link=TCLink, autoStaticArp=True)
    mgr = VNFManager(net)
    hosts = create_topology(net, host_num)
    # Number of relays in the middle.
    relay_num = host_num - 2 - 2
    rec_st_idx = 2

    try:
        info("*** Starting network\n")
        net.start()
        info("*** Adding OpenFlow rules\n")
        add_ovs_flows(net, host_num)
        info("*** Disable Checksum offloading\n")
        disable_cksum_offload(host_num)

        if profile == PROFILES["forward_vs_recode"]:
            info("*** Run experiment to compare forwarding and recoding.\n")

            for action in ["forward", "recode"]:
                action_map = [action] * relay_num
                info(
                    "Number of relays: %s, the action map: %s\n"
                    % (relay_num, ", ".join(action_map))
                )
                coders = deploy_coders(mgr, hosts, rec_st_idx, relay_num, action_map)
                # Wait for coders to be ready
                time.sleep(3)
                run_iperf_test(hosts[0], hosts[-1], "udp", IPERF_TEST_DURATION)
                print_coders_log(coders, coder_log_conf)
                remove_coders(mgr, coders)

        info("*** Emulation stops...\n")

    except Exception as e:
        error("*** Emulation has errors:\n")
        error(e)
    finally:
        info("*** Stopping network\n")
        net.stop()
        mgr.stop()
        config_ipv6(action="enable")


if __name__ == "__main__":

    # Default global parameters
    HOST_NUM = 7
    # Duration of the Iperf traffic in seconds.
    IPERF_TEST_DURATION = 15
    IPERF_BANDWIDTH = "10K"
    # The loss rate between each relay, there is no losses between the client,
    # encoder and decoder, server.
    RELAY_LINK_LOSS = 10

    setLogLevel("info")
    coder_log_conf = {"encoder": False, "decoder": False, "recoder": False}

    PROFILES = {"forward_vs_recode": 0}
    run_multihop_nc_test(HOST_NUM, PROFILES["forward_vs_recode"], coder_log_conf)
