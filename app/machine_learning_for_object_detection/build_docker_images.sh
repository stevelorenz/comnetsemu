#! /bin/bash

echo "[WARN] The built YOLOv2 image is large (around 5GB). Are you sure to build the image? ([y]/n)"
read -r -n 1
if [[ ! $REPLY ]] || [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Build docker images for YOLOv2 object detection..."
    # --squash: Squash newly built layers into a single new layer
    # Used to reduce built image size.
    docker build --squash -t yolov2:latest --file ./Dockerfile.yolov2 .
fi
