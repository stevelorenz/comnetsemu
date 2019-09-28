# FAQ #

## General Questions ##

##### Why not the vanilla Mininet ?

Default Mininet (the latest version) does not support running Docker containers applications directly inside Mininet Host with sufficient network isolation.
ComNetsEmu adds a new node type: DockerHost to deploy internal Docker application containers.

##### Why not Containernet ?

Containernet did a fork (hold all source codes of Mininet in its own Repo) of the Mininet.
New features and fixes from upstream Mininet can not be **merged** into Containernet **directly**.
ComNetsEmu is only an extension of the upstream Mininet:

-   Mininet's Python modules are installed with its built-in installer and only used as **dependencies**.

-   ComNetsEmu's Python modules only create sub-classes of **essential and minimal** classes of Mininet to add its
    features. So Mininet must be installed before installing ComNetsEmu.

-   With this development profile, upstream's commits can be updated easily by running the installer's update function.

-   ComNetsEmu tries its best to keep the comparability with upstream Mininet. All examples, CLI commands of Mininet
    should also work on ComNetsEmu.

##### Why not Kubernetes(K8s)?

For teaching and emulation on a single laptop, K8s is too heavy and complex.
ComNetsEmu can emulate typical K8s setup with more lightweight virtualisation.
And thanks to Mininet, all links on the data plane can be configured with different bandwidth, link losses or transport delay (Use Linux TC utility). It is great for teaching.
