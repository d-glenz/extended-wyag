import pathlib
from typing import Tuple, List, Optional

from wyag.objects import GitObject, object_read, GitBlob
from wyag.repository import GitRepository


class GitTreeLeaf:
    def __init__(self, mode: bytes, path: bytes, sha: str) -> None:
        self.mode = mode
        self.path = path
        self.sha = sha


class GitTree(GitObject):
    def __init__(self, repo: Optional[GitRepository], data: bytes = None) -> None:
        assert data is not None, "Tree bytes empty"

        self.items = tree_parse(data)
        super(GitTree, self).__init__(repo, b'tree', data)

    def serialize(self):
        return tree_serialize(self)


def tree_parse_one(raw: bytes, start: int = 0) -> Tuple[int, GitTreeLeaf]:
    # Find the space terminator of the mode
    x = raw.find(b' ', start)
    assert x - start == 5 or x - start == 6

    # Read the mode
    mode = raw[start:x]

    # Find the NULL terminator of the path
    y = raw.find(b'\x00', x)
    # and read the path
    path = raw[x+1:y]

    # Read the SHA and convert to a hex string
    # hex(..) adds 0x in front
    sha = hex(int.from_bytes(raw[y+1:y+21], "big"))[2:]

    return y+21, GitTreeLeaf(mode, path, sha)


def tree_parse(raw: bytes) -> List[GitTreeLeaf]:
    pos = 0
    ret = list()
    while pos < len(raw):
        pos, data = tree_parse_one(raw, pos)
        ret.append(data)

    return ret


def tree_serialize(obj: GitTree) -> bytes:
    # FIXME: Add serializer!
    ret = b''
    for i in obj.items:
        ret += i.mode + b' ' + i.path + b'\x00'
        sha = int(i.sha, 16)
        ret += sha.to_bytes(20, byteorder="big")

    return ret


def tree_checkout(repo: GitRepository, tree: GitTree, path: pathlib.Path) -> None:
    for item in tree.items:
        obj = object_read(repo, item.sha)
        dest = path / item.path.decode("ascii")

        if isinstance(obj, GitTree):
            if obj.fmt == b'tree':
                dest.mkdir(parents=True)
                tree_checkout(repo, obj, dest)
        elif isinstance(obj, GitBlob):
            if obj.fmt == b'blob':
                with open(dest, 'wb') as f:
                    f.write(obj.blobdata)
