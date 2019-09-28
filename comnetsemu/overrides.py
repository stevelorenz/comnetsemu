"""
Overriding functionality that is provided outside the
scope of this project and where subclassing is not possible

Authors:
Patrick Ziegler, Dresden University of Technology
"""

from importlib import __import__
from mininet.log import debug
from mininet.util import errRun, quietRun
import sys


def override(module, name):
    """
    A decorator for replacing a given function of
    a specified module with the decorated function

    Caution:
    Be aware that functions named 'name' in any given module
    will be replaced!
    """
    __import__(module)

    def _wrapper(fn):
        for m in sys.modules:
            if name in dir(sys.modules[m]):
                debug(f"Overriding function {name} in module {m}")
                setattr(sys.modules[m], name, fn)
        return fn

    return _wrapper


@override("mininet.util", "makeIntfPair")
def makeIntfPairFixed(
    intf1,
    intf2,
    addr1=None,
    addr2=None,
    node1=None,
    node2=None,
    deleteIntfs=True,
    runCmd=None,
):
    """Make a veth pair connnecting new interfaces intf1 and intf2
       intf1: name for interface 1
       intf2: name for interface 2
       addr1: MAC address for interface 1 (optional)
       addr2: MAC address for interface 2 (optional)
       node1: home node for interface 1 (optional)
       node2: home node for interface 2 (optional)
       deleteIntfs: delete intfs before creating them
       runCmd: function to run shell commands (quietRun)
       raises Exception on failure"""
    if not runCmd:
        runCmd = quietRun if not node1 else node1.cmd
        runCmd2 = quietRun if not node2 else node2.cmd
    if deleteIntfs:
        # Delete any old interfaces with the same names
        runCmd("ip link del " + intf1)
        runCmd2("ip link del " + intf2)
    # Create new pair
    netns1 = node1.pid
    netns2 = 1 if not node2 else node2.pid
    if addr1 is None and addr2 is None:
        cmd = "ip link add name %s netns %s " "type veth peer name %s netns %s" % (
            intf1,
            netns1,
            intf2,
            netns2,
        )
    else:
        cmd = (
            "ip link add name %s address %s netns %s "
            "type veth peer name %s address %s netns %s"
            % (intf1, addr1, netns1, intf2, addr2, netns2)
        )

    _, cmdOutput, _ = errRun(cmd)

    # iproute2 changes behaviour in release 5.1
    # the following workaround should be removed when
    # issue in iproute2 was fixed
    # [1] https://github.com/mininet/mininet/issues/884
    # [2] https://lwn.net/Articles/783494/
    if "No such device" in cmdOutput:
        debug(
            "Ignored error creating interface pair (%s,%s): %s "
            % (intf1, intf2, cmdOutput)
        )
        cmdOutput = ""

    if cmdOutput:
        raise Exception(
            "Error creating interface pair (%s,%s): %s " % (intf1, intf2, cmdOutput)
        )
