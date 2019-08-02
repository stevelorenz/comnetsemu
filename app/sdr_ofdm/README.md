
# Data transmission using Ettus Research USRP #
In this directory, you can find two examples that show the functionality of USRP systems in real
data trasmission applications. Before being enable to exchange data between 2 SDR systems, it is
required the installation of the UHD driver, which ensure the communication between the host computer and the USRP, GNURadio, which is free and open-source SDK employed to implement software
radio transceivers through built-in C++ signal processing blocks. GNU Radio supports a large set of
platforms, but for the purpose of this chapter the development platform is the Ettus Research N210.

The details about the installation of the UHD drivers and the GNU can be found in the following link: 
https://kb.ettus.com/Building_and_Installing_the_USRP_Open-Source_Toolchain_(UHD_and_GNU_Radio)_on_Linux

# OFMD Tunnel #
The first application is an example about OFDM tunnel between two USRP connected to different
host computers, as depicted.
#Description of the setup
````Text

------------------                           ------------------- 
| HOST A | SDR A |  ---- OFDM tunnel  ----  | SDR B | HOST B |
------------------                           ------------------- 
````
An OFDM tunnel is basically a link between two 
This example


# OFDM data transmission#
