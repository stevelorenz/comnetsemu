#
# Dockerfile for NC coders.
#

# The Python version of this image should be the same of the OS that builds the kodo-python.
# Otherwise, Python program for coders can not run inside container.
FROM ubuntu:18.04

RUN apt-get update && \
    apt-get install -y sudo net-tools iproute2 python3 libpython3-dev python3-dev \
    iperf tcpdump

# Add kodo user
RUN useradd -ms /bin/bash kodo
RUN adduser kodo sudo
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
USER kodo
ENV HOME /home/kodo
WORKDIR /home/kodo

USER root
# Copy kodo.so
COPY ./kodo.so /home/kodo/kodo.so
RUN chown kodo:kodo /home/kodo/kodo.so
RUN chmod 700 /home/kodo/kodo.so
# Copy coder apps and add exec
COPY ./common.py /home/kodo/common.py
COPY ./encoder.py /home/kodo/encoder.py
COPY ./decoder.py /home/kodo/decoder.py
COPY ./recoder.py /home/kodo/recoder.py
COPY ./rawsock_helpers.py /home/kodo/rawsock_helpers.py
COPY ./log.py /home/kodo/log.py

RUN chown kodo:kodo /home/kodo/*.py
RUN chmod 700 /home/kodo/*.py

# Avod encoding problem for Python3
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

USER kodo

CMD ["bash"]
