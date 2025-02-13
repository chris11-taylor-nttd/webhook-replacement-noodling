import json
import pathlib

import pytest


@pytest.fixture
def test_file():
    def _test_file(path: pathlib.Path) -> dict:
        return path.read_text()

    return _test_file


@pytest.fixture
def test_json(test_file):
    def _test_json(path: pathlib.Path) -> dict:
        return json.loads(test_file(path))

    return _test_json
