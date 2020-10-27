## Reinforcement Learning for Congestion Control ##
**NOTE: This example requires _libvirt_ as the virtual machine provider instead of _Virtualbox_**

## Requirements
This example requires Python3.7 and the following Python3.7 modules:
* numpy
* matplotlib
* tensorflow
* keras-rl

Install them with:
```bash
$ pip3 install numpy matplotlib keras-rl
$ pip3 install tensorflow==1.13.1
$ pip3 install keras==2.2.4
```

### Running examples ###
Run
```bash
$ python3 ./dumbbell.py -a
```
to start an emulation of a single flow within a dumbbell topology that lasts for 30 seconds.
Afterwards,
plot the results with
```bash
$ python3 ./plot_tsv.py
```
