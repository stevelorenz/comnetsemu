
# Data transmission using Ettus Research USRP #
In this directory, you can find two examples that show the functionality of USRP systems in real
data trasmission applications. Before being enable to exchange data between 2 SDR systems, it is
required the installation of the UHD driver, which ensures the communication between the host computer and the USRPs; GNURadio, which is a free and open-source SDK employed to implement software radio transceivers through built-in C++ signal processing blocks. GNU Radio supports a large set of platforms, but for the purpose of this chapter the development platform is the Ettus Research N210.

The details about the installation of the UHD drivers and the GNU can be found in the following link: 
https://kb.ettus.com/Building_and_Installing_the_USRP_Open-Source_Toolchain_(UHD_and_GNU_Radio)_on_Linux

# OFMD Tunnel #
The first application is an example about OFDM tunnel between two USRPs connected via a physical 
unmanaged TP-LINK switch, as depicted.

# Setup description
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
An OFDM tunnel provides a virtual ethernet interface between 2 USRPs throughout the physical (PHY) and medium access control (MAC) layers. Hence, several IP-based applications, which correspond to applications in upper layers, can be inserted in the tunnel to transmit and receive data. 

The PHY layer is composed of: transmitter, receiver and sensors. 
Bits are gathered on the USRP's buffers and transmitted and received using digital-to-analog and analog-to-digital converters to transform the information bits to baseband waveforms. 

The MAC layer is based on the carrier-sense multiple access (CSMA) protocol. Therefore, the transfer of data packets, between the PHY and the MAC, is carried out by the addition of some
headers inside the IP-packet received at the PHY layer.

In order to configure the USRP to run this example, access to the ofdm directory and run the following command to run the tunnel program:

````Text
sudo ./tunnel.py --freq 2.45G --args="192.168.10.2"
````

In a new terminal, create the tunnel for the second USRP with:

````Text
sudo ./tunnel.py --freq 2.45G --args="192.168.10.3"
````

as we dispose of two USRP, one identified with the IP address: 192.168.10.2 and the other with the 
IP address: 192.168.10.3. The previous command is a python file that controls the signal processing blocks to configure the hardware. By following the code instructions, it then required
to configure the virtual ethernet interface of each USRP with the following command:

````Text
sudo ifconfig gr0 192.168.200.1
````

And for the second USRP configure the virtual ethernet interface with:

````Text
sudo ifconfig gr0 192.168.200.2
````

Now the user should be able to ping between both USRP systems seamlessly. For curious users of this
tutorial, it is possible to transfer files among the USRP using the SSH transfers as follows:

````Text
cd data_rx
scp -r file_tx.txt user@192.168.200.2:
````

# OFDM data transmission #

In this example will be show how to transmit and receive OFMD-modulated data packets using GNU-Radio's built-in building blocks. Therefore, the 


The importance of this example relies on understanding the interaction between functional blocks to perform signal processing operations. By adjusting the internal parameters of each block
based on the requirements of the application, in this case an OFDM transreceiver, the design
becomes trivial.


In the GNURadio/GNURadio_OFDM, you can find two directories: one for OFDM transmitter, and the other for the receiver. Inside each directory, you can find a text file. The transmitter directory contains the file with a message to be transmitted. Similarly, in the receiver,
we set a file to write the message obtained after the reception of the OFDM symbols.

# Configuration

Open the GNURadio SDK by typing:

````Text
gnuradio-companion
````

Then, open the transmitter and the receiver files in the gnuradio_tx and the gnuradio_rx directories. The default configuration was set to transmit constantly the same message stored in

