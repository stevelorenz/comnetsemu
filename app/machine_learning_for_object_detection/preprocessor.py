#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: YOLOv2 preprocessor

TODO: Add and polish docstrings and comments
"""

import argparse
import copy
import math
import socket
import struct
import sys
import time

import cv2
import numpy as np

import tensorflow as tf
from utils.imgutils import feature_maps_to_image

MTU = 1500


class CompressorObj(object):
    def __init__(self):
        pass

    def jpeg_enc(self, feature_maps, quality):
        """
        feature_maps: output tensor of feature maps in shape (1, 78, 78, 128)
        quality: quality of JPEG lossy compression from 0 - 100
        return: sliced image of feature maps, pixel from 0 - 255
        """
        shape = (8, 16)
        fmap_images_with_info = feature_maps_to_image(
            feature_maps, shape, is_display=0, is_save=0)
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        result, encimg = cv2.imencode(
            '.jpg', fmap_images_with_info[0][0], encode_param)
        self.compressed_mem = len(encimg)
        # print(len(encimg), "length of encoded image")
        res = (encimg, fmap_images_with_info[0][1])
        return res

    def webp_enc(self, x, quality):
        shape = (8, 16)
        data = copy.copy(x)
        fmap_images_with_info = feature_maps_to_image(
            data, shape, is_display=0, is_save=0)
        encode_param = [int(cv2.IMWRITE_WEBP_QUALITY), quality]
        result, encimg = cv2.imencode(
            '.webp', fmap_images_with_info[0][0], encode_param)
        self.compressed_mem = len(encimg)
        print(len(encimg), "length of encoded image")
        res = (encimg, fmap_images_with_info[0][1])
        return res


class Preprocessor(object):
    def __init__(self):
        # tensorflow graph
        self.__model_path = './model/part1.pb'
        self.__name = 'part1'
        self.__input_tensor_name = 'input:0'
        self.__output_tensor_name = 'Pad_5:0'
        self.sess = self._read_model(
            self.__model_path, self.__name, is_onecore=False)
        self.input1 = self.sess.graph.get_tensor_by_name(
            '{}/{}'.format(self.__name, self.__input_tensor_name))
        self.output1 = self.sess.graph.get_tensor_by_name(
            '{}/{}'.format(self.__name, self.__output_tensor_name))
        # compression object
        self.compressor = CompressorObj()
        self.buffer = bytearray(10000000)
        # meta data
        self.shape = (1, 78, 78, 128)
        self.batch_size = self.shape[0]
        self.w = self.shape[1]
        self.h = self.shape[2]
        self.channels = self.shape[3]
        self.dtype_header = np.float16
        self.dtype_payload = np.uint8
        self.payload_length = self.batch_size * 78 * 78 * 128
        self.header_length = self.batch_size * 2 * 2 + 1
        self.header = bytes(self.header_length)
        self.payload = bytes(self.payload_length)
        self.results = bytes(self.header_length+self.payload_length)

    def __setitem__(self, k, v):
        self.k = v

    def _read_model(self, path, name, is_onecore=True):
        """
        path: the location of pb file path
        name: name of tf graph
        return: tf.Session()
        """
        sess = tf.Session()
        # use one cpu core
        if is_onecore:
            session_conf = tf.ConfigProto(
                intra_op_parallelism_threads=1,
                inter_op_parallelism_threads=1)
            sess = tf.Session(config=session_conf)

        mode = 'rb'
        with tf.gfile.FastGFile(path, mode) as f:
            graph_def = tf.GraphDef()
            graph_def.ParseFromString(f.read())
            sess.graph.as_default()
            tf.import_graph_def(graph_def, name=name)
        return sess

    def read_img_jpeg_bytes(self, img_path):
        img = cv2.imread(img_path)
        img = cv2.resize(img, (608, 608))
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 100]
        _, encimg = cv2.imencode('.jpg', img, encode_param)
        encimg = encimg.tobytes()
        return encimg

    def preprocess_image(self, image, image_size=(608, 608)):
        image_cp = np.copy(image).astype(np.float32)
        # resize image
        image_rgb = cv2.cvtColor(image_cp, cv2.COLOR_BGR2RGB)
        image_resized = cv2.resize(image_rgb, image_size)
        # normalize
        image_normalized = image_resized.astype(np.float32) / 225.0
        # expand dimension
        image_expanded = np.expand_dims(image_normalized, axis=0)
        return image_expanded

    def inference(self, mode, img_bytes, info):
        """
        mode: 0:jpeg 1:webp
        img: bytes array of image
        return: info payload in bytes
        """
        data = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(data, 1)
        img_preprossed = self.preprocess_image(img)
        feature_maps = self.sess.run(self.output1, feed_dict={
                                     self.input1: img_preprossed})
        h_1 = bytes([self.batch_size])
        h_2 = bytes([mode])
        header_tmp = b''
        payload_tmp = b''
        res_bytes = b''
        if mode == 0 or mode == 1:
            quality = info
            if mode == 0:
                fmaps_bytes_with_info = self.compressor.jpeg_enc(
                    feature_maps, quality)
            if mode == 1:
                fmaps_bytes_with_info = self.compressor.webp_enc(
                    feature_maps, quality)
            fmaps_data = fmaps_bytes_with_info[0]
            header_tmp += np.array(fmaps_bytes_with_info[1],
                                   dtype=self.dtype_header).tobytes()
            payload_tmp += np.array(fmaps_data,
                                    dtype=self.dtype_payload).tobytes()
            l1 = struct.pack('<H', len(header_tmp))
            lp = struct.pack('>I', len(payload_tmp))
            res_bytes = h_1 + h_2 + l1 + lp + header_tmp + payload_tmp

        return res_bytes


def test_preprocessor_local():
    preprocessor = Preprocessor()
    img_bytes = preprocessor.read_img_jpeg_bytes("./pedestrain.jpg")
    start = time.time()
    # Use JPEG compression
    res_bytes = preprocessor.inference(0, img_bytes, 70)
    # Use WebP compression
    # res_bytes = preprocessor.inference(1, img_bytes, 70)
    dur = time.time() - start
    print("-" * 30 + "\n" + "YOLOv2 Preprocessor\n" + "-" * 30)
    pack_num_before = math.ceil(len(img_bytes) / MTU)
    pack_num_after = math.ceil(len(res_bytes) / MTU)

    print("Duration of preprocessing: {:.2f} ms".format(dur * 1000.0))
    print("MTU size: {} bytes".format(MTU))
    print("Number of packets to send before preprocessing:{}, size: {} bytes".format(
        pack_num_before, len(img_bytes))
    )
    print("Number of packets to send after preprocessing: {}, size: {} bytes".format(
        pack_num_after, len(res_bytes)))

    with open("./middle_results.bin", "wb+") as f:
        f.write(res_bytes)


class Client(object):
    """UDP client"""

    def __init__(self, mode):
        self.mode = mode
        self.server_addr = ("10.0.0.21", 9999)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("10.0.0.11", 9999))
        self.preprocessor = Preprocessor()

    def gen_data_arr(self, path):
        data_arr = list()
        img_bytes = self.preprocessor.read_img_jpeg_bytes(path)
        if self.mode == 1:
            img_bytes = self.preprocessor.inference(0, img_bytes, 70)
        bs = MTU - 500  # block size
        num = math.ceil(len(img_bytes)/bs)
        print("Data size: {} bytes, number of UDP datagrams: {}".format(
            len(img_bytes), num
        ))
        data_arr = [img_bytes[i*bs:(i+1)*bs] for i in range(num)]

        return data_arr

    def send_data(self, data_arr):
        self.sock.sendto(
            struct.pack(">BH", self.mode, len(data_arr)), self.server_addr)
        time.sleep(0.5)
        for data in data_arr:
            self.sock.sendto(data, self.server_addr)

    def recv_resp(self, timeout=10):
        """Receive server's response with timeout"""
        self.sock.settimeout(timeout)
        try:
            resp, addr = self.sock.recvfrom(MTU)
        except socket.timeout:
            return False
        else:
            return resp.decode()

    def run(self, max_delay=5):
        start = time.time()
        data_arr = self.gen_data_arr("./pedestrain.jpg")
        self.send_data(data_arr)
        proc_delay = time.time() - start
        recv_timeout = max_delay - proc_delay
        print("*** Processing delay: {:.2f} s, receive timeout:{:.2f} s".format(
            proc_delay, recv_timeout
        ))
        resp = self.recv_resp(recv_timeout)
        if resp:
            print("*** Get response from server, response: {}".format(resp))
        else:
            print("*** Failed to get response from server.")

        dur = time.time() - start
        print("*** Total time used: {:.2f} s".format(dur))

    def cleanup(self):
        self.sock.close()


def main():
    parser = argparse.ArgumentParser(
        description='Client with YOLOv2 preprocessor')
    parser.add_argument('mode', type=int, choices=[0, 1],
                        help="Run mode. 0: Send raw image data. "
                        "1: Send preprocessed data.")
    parser.add_argument('--test', action="store_true",
                        help="[DEV] Test preprocessor locally.")

    args = parser.parse_args()
    if args.test:
        test_preprocessor_local()
        sys.exit(0)

    mode_desp = {
        0: "Send original raw image data in bytes",
        1: "Send preprocessed image data in bytes"
    }
    print("*** Run client in mode {}: {}".format(args.mode,
                                                 mode_desp[args.mode]))

    client = Client(args.mode)
    try:
        client.run(15)
    except KeyboardInterrupt:
        print("Client exists.")
        sys.exit(1)
    finally:
        client.cleanup()


if __name__ == "__main__":
    main()
