# coding:utf-8

import cv2
import numpy as np

import socket
import sys
import os
import time
import struct

if __name__ == "__main__":
    server_address = './uds_socket'
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(server_address)
    except socket.error as msg:
        print(msg)
        sys.exit(1)
    imgs_path = './pedes_images'
    img_names = sorted(os.listdir(imgs_path))
    img_paths = [os.path.join(imgs_path, img_name) for img_name in img_names]
    for img_name in img_paths:
        img = cv2.imread(img_name)
        img = cv2.resize(img, (608, 608))
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 100]
        result, encimg = cv2.imencode('.jpg', img, encode_param)
        encimg = encimg.tobytes()
        sock.sendall(struct.pack('>L', len(encimg)) + encimg)
        print(len(encimg) + 4)
        time.sleep(2)
            
