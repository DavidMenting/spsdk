#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2020-2023 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Tests for `ifr` application."""

import filecmp
import os

import pytest
from click.testing import CliRunner

from spsdk.apps import ifr


@pytest.mark.parametrize(
    "family",
    [
        ("kw45xx"),
        ("k32w1xx"),
    ],
)
def test_ifr_user_config(tmpdir, family):
    """Test IF CLI - Generation IF user config."""
    cmd = ["get-template", "-f", family, "--output", f"{tmpdir}/ifr.yml"]
    runner = CliRunner()
    result = runner.invoke(ifr.main, cmd)
    assert result.exit_code == 0, result.output
    assert os.path.isfile(f"{tmpdir}/ifr.yml")


def test_roundtrip(data_dir, tmpdir):
    parse_cmd = [
        "parse-binary",
        "-f",
        "kw45xx",
        "--binary",
        f"{data_dir}/ref.bin",
        "--output",
        f"{tmpdir}/ref.yaml",
    ]
    runner = CliRunner()
    result = runner.invoke(ifr.main, parse_cmd)
    assert result.exit_code == 0

    generate_cmd = f"generate-binary -f kw45xx --config {tmpdir}/ref.yaml --output {tmpdir}/new.bin"
    result = runner.invoke(ifr.main, generate_cmd.split())
    assert result.exit_code == 0

    assert filecmp.cmp(f"{data_dir}/ref.bin", f"{tmpdir}/new.bin")
