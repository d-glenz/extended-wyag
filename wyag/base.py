import pathlib
import zlib


class GitObjectTypeError(Exception):
    pass


def zlib_read(path: pathlib.Path) -> bytes:
    with open(str(path), "rb") as f:
        return zlib.decompress(f.read())
