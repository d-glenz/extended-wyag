import hashlib
from typing import Any, Optional
import zlib

from wyag.base import GitObjectTypeError, zlib_read, Sha
from wyag.repository import GitRepository, repo_file


class GitObject:
    def __init__(self, repo: Optional[GitRepository], fmt: bytes, data: Any = None) -> None:
        self.repo = repo
        self.fmt: bytes = fmt
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

    def pretty_print(self) -> str:
        raise NotImplementedError("Unimplemented method pretty_print")


class GitBlob(GitObject):
    def __init__(self, repo: Optional[GitRepository], data: Any = None) -> None:
        super(GitBlob, self).__init__(repo, b'blob', data)

    def serialize(self) -> Any:
        return self.blobdata

    def pretty_print(self) -> Any:
        return self.blobdata.decode()

    def deserialize(self, data: Any) -> None:
        self.blobdata = data


def blob_read(repo: GitRepository, sha: Sha) -> GitBlob:
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

    return GitBlob(repo, raw[y+1:])


def object_get_type(repo: GitRepository, sha: Sha) -> bytes:
    """Read object object_id from Git repository repo. Return a GitObject whose exact
       type depends on the object"""
    path = repo_file(repo, "objects", sha[0:2], sha[2:])
    assert path is not None, f"Path {path} for object {sha} could not be found"

    raw = zlib_read(path)

    # Read object type
    x = raw.find(b' ')
    return raw[0:x]


def object_write(obj: GitObject, actually_write: bool = True) -> str:
    # Serialize object data
    data = obj.serialize()

    # Add header
    result = obj.fmt + b' ' + str(len(data)).encode() + b'\x00' + data

    # Compute hash
    sha = hashlib.sha1(result).hexdigest()

    if actually_write:
        if obj.repo is None:
            raise ValueError("repo is None on actually_write in object_write")
        # Compute path
        path = repo_file(obj.repo, "objects", sha[0:2], sha[2:], mkdir=True)

        with open(str(path), "wb") as f:
            # Compress and write
            f.write(zlib.compress(result))

    return sha
