#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: YOLOv2 Server
"""

import argparse
import os
import socket
import struct
import sys
import json
import time

import cv2
import numpy as np

import tensorflow as tf
from utils.config import class_names, anchors
from utils.imgutils import image_to_feature_maps, decode_result, postprocess

MTU = 1500


class Detector(object):
    """YOLOv2 Object Detector"""

    def __init__(self, mode="preprocessed"):
        self._name = "yolo"
        self._model_path = "./model/yolo.pb"

        self._mode = mode
        if mode == "preprocessed":
            self._input_tensor_name = "Pad_5:0"
            self._output_tensor_name = "output:0"
        elif mode == "raw":
            self._input_tensor_name = "input:0"
            self._output_tensor_name = "output:0"
        else:
            raise RuntimeError("Invalid server mode, modes: preprocessed, raw.")

        self.dtype_header = np.float16
        self.dtype_payload = np.uint8
        self.shape_splice = (8, 16)

        self.sess = self._read_model(self._model_path, self._name, is_onecore=False)
        self._init_tensors(self._input_tensor_name, self._output_tensor_name)

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
                intra_op_parallelism_threads=1, inter_op_parallelism_threads=1
            )
            sess = tf.Session(config=session_conf)

        mode = "rb"
        with tf.gfile.FastGFile(path, mode) as f:
            graph_def = tf.GraphDef()
            graph_def.ParseFromString(f.read())
            sess.graph.as_default()
            tf.import_graph_def(graph_def, name=name)
        return sess

    def _init_tensors(self, input_tensor_name, output_tensor_name):
        self.input1 = self.sess.graph.get_tensor_by_name(
            "{}/{}".format(self._name, input_tensor_name)
        )
        self.output1 = self.sess.graph.get_tensor_by_name(
            "{}/{}".format(self._name, output_tensor_name)
        )

    def _read_img_jpeg_bytes(self, img_path):
        img = cv2.imread(img_path)
        img = cv2.resize(img, (608, 608))
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 100]
        _, encimg = cv2.imencode(".jpg", img, encode_param)
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

    def inference_preprocessed(self, data):
        """
        @header: (first 8 bytes are header)
        h_1: batch size (1 bytes)
        h_2: mode (0: JPEG  1: WebP) (1 bytes)
        l1: length feature maps info header (maximal and mininal values of the feature maps) (2 bytes)
        lp: length of payload (encoded feature maps) (4 bytes)
        @data
        header_tmp: feature maps info header
        payload_tmp: encoded feature maps
        """
        # header parsing
        h_1 = data[0]
        h_2 = data[1]
        l1 = struct.unpack("<H", data[2:4])[0]
        lp = struct.unpack(">I", data[4:8])[0]
        header_tmp = np.frombuffer(data[8 : 8 + l1], self.dtype_header)
        payload_tmp = np.frombuffer(data[8 + l1 :], self.dtype_payload)
        # predict
        codec = "jpg" if h_2 == 0 else "webp"
        feature_maps = image_to_feature_maps(
            [(payload_tmp, header_tmp)], self.shape_splice
        )
        res = self.sess.run(self.output1, feed_dict={self.input1: feature_maps})
        bboxes, obj_probs, class_probs = decode_result(
            model_output=res,
            output_sizes=(608 // 32, 608 // 32),
            num_class=len(class_names),
            anchors=anchors,
        )
        # image_shape: original image size for displaying
        bboxes, scores, class_max_index = postprocess(
            bboxes, obj_probs, class_probs, image_shape=(432, 320)
        )

        return bboxes, scores, class_max_index, class_names

    def inference_raw(self, data):
        """Inference the raw image data in bytes"""
        data = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(data, 1)
        img_preprossed = self.preprocess_image(img)
        res = self.sess.run(self.output1, feed_dict={self.input1: img_preprossed})
        bboxes, obj_probs, class_probs = decode_result(
            model_output=res,
            output_sizes=(608 // 32, 608 // 32),
            num_class=len(class_names),
            anchors=anchors,
        )
        bboxes, scores, class_max_index = postprocess(
            bboxes, obj_probs, class_probs, image_shape=(432, 320)
        )

        return bboxes, scores, class_max_index, class_names

    def inference(self, data):

        if self._mode == "preprocessed":
            ret = self.inference_preprocessed(data)
            return ret
        elif self._mode == "raw":
            ret = self.inference_raw(data)
            return ret

    def get_detection_results(
        self, bboxes, scores, class_max_index, class_names, thr=0.3
    ):
        results = list()
        for i, box in enumerate(bboxes):
            if scores[i] < thr:
                continue
            cls_indx = class_max_index[i]
            r = {
                "object": class_names[cls_indx],
                "score": float(scores[i]),
                "position": (int(box[0]), int(box[1]), int(box[2]), int(box[3])),
            }
            results.append(r)
        results = json.dumps(results)
        return results


def test_detector_local():
    """Test the functionality of detector with local image"""
    print("*** Test raw mode:")
    detector = Detector(mode="raw")
    img_bytes = detector._read_img_jpeg_bytes("./pedestrain.jpg")
    print("The size of original image: {} bytes".format(len(img_bytes)))
    start = time.time()
    ret = detector.inference(img_bytes)
    dur = time.time() - start
    print("Duration of detection for raw image: {} s".format(dur))
    results = detector.get_detection_results(*ret)
    print(results)

    if os.path.exists("./middle_results.bin"):
        print("*** Test preprocessed mode:")
        detector = Detector(mode="preprocessed")
        with open("./middle_results.bin", "rb") as f:
            data = f.read()
        start = time.time()
        ret = detector.inference(data)
        dur = time.time() - start
        print("Duration of detection for preprocessed image: {} s".format(dur))
        results = detector.get_detection_results(*ret)
        print(results)
    else:
        print("Can not find ./middle_results.bin.")
        print(
            "Run '$ python ./preprocessor.py 0 --test' to generate middle_results.bin"
        )


class Server(object):
    """UDP server"""

    def __init__(self):
        self.client_addr = ("10.0.0.11", 9999)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("10.0.0.21", 9999))
        self.detector = None

    def send_resp(self, resp):
        self.sock.sendto(resp.encode(), self.client_addr)

    def get_resp(self, mode, data):
        if mode == 0:
            self.detector = Detector(mode="raw")
            ret = self.detector.inference(data)
            results = self.detector.get_detection_results(*ret)
            return results
        elif mode == 1:
            self.detector = Detector(mode="preprocessed")
            ret = self.detector.inference(data)
            results = self.detector.get_detection_results(*ret)
            return results

    def get_data(self, timeout=5):
        blocks = list()
        self.sock.settimeout(None)
        meta_data, _ = self.sock.recvfrom(MTU)
        mode, num = struct.unpack(">BH", meta_data)
        print("*** Client mode: {}, number of datagrams: {}".format(mode, num))
        self.sock.settimeout(timeout)
        for _ in range(num):
            try:
                block, _ = self.sock.recvfrom(MTU)
            except socket.timeout:
                print("Server recv timeout! Exits")
                self.cleanup()
                sys.exit(1)
            blocks.append(block)
        data = b"".join(blocks)

        return mode, data

    def cleanup(self):
        self.sock.close()

    def run(self):
        while True:
            print("*** Wait for data from client.")
            mode, data = self.get_data()
            start = time.time()
            resp = self.get_resp(mode, data)
            proc_delay = time.time() - start
            print("*** Processing delay: {:.2f} s".format(proc_delay))
            print("*** Generated response: {}".format(resp))
            for _ in range(3):
                self.sock.sendto(resp.encode(), self.client_addr)


def main():

    parser = argparse.ArgumentParser(description="YOLOv2 Server")
    parser.add_argument(
        "--test", action="store_true", help="[DEV] Test detector locally"
    )

    args = parser.parse_args()
    if args.test:
        test_detector_local()
        sys.exit(0)

    server = Server()
    try:
        server.run()
    except KeyboardInterrupt:
        print("Server exists.")
        sys.exit(1)
    finally:
        server.cleanup()


if __name__ == "__main__":
    main()
