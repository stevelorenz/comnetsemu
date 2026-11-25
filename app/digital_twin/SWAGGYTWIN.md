# SWAGGY TWIN

**Project by August Skorgen Rakvaag and Victor Beisland Hessevaagbakke done the Fall of 2026 at the University of Trento**

### Table of Content
- Project file-structure
- Project set-up
- Project task 
- Our solution

## File-structure
  
```
digital_twin/  
├── change_scenario.py  
├── physical_net.py  
├── ryu_client.py  
├── ryu_manager.sh  
├── ryu_twin_manager.sh  
├── traffic_mirror.py  
├── twin_builder.py  
├── validate.py  
├── viz.py  
├── SWAGGYTWIN.md  
└── .gitignore  
```

## Project set-up

**If you are not familiar with the Comnetsemu a guide to the basic setup can be found under .. \ ..\comnetsemu\README.md.**


The project runs inside the ComNetsEmu virtual machine (Ubuntu 20.04).
Your own computer can run Windows, macOS or Linux, since the VM is created automatically.

> **Note:** ComNetsEmu is built for x86 machines. Apple Silicon Macs (M1–M4) are not supported.

### 1. Install the requirements on your computer
- [VirtualBox](https://www.virtualbox.org/wiki/Downloads)
- [Vagrant](https://developer.hashicorp.com/vagrant/install)
- Git

At least 2 vCPUs and 2 GB RAM should be available for the VM.

### 2. Create the ComNetsEmu VM
```bash
cd ~
git clone https://git.comnets.net/public-repo/comnetsemu.git
cd comnetsemu
vagrant up comnetsemu
```
The first run takes about 15 minutes. The VM is ready when the ComNetsEmu banner is printed.

### 3. Get our project into the VM
SSH into the VM (`-X` enables graphical windows, which are needed for `xterm` and the visualization):
```bash
vagrant ssh comnetsemu -- -X
```
Inside the VM, clone this repository:
```bash
cd ~
git clone <https://github.com/augustrakvaag/comnetsemu.git>
cd <comnetsemu>/digital_twin
```

### 4. Make the scripts executable
```bash
chmod +x ryu_manager.sh ryu_twin_manager.sh
```

**Windows users:** use [MobaXterm](https://mobaxterm.mobatek.net/) as the terminal so graphical windows (`xterm`, plots) open correctly.

The setup is now complete. See [How to use](#how-to-use) to run the digital twin.
 


## Project task

Digital Twin for SDN networks
- GOAL: **To buid a script that allows to generate the
Digital Twin of an SDN network**
- Exploit RYU Northbound RestAPI to retrieve the
topology- and traffic-related information
- The procedure should be completely automated
- Runtime, changes to the Physical Twin are
reproduced automatically to the Digital Twin


## Our solution

## How to use

Everything is run **inside the VM** from `~/comnetsemu/app/digital_twin`.
You need **four terminals**. Open each one with:
```bash
vagrant ssh comnetsemu
cd ~/comnetsemu/app/digital_twin
```

### 1. Start both controllers
**Terminal 1:**
```bash
bash ryu_manager.sh
```
**Terminal 2:**
```bash
bash ryu_twin_manager.sh
```

### 2. Start the physical network
**Terminal 3:**
```bash
sudo python3 physical_net.py
```
Wait until `pingAll` is done and the `mininet>` prompt appears.

### 3. Build the digital twin
**Terminal 4:**
```bash
sudo python3 twin_builder.py
```
The twin builder fetches the topology from the physical controller (port 8080) and creates an identical
network (switches `ts1`–`ts3`, hosts `th1`–`th3`) connected to the twin controller (port 6654).
When the twin is built it is validated automatically, and you should see:
```
GREAT SUCCESS!
```
The twin builder then checks the physical network every 5 seconds and rebuilds the twin when something changes.

### 4. Run the change scenario
In **Terminal 3**, type `exit` at the first `mininet>` prompt. This starts the scenario in the background,
and a new `mininet>` prompt appears. The scenario does the following (seconds after it starts):

| Time | Change in the physical network |
|---|---|
| 30 s | Link `h1 – s1` goes down |
| 45 s | Link `h1 – s1` comes back up |
| 60 s | New host `h4` (`10.0.0.4`) is added to `s1` |


Watch **Terminal 4**: when a change is detected it prints `*** Physical network changed!`,
rebuilds the twin and prints `GREAT SUCCESS!` again if the twin matches.

### 5. Validate manually (optional)
You can compare the two networks at any time from a new terminal:
```bash
python3 validate.py
```
It prints `GREAT SUCCESS!` if they match, or a list of differences (`missing_switch`, `extra_host`, ...).

### Stopping and cleaning up
1. Type `exit` at the `mininet>` prompt in Terminal 3, and press `Ctrl+C` in Terminals 1, 2 and 4.
2. Clean up before running again:
```bash
sudo mn -c
```

### Troubleshooting
| Problem | Fix |
|---|---|
| `Could not connect to http://127.0.0.1:8080` | A controller is not running. Start Terminal 1 and 2 first. |
| `Address already in use` | An old controller is still running: `sudo pkill -f ryu-manager` |
| Twin has no hosts | Start `twin_builder.py` only after `pingAll` in Terminal 3 has finished. Ryu only sees hosts that have sent traffic. |
| Errors about existing interfaces | Run `sudo mn -c` |