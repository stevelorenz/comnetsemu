#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Build all test and example images
"""

import sys
import time

from collections import OrderedDict

import docker

IMAGES = OrderedDict({"dev_test:latest": "./Dockerfile.dev_test"})


def colored(r, g, b, text):
    return "\033[38;2;{};{};{}m{} \033[38;2;255;255;255m".format(r, g, b, text)


def perror(text):
    print(colored(255, 0, 0, text), file=sys.stderr)


def build_image(client, tag, dockerfile, retry):
    for _ in range(retry):
        try:
            client.images.build(
                tag=tag,
                path="./",
                dockerfile=dockerfile,
                rm=True,
            )
            return True
        except (docker.errors.APIError, docker.errors.BuildError):
            time.sleep(5)
            continue
    else:
        return False


def main():
    print("*** Build minimal test images.")
    client = docker.from_env()
    retry = 3

    for tag, dockerfile in IMAGES.items():
        print(f"- Build image with tag: {tag}, Dockerfile path: {dockerfile}")
        ret = build_image(client, tag, dockerfile, retry)
        if not ret:
            perror(
                f"""Failed to build the image with {retry} times.
This may be due to the Dockerhub image server unavailability or other network issues.
Please try to rebuild the image after checking your network connection and the access to the Dockerhub"""
            )

    print("- Delete all unused images to save disk space.")
    client.images.prune()


if __name__ == "__main__":
    main()
