#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Test comnetsemu.builder module
"""

import os
import pathlib
import unittest

import comnetsemu.builder

UNIT_TEST_DIR = os.path.dirname(os.path.abspath(__file__))


class TestP4Builder(unittest.TestCase):
    """TestP4Builder"""

    def test_build_bmv2(self):
        p4_src = os.path.join(UNIT_TEST_DIR, "test.p4")
        p4_builder = comnetsemu.builder.P4Builder(p4_src=p4_src, out_dir="build")
        with self.assertRaises(FileNotFoundError):
            p4_builder.build(mk_dir=False)
        out_dir_path = pathlib.Path("./build")
        json_out, p4runtime_files = p4_builder.build(mk_dir=True)
        assert json_out == out_dir_path / "test.json"
        assert (
            p4runtime_files
            == out_dir_path / f"test.{p4_builder.p4runtime_files_extension}"
        )
        p4_builder.clean()


if __name__ == "__main__":
    unittest.main(verbosity=2)
