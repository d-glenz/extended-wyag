import io
import pathlib
from typing import Tuple, List, Optional, BinaryIO, Any

from wyag.base import GitObjectTypeError, zlib_read
from wyag.objects import GitObject, object_get_type, Sha, blob_read, object_write
from wyag.repository import GitRepository, repo_find, repo_file
from wyag.index import GitIndexEntry


class GitTreeLeaf:
    def __init__(self, mode: bytes, path: bytes, sha: Sha) -> None:
        self.mode = mode
        self.path = path
        self.sha = sha


class GitTree(GitObject):
    def __init__(self, repo: Optional[GitRepository], data: bytes = None) -> None:
        super(GitTree, self).__init__(repo, b'tree', data)

    def deserialize(self, data: bytes) -> None:
        assert data is not None, "Tree bytes empty"
        self.items = tree_parse(data)

    def serialize(self) -> Any:
        return tree_serialize(self)

    def pretty_print(self) -> str:
        return tree_print(self)


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

    return y+21, GitTreeLeaf(mode, path, Sha(format(int(sha), "040x")))


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
        dest = path / item.path.decode("ascii")
        try:
            tree = tree_read(repo, item.sha)
            dest.mkdir(parents=True)
            tree_checkout(repo, tree, dest)
        except GitObjectTypeError:
            blob = blob_read(repo, item.sha)
            with open(dest, 'wb') as f:
                f.write(blob.blobdata)


def tree_hash(fd: BinaryIO, repo: Optional[GitRepository] = None) -> str:
    data = fd.read()
    return object_write(GitTree(repo, data), repo is not None)


def tree_write(repo: GitRepository, idx: List[GitIndexEntry]) -> str:
    """Write a tree object from the current index entries."""
    tree_entries = []

    for entry in idx:
        assert '/' not in entry.name, "currently only supports a single, top-level directory"

        mode_path = bytes('{:o} {}'.format(entry.mode, entry.name).encode())
        tree_entry = mode_path + b'\x00' + entry.obj.encode()
        tree_entries.append(tree_entry)
    return tree_hash(io.BytesIO(b''.join(tree_entries)), repo)


def tree_print(obj: GitTree) -> str:
    ret = ''
    for i in obj.items:
        try:
            repo = repo_find()
            assert repo is not None
            fmt = object_get_type(repo, i.sha).decode()
        except FileNotFoundError:
            fmt = '????'
        ret += f"{i.mode.decode()} {fmt} {i.sha.zfill(40)}    {i.path.decode()}\n"

    return ret


def tree_read(repo: GitRepository, sha: Sha) -> GitTree:
    """Read object object_id from Git repository repo. Return a GitObject whose exact
       type depends on the object"""
    path = repo_file(repo, "objects", sha[0:2], sha[2:])
    assert path is not None, f"Path {path} for object {sha} could not be found"

    raw = zlib_read(path)

    # Read object type
    x = raw.find(b' ')
    fmt = raw[0:x]

    # Read and validate object size
    y = raw.find(b'\x00', x)
    size = int(raw[x:y].decode("ascii"))
    if size != len(raw) - y - 1:
        raise ValueError(f"Malformed object {sha}: bad length")

    if fmt != b'blob':
        raise GitObjectTypeError(f"Unknown type {fmt.decode('ascii')} for object {sha}")

    return GitTree(repo, raw[y+1:])
