#
# Dockerfile for NC encoder
#

# Pull base image.
FROM jupyter/scipy-notebook:82d1d0bf0867

# Install KODO python
USER root

# Copy the notebooks
COPY ./notebooks /home/jovyan/notebooks
COPY ./kodo.so /home/jovyan/notebooks/kodo.so
RUN chown -R jovyan /home/jovyan/notebooks
RUN chmod -R 700 /home/jovyan/notebooks

# We need to downgrade python to 3.6.8 because
# thats the version in the vagrant VM
RUN conda install --yes \
    'python=3.6.8'


USER $NB_UID
