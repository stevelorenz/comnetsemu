FROM ubuntu:18.04

RUN \
    apt-get update --fix-missing && \
    apt-get install -y curl make  && \
    apt-get install -y gcc  && \
    apt-get install -y tzdata  && \
    apt-get install -y net-tools iproute2 iputils-ping && \
    apt-get install -y iperf iperf3 telnet netcat apt-utils && \

    add-apt-repository ppa:ettusresearch/uhd && \
    apt-get install -y update && \
    apt-get install -y install libuhd-dev libuhd003 uhd-host \


WORKDIR /home
RUN mkdir GNURadio-Files
WORKDIR /home/GNURadio-Files
ADD tx_ofdm.py /home/GNURadio-Files
ADD rx_ofdm.py /home/GNURadio-Files
#CMD python /tx_ofdm.py
#CMD python /rx_ofdm.py



