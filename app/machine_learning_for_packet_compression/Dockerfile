FROM ubuntu:latest

WORKDIR /root

RUN apt-get update
RUN apt-get install -y git
RUN apt-get install -y wget

RUN wget https://repo.anaconda.com/miniconda/Miniconda3-4.6.14-Linux-x86_64.sh
RUN bash Miniconda3-4.6.14-Linux-x86_64.sh -bf
RUN git clone https://tomoskozi@dev.azure.com/tomoskozi/o2sc/_git/o2sc --depth 1

RUN /root/miniconda3/bin/pip install -r /root/o2sc/requirements.txt
RUN /root/miniconda3/bin/pip install git+https://tomoskozi@dev.azure.com/tomoskozi/o2sc/_git/o2sc


ENTRYPOINT ["/root/miniconda3/bin/python3", "/root/o2sc/emulator/emulator.py"]
