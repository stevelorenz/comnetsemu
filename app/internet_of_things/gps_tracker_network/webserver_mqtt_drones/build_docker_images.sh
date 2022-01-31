#!/bin/bash

echo "Downloading the base docker image for the MQTT broker."
docker pull eclipse-mosquitto

echo "Building a custom docker image with a different conf file for the MQTT broker."
docker build -t broker_mqtt_broker --file ./Dockerfile.mqtt .

echo "Building a docker image for the drone MQTT client."
docker build -t drone_mqtt_client --file ./Dockerfile.drone .

echo "Building a docker image for the my dev server image."
docker build -t server --file ./Dockerfile.webserver .

echo "Building a docker image for the my dev client image."
docker build -t client --file ./Dockerfile.client .

echo "Building dev_test image"
docker build -t dev_test --file ./Dockerfile.dev_test .
