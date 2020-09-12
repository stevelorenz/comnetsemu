#!/bin/bash

echo "Building drone docker image"
docker build -t drone --file ./Dockerfile.drone .

echo "Pulling MQTT broker docker image"
docker pull eclipse-mosquitto:latest

echo "Building webserver docker image"
docker build -t webserver --file ./Dockerfile.webserver .

echo "Building client docker image"
docker build -t client --file ./Dockerfile.client .