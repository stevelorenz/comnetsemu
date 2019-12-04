#! /bin/bash

echo "[WARN] The built YOLOv2 image is large (around 9GB). Are you sure to build the image? ([y]/n)"
read -r -n 1;
if [[ ! $REPLY ]] || [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Build docker images for YOLOv2 object detection..."
    sudo docker build -t yolov2:latest --file ./Dockerfile.yolov2 .
fi
