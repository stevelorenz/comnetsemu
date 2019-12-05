## Reinforcement Learning for Routing in Software-defined networks ##
**NOTE: This example requires _libvirt_ as virtual machine provider instead of _Virtualbox_**
### Setup ###

```text
             s2 (3 MBits/s)
   h1  10ms/    \10ms  h4
   h2 -- s1      s3 -- h5
   h3  14ms\    /14ms  h6
             s4 (4 MBits/s)
```

This example requires additional libraries for statistical calculations.
These can be installed with:
```bash
$ sudo ./install_dependencies.sh
```

### How to run ###
This example requires two terminals.

Terminal 1:
```bash
$ sudo python3 ./example_scenario.py
``` 

Terminal 2:
```bash
$ ryu-manager ./controller/remote_controller.py
``` 

Parameters can be found in [controller/config.py](./controller/config.py)