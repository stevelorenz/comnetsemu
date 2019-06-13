This documentation uses the same build tool (doxygen) of Mininet. You can view namespaces, classes, files just like
Mininet's API documentation(http://mininet.org/api/hierarchy.html).

Detailed documentation of each class can be found in the **Classes** tab (MARK: Javascript needs to be enabled for tab
support).

Brief Summary:

- In order to enable Docker-in-Docker setup, following Mininet modules are enhanced in ComnetsEmu:

  - comnetsemu/node.py: Two sub-classes are added here to enable docker-in-docker setup:

      - DockerHost: Class of external containers. Its instances have the same methods of default Mininet host.

      - DockerContainer: Class of the internal container. To make it simple, currently there are no private methods
          implemented in this sub-class.

  - comnetsemu/net.py: Two classes are added here to manage internal and external Docker hosts:

      - Containernet: Management of the external containers.

      - VNFManager: Management of the internal containers. To make it simple, currently there are only create, delete and
          the cleanup methods are implemented. More methods will be added depending on to be deployed applications.

  - comnetsemu/cli.py: Extended CLI methods to support DockerHost.
