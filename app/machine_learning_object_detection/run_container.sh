#!/bin/bash
#
# About: Used by development/debugging
#

sudo docker run --rm -it \
    -v $(pwd)/pedestrain.jpg:/app/yolov2/pedestrain.jpg \
    -v $(pwd)/preprocessor.py:/app/yolov2/preprocessor.py \
    -v $(pwd)/server.py:/app/yolov2/server.py \
    yolov2 bash
