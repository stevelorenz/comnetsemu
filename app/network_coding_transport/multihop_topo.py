#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Multi-hop topology for network coding application(s)
"""


import csv
import time
from shlex import split
from subprocess import check_output

from common import SYMBOL_SIZE
from comnetsemu.net import Containernet, VNFManager
from mininet.cli import CLI
from mininet.log import error, info, setLogLevel
from mininet.node import Controller


def get_recoder_placement(recoder_num, link_para={}):
    """Get the placement of the recoder based on link parameters

    :param recoder_num:
    :param link_para:
    """
    return ["recode"] * recoder_num


def get_ofport(ifce):
    """Get the openflow port based on iterface name

    :param ifce (str): Name of the interface
    """
    return check_output(
        split("sudo ovs-vsctl get Interface {} ofport".format(ifce)
              )).decode("utf-8")


def add_ovs_flows(net, switch_num):
    """Add OpenFlow rules for TCP/UDP traffic for dev tests, SHOULD be performed by the SDN controller"""

    for i in range(switch_num - 1):
        check_output(
            split("sudo ovs-ofctl del-flows s{}".format(i+1))
        )
        proto = "udp"
        in_port = get_ofport("s{}-h{}".format((i+1), (i+1)))
        out_port = get_ofport("s{}-s{}".format((i+1), (i+2)))
        check_output(
            split(
                "sudo ovs-ofctl add-flow s{sw} \"{proto},in_port={in_port},actions=output={out_port}\"".format(
                    **{"sw": (i+1), "in_port": in_port, "out_port": out_port,
                       "proto": proto}
                )
            )
        )

        if i == 0:
            continue

        in_port = get_ofport("s{}-s{}".format((i+1), i))
        out_port = get_ofport("s{}-h{}".format((i+1), (i+1)))
        check_output(
            split(
                "sudo ovs-ofctl add-flow s{sw} \"{proto},in_port={in_port},actions=output={out_port}\"".format(
                    **{"sw": (i+1), "in_port": in_port, "out_port": out_port,
                       "proto": proto}
                )
            )
        )


def dump_ovs_flows(switch_num):
    """Dump OpenFlow rules of first switch_num switches"""
    for i in range(switch_num):
        ret = check_output(split("sudo ovs-ofctl dump-flows s{}".format(i+1)))
        info("### Flow table of the switch s{} after adding flows:\n".format(
            i+1))
        print(ret.decode("utf-8"))


def disable_cksum_offload(switch_num):
    """Disable RX/TX checksum offloading"""
    for i in range(switch_num):
        ifce = "s%s-h%s" % (i+1, i+1)
        check_output(
            split("sudo ethtool --offload %s rx off tx off" % ifce)
        )


def save_hosts_info(hosts):
    info = list()
    for i, h in enumerate(hosts):
        mac = str(h.MAC("h{}-s{}".format(i+1, i+1)))
        ip = str(h.IP())
        info.append([h.name, mac, ip])

    with open('hosts_info.csv', 'w+') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for i in info:
            writer.writerow(i)


def TestMultiHopNC(host_num, coder_log_conf):
    "Create an empty network and add nodes to it."

    if host_num < 5:
        raise RuntimeError("Require at least 5 hosts")

    net = Containernet(controller=Controller)
    mgr = VNFManager(net)

    info('*** Adding controller\n')
    net.addController('c0')

    try:
        info("*** Adding Docker hosts and switches in a multi-hop chain topo\n")
        hosts = list()
        last_sw = None
        # Connect hosts
        for i in range(host_num):
            # Each host gets 50%/n of system CPU
            host = net.addDockerHost(
                'h%s' % (i+1), dimage='dev_test', ip='10.0.0.%s' % (i+1),
                cpu_quota=int(50000 / host_num),
                volumes=["/var/run/docker.sock:/var/run/docker.sock:rw"])
            hosts.append(host)
            switch = net.addSwitch("s%s" % (i + 1))
            net.addLinkNamedIfce(switch, host, bw=10, delay="1ms", use_htb=True)
            if last_sw:
                # Connect switches
                net.addLinkNamedIfce(switch, last_sw,
                                     bw=10, delay="1ms", use_htb=True)
            last_sw = switch

        # save_hosts_info(hosts)

        info("*** Starting network\n")
        net.start()
        info("*** Ping all to update ARP tables of each host\n")
        net.pingAll()

        info("*** Adding OpenFlow rules\n")
        add_ovs_flows(net, host_num)
        info("*** Disable Checksum offloading\n")
        disable_cksum_offload(host_num)

        info("*** Run NC decoder on host %s\n" % hosts[-2].name)
        decoder = mgr.addContainer(
            "decoder", hosts[-2], "nc_coder",
            "sudo python3 ./decoder.py h%d-s%d" % (host_num-1, host_num-1))

        rec_num = host_num - 2 - 2
        recoders = list()
        info("*** Run NC recoder(s) in the middle, on hosts %s...\n" % (
            ", ".join([x.name for x in hosts[2:2+rec_num]])))
        action_map = get_recoder_placement(rec_num)
        print("Action map of recoders: %s" % ", ".join(action_map))
        for i in range(2, 2+rec_num):
            name = "recoder_on_h%d" % (i+1)
            rec_cli = "h{}-s{} --action {}".format(i+1, i+1, action_map[i-2])
            recoder = mgr.addContainer(
                name, hosts[i], "nc_coder",
                " ".join(("sudo python3 ./recoder.py", rec_cli)))
            recoders.append(recoder)

        time.sleep(3)

        info("*** Run NC encoder on host %s\n" % hosts[1].name)
        encoder = mgr.addContainer(
            "encoder", hosts[1], "nc_coder",
            "sudo python3 ./encoder.py h2-s2")
        # Wait for encoder to be ready
        time.sleep(3)

        info("*** Run Iperf server on host %s in background.\n" %
             hosts[-1].name)
        hosts[-1].cmd(
            "iperf -s {} -p 9999 -i 1 -u > /tmp/iperf_server.log 2>&1 &".format(
                hosts[-1].IP()))

        info("*** Run Iperf client on host %s, wait for its output...\n" %
             hosts[0].name)
        iperf_client_para = {
            "server_ip": hosts[-1].IP(),
            "port": 9999,
            "bw": "1K",
            "time": 10,
            "interval": 1,
            "length": str(SYMBOL_SIZE - 60),
            # Use UDP rather than TCP "proto": "-u",
            "proto": "-u",
            "suffix": "",
            # "proto": "",
            # "suffix": "> /dev/null 2>&1 &"
        }

        iperf_clt_cmd = """iperf -c {server_ip} -p {port} -t {time} -i {interval} -b {bw} -l {length} {proto} {suffix}""".format(
            **iperf_client_para)
        print("Iperf client command: {}".format(iperf_clt_cmd))
        ret = hosts[0].cmd(iperf_clt_cmd)
        info("*** Output of Iperf client:\n")
        print(ret)

        info("*** Output of Iperf server:\n")
        print(hosts[-1].cmd("cat /tmp/iperf_server.log"))

        if coder_log_conf.get("decoder", None):
            info("*** Log of decoder: \n")
            print(decoder.dins.logs().decode("utf-8"))

        if coder_log_conf.get("encoder", None):
            info("*** Log of the encoder: \n")
            print(encoder.dins.logs().decode("utf-8"))

        if coder_log_conf.get("recoder", None):
            info("*** Log of recoders: \n")
            for r in recoders:
                print(r.dins.logs().decode("utf-8"))

        info("*** Emulation stops...")
        mgr.removeContainer("encoder")
        mgr.removeContainer("decoder")
        for r in recoders:
            mgr.removeContainer(r)

    except Exception as e:
        error("*** Emulation has errors:")
        print(e)
    finally:
        info('*** Stopping network\n')
        net.stop()
        mgr.stop()


if __name__ == '__main__':

    setLogLevel('info')
    coder_log_conf = {
        "encoder": False,
        "decoder": False,
        "recoder": False
    }

    TestMultiHopNC(5, coder_log_conf)
