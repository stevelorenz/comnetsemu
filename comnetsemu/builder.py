#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""

This module contains wrappers for common builders/compilers involved in network programming.
This helps to avoid remembering complex compiler options and flags.
"""

import pathlib
import subprocess
import shlex
import shutil

from comnetsemu.log import info


class P4Builder:
    """P4 builder for P4 programs.

    :param p4_src: The path of the P4 source code file.
    :type p4_src: str
    :param p4c_bin: The binary name of the P4 compiler.
    :type p4c_bin: str
    :param out_dir: The directory for P4 compiler output files.
    :type out_dir: str
    :param target: The target for P4 compiler.
    :type target: str
    :param arch: The target architecture.
    :type arch: str
    :param std: The P4 language standard.
    :type std: str
    """

    p4runtime_files_extension = "p4info.txt"

    def __init__(
        self,
        p4_src: str,
        p4c_bin: str = "p4c",
        out_dir: str = "./build",
        target: str = "bmv2",
        arch: str = "v1model",
        std: str = "p4-16",
    ) -> None:
        self.p4c_bin = p4c_bin
        self.out_dir = out_dir
        self.out_dir_path = pathlib.Path(out_dir)
        self.target = target
        self.arch = arch
        self.std = std

        p4_src_path = pathlib.Path(p4_src)
        if not p4_src_path.is_file():
            raise FileNotFoundError(f"Can not find the P4 source file: {p4_src}")
        else:
            self.p4_src_path = p4_src_path

        stem = self.p4_src_path.stem
        self.p4_json_out = self.out_dir_path / f"{stem}.json"
        self.p4runtime_files = (
            self.out_dir_path / f"{stem}.{self.p4runtime_files_extension}"
        )

    def build(self, mk_dir=True) -> tuple:
        """Build P4 target files in the out_dir

        :param mk_dir: Create the output directory if it not exists.
        :type mk_dir: bool
        :return: A tuple of two pathlib.Path objects. The first is the path of the generated JSON file. The second is the path of generated P4Runtime information file.
        :rtype: tuple
        """

        if not self.out_dir_path.is_dir():
            if not mk_dir:
                raise FileNotFoundError(
                    f"Can not find the output directory: {self.out_dir_path.as_posix()}"
                )
            else:
                self.out_dir_path.mkdir(exist_ok=True)
                pass

        cmd = "{p4c_bin} --target {target} --arch {arch} --std {std}".format(
            **{
                "p4c_bin": self.p4c_bin,
                "target": self.target,
                "arch": self.arch,
                "std": self.std,
            }
        )

        cmd = " ".join(
            (
                cmd,
                f"--p4runtime-files {self.p4runtime_files}",
                f"-o {self.out_dir_path.as_posix()}",
                f"{self.p4_src_path.as_posix()}",
            )
        )
        info(
            f"Build P4 target files of source: {self.p4_src_path.as_posix()} to output directory: {self.out_dir_path.as_posix()}\n"
        )
        subprocess.run(shlex.split(cmd), check=True)

        return (self.p4_json_out, self.p4runtime_files)

    def clean(self):
        """Remove build directory."""
        info("Remove build output directory: {self.out_dir_path.as_posix()}\n")
        shutil.rmtree(self.out_dir_path.as_posix())


class eBPFBuilder:
    """eBPF compiler"""

    def __init__(cc_bin: str = "clang"):
        pass


class XDPBuilder:
    pass
