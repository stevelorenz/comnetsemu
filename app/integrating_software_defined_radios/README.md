# Integrating Software-Defined Radios #

# Data transmission using Ettus Research USRP #

In this directory, you can find two examples that show the functionality of USRP systems in real
data transmission applications. Before being enable to exchange data between 2 SDR systems, it is
required the installation of the UHD driver, which ensures the communication between the host computer
 and the USRPs; GNURadio, which is a free and open-source SDK employed to implement software radio transceivers
 through built-in C++ signal processing blocks. GNU Radio supports a large set of platforms, but for the purpose 
of this chapter the development platform is the Ettus Research N210.


## OFDM Modulation ##

The first application is an example about data exchange between two URSPs using an OFDM modulation.
The idea of this exercise is to make the reader familiar with the URSP's programming framework, GNU Radio Companion.
To accomplish this purpose, the reader places different programming blocks to achieve the transmission 
of a text file between the USRP using a OFDM modulation. Physically, the USRP are connected to a host machine, 
which is also connected the emulator ComNetsEmu through a brigde network. 


## OFMD Tunnel ##

The second application is an example about OFDM tunnel between two USRPs connected via a physical 
unmanaged TP-LINK switch, as depicted in the figure of the setup description section.

An OFDM tunnel provides a virtual Ethernet interface between 2 USRPs throughout the physical (PHY) and 
medium access control (MAC) layers. Hence, several IP-based applications, which correspond to applications 
in upper layers, can be inserted in the tunnel to transmit and receive data. 

The PHY layer is composed of: transmitter, receiver and sensors. 
Bits are gathered on the USRP's buffers and transmitted and received using digital-to-analog and analog-to-digital 
converters to transform the information bits to baseband waveforms. 

The MAC layer is based on the carrier-sense multiple access (CSMA) protocol. Therefore, the transfer of data packets, 
between the PHY and the MAC, is carried out by the addition of some
headers inside the IP-packet received at the PHY layer.

## Setup description ##

The two USRPs are connected to the host computer using a TP-LINK switch as it is depicted in the figure below.
Each USRP, called SDR A and SDR B, has a IP address, which allows to identify them to assign a signal processing function:
receiver or transmitter.

````Text

		| HOST PC |
		     |	
		     |
                | SWITCH | 

		/	  \
	       /	   \
---------                           -------- 
| SDR A |  ---- OFDM tunnel  ----  | SDR B |
---------                           -------- 
````

## Testbed start ##
Run the script ./setup.sh inside the integrating _software_defined_radios directory.

To run an example, access to the examples directory, and select the example you desire to execute. 

````Text
examples/<name>
````
Run the containers with the following command:

````Text
docker-compose up
````
Login into the containerized running examples with following command:

````Text
docker exec -it sdr[1|2] /bin/bash
````



