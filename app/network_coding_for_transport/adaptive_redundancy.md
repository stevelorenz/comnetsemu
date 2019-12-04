# Network Coding for Transport #
## Adaptive redundancy ##
### Motivation and Setup ###
This examples demonstrates how to leverage the SDN controller's knowledge about the network parameters to flexibly adapt
the redundancy created by Random Linear Network Coding (RLNC) to repair losses in the transmission.

A simple Client - Encoder - Decoder - Server topology is created with an unknown loss ratio between the encoder and decoder.
The goal of this example is to show, that the controller can estimate these losses and precisely adapt the amount of
redundancy to guarantee a certain delivery probability for each packet transmitted. 

The following figure depicts the setup:

```text
Control plane:                     SDN Controller
                                   /            \
Data plane:    Switch1 --- Switch2 --- Dummy --- Switch4 --- Switch5
                  |           |                     |           |
Hosts:         Host1       Host2                 Host3       Host4 
                  |           |                     |           |
Programs:      Client      Encoder    Loss emu.  Decoder     Server
```

### Running the experiment ###

The experiment can be run with:

```
$ sudo python3 adaptive_redundancy.py
```

Parameters can be found in [common.py](./common.py)