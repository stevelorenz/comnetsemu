FROM ubuntu:18.04

RUN \
    apt-get update --fix-missing && \
    apt-get install -y curl make  && \
    apt-get install -y gcc software-properties-common && \
    apt-get install -y tzdata  && \
    apt-get install -y net-tools iproute2 iputils-ping && \
    apt-get install -y iperf iperf3 telnet netcat apt-utils && \
    add-apt-repository ppa:ettusresearch/uhd && \
    apt-get update && \
    apt-get install -y libuhd-dev libuhd003 uhd-host

RUN \
    apt-get install -y 	cmake git g++ libboost-all-dev python-dev python-mako \
			python-numpy python-wxgtk3.0 python-sphinx python-cheetah swig libzmq3-dev \
			libfftw3-dev libgsl-dev libcppunit-dev doxygen libcomedi-dev libqt4-opengl-dev \
			python-qt4 libqwt-dev libsdl1.2-dev libusb-1.0-0-dev python-gtk2 python-lxml \
			pkg-config python-sip-dev

#Installation of GNU-Radio
WORKDIR /home
RUN mkdir workarea-gnuradio
RUN cd workarea-gnuradio
WORKDIR /home/workarea-gnuradio
RUN git clone --recursive https://github.com/gnuradio/gnuradio
RUN cd gnuradio
WORKDIR /home/workarea-gnuradio/gnuradio
RUN git checkout maint-3.7
RUN git submodule update --init --recursive

RUN mkdir build && cd build
WORKDIR /home/workarea-gnuradio/gnuradio/build

RUN cmake ../
RUN make -j2
RUN make install
RUN ldconfig

WORKDIR /etc/security/
RUN echo "@GROUP    - rtprio    99" >> limits.conf

WORKDIR /home
RUN mkdir GNURadio-Files
CMD /bin/bash

WORKDIR /home/GNURadio-Files
