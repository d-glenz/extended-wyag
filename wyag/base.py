import pathlib
from typing import NewType
import zlib


Sha = NewType('Sha', str)


class GitObjectTypeError(Exception):
    pass


def zlib_read(path: pathlib.Path) -> bytes:
    with open(str(path), "rb") as f:
        return zlib.decompress(f.read())
