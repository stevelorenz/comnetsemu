FROM ubuntu:latest

WORKDIR /root

RUN apt-get update
RUN apt-get install -y git
RUN apt-get install -y wget
RUN apt-get install -y apt-transport-https
RUN apt-get install -y net-tools
RUN apt-get install -y iputils-ping
RUN apt-get install -y iproute2

RUN wget https://repo.anaconda.com/miniconda/Miniconda3-4.6.14-Linux-x86_64.sh
RUN bash Miniconda3-4.6.14-Linux-x86_64.sh -bf
RUN git clone https://tomoskozi@dev.azure.com/tomoskozi/o2sc/_git/o2sc --depth 1

RUN /root/miniconda3/bin/pip install -r /root/o2sc/requirements.txt
RUN /root/miniconda3/bin/pip install git+https://tomoskozi@dev.azure.com/tomoskozi/o2sc/_git/o2sc

# Set the locale
RUN apt-get install locales -y
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

ENV PATH="/root/miniconda3/bin:${PATH}"

RUN ln -s /root/miniconda3/bin/python3 /root/python3
RUN ln -s /root/o2sc/docker/node.py /root/node.py
#RUN ln -s /root/o2sc/emulator/emulator.py /emulator.py

ENTRYPOINT ["/root/miniconda3/bin/python3", "/root/o2sc/emulator/emulator.py"]
