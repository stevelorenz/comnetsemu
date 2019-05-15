#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Multi-hop topology for network coding application(s)
"""


import time
from shlex import split
from subprocess import check_output

from comnetsemu.net import Containernet, VNFManager
from mininet.cli import CLI
from mininet.log import info, setLogLevel, error
from mininet.node import Controller


# TODO(zuo): Add placement algo here
def get_recoder_placement(recoder_num, link_para={}):
    """Get the placement of the recoder based on link parameters

    :param recoder_num:
    :param link_para:
    """
    return ["forward"] * recoder_num


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


def TestMultiHopNC(host_num, print_recoder_logs=False):
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
            # MARK: The destination MAC address of the frame MUST be updated if this
            # frame is transmitted to a host on which a l4-socket-base program is
            # running. Otherwise the kernel will simply drop packets
            dst_h_ifce = "h{}-s{}".format(host_num-1, host_num-1)
            # Avoid error during querying MAC address
            _try = 0
            while True:
                _try += 1
                time.sleep(0.5)
                dst_h_mac = hosts[-2].MAC(dst_h_ifce)
                print("**** Try %d times to get destination MAC address" % _try)
                if dst_h_mac:
                    break
            # info("[Recoder] The MAC address of the last recoder: %s\n" % dst_h_mac)
            rec_cli += " --dst_mac " + dst_h_mac

            # MARK: recoder uses raw socket, the root privilege is required
            recoder = mgr.addContainer(
                name, hosts[i], "nc_coder",
                " ".join(("sudo python3 ./recoder.py", rec_cli)))
            recoders.append(recoder)

        time.sleep(3)

        info("*** Run NC encoder on host %s\n" % hosts[1].name)
        encoder = mgr.addContainer(
            "encoder", hosts[1], "nc_coder",
            "sudo python3 ./encoder.py h2-s2")

        CLI(net)

        info("*** Run Iperf server on host %s\n" % hosts[-1].name)
        hosts[-1].cmd("iperf -s {} -p 8888 -D".format(hosts[-1].IP()))

        info("*** Run Iperf client on host %s\n" % hosts[0].name)
        # Iperf3 client parameter: Check https://iperf.fr/iperf-doc.php
        iperf_client_para = {
            "server_ip": hosts[-1].IP(),
            "port": 8888,
            "bw": "1K",
            "time": 6,
            "length": "50",
            # "suffix": ""
            # Use UDP rather than TCP
            "suffix": "-u"
            # "suffix": "-u > /dev/null 2>&1 &"
        }
        ret = hosts[0].cmd(
            "iperf -c {server_ip} -p {port} -t {time} -b {bw} -l {length} {suffix}".format(
                **iperf_client_para
            )
        )
        info("*** Output of Iperf client: \n")
        print(ret)

        # Wait until decoder finishes its task
        dec_timeout = 10
        wait_time = 0
        while True:
            time.sleep(3)
            wait_time += 3
            if wait_time > dec_timeout:
                info("*** Decode timeout! Stop the emulation \n")
                break
            log = decoder.dins.logs().decode("utf-8")
            if not log:
                continue
            sig = log.splitlines()[-1].strip()
            if sig == "Decoder will exit.":
                break

        info("*** Decoder will exit. Log of decoder: \n")
        print(decoder.dins.logs().decode("utf-8"))

        info("*** Log of the encoder: \n")
        print(encoder.dins.logs().decode("utf-8"))

        if print_recoder_logs:
            info("*** Log of recoders: \n")
            for r in recoders:
                print(r.dins.logs().decode("utf-8"))

        # dump_ovs_flows(3)

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
    TestMultiHopNC(host_num=5, print_recoder_logs=False)
