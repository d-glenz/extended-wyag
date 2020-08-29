import hashlib
import sys
from typing import Any, Optional, BinaryIO
import zlib

from wyag.repository import GitRepository, repo_file


class GitObject:
    def __init__(self, repo: GitRepository, data: Any = None) -> None:
        self.repo = repo
        self.fmt: bytes = b""
        if data is not None:
            self.deserialize(data)

    def serialize(self) -> Any:
        """This function MUST be implemented by a subclass. It must read the object's
           contents from self.data, a byte string, and do whatever it takes to convert
           it into a meaningful representation. What exactly that means depends on
           each subclass."""
        raise NotImplementedError("Unimplemented method serialize")

    def deserialize(self, data: Any) -> None:
        raise NotImplementedError("Unimplemented method serialize")


class GitBlob(GitObject):
    def __init__(self, repo: GitRepository, data: Any = None) -> None:
        self.fmt = b'blob'
        self.blobdata = None
        super(GitBlob, self).__init__(repo, data)

    def serialize(self) -> Any:
        return self.blobdata

    def deserialize(self, data: Any) -> None:
        self.blobdata = data


def object_read(repo: GitRepository, sha: str) -> GitObject:
    """Read object object_id from Git repository repo. Return a GitObject whose exact
       type depends on the object"""
    path = repo_file(repo, "objects", sha[0:2], sha[2:])

    if path is None:
        ValueError(f"Path {path} for object {sha} could not be found")

    with open(str(path), "rb") as f:
        raw = zlib.decompress(f.read())

        # Read object type
        x = raw.find(b' ')
        fmt = raw[0:x]

        # Read and validate object size
        y = raw.find(b'\x00', x)
        size = int(raw[x:y].decode("ascii"))
        if size != len(raw) - y - 1:
            raise ValueError(f"Malformed object {sha}: bad length")

        # Pick constructor
        # if fmt == b'commit':
        #     c = GitCommit
        # elif fmt == b'tree':
        #     c = GitTree
        # elif fmt == b'tag':
        #     c = GitTag
        if fmt == b'blob':
            c = GitBlob
        else:
            raise ValueError(f"Unknown type {fmt.decode('ascii')} for object {sha}")

        return c(repo, raw[y+1:])


def object_find(repo: GitRepository, name: str, fmt: Optional[str] = None, follow: bool = True) -> str:
    """Will resolve objects by full hash, short hash, tags, ..."""
    return name


def object_write(obj: GitObject, actually_write: bool = True) -> str:
    # Serialize object data
    data = obj.serialize()

    # Add header
    result = obj.fmt + b' ' + str(len(data)).encode() + b'\x00' + data

    # Compute hash
    sha = hashlib.sha1(result).hexdigest()

    if actually_write:
        # Compute path
        path = repo_file(obj.repo, "objects", sha[0:2], sha[2:], mkdir=True)

        with open(str(path), "wb") as f:
            # Compress and write
            f.write(zlib.compress(result))

    return sha


# TODO: function name inconsistent
def cat_file(repo: GitRepository, obj: Any, fmt: Optional[str] = None) -> None:
    obj = object_read(repo, object_find(repo, obj, fmt=fmt))
    sys.stdout.buffer.write(obj.serialize())


def object_hash(fd: BinaryIO, fmt: bytes, repo: Optional[GitRepository] = None) -> str:
    data = fd.read()

    if repo is None:
        raise ValueError("repo is None")
    # Choose constructor depending on
    # object type found in header
    # if fmt == b'commit':
    #     obj = GitCommit(repo, data)
    # elif fmt == b'tree':
    #     obj = GitTree(repo, data)
    # elif fmt == b'tag':
    #     obj = GitTag(repo, data)
    if fmt == b'blob':
        obj = GitBlob(repo, data)
    else:
        raise ValueError(f"Unknown type {fmt!s}!")

    return object_write(obj, True)
