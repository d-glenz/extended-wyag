import collections
import hashlib
import pathlib
import re
from typing import Any, Optional, Dict, List
import zlib

from wyag.base import GitObjectTypeError, zlib_read, Sha
from wyag.repository import GitRepository, repo_file, repo_dir


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


def object_resolve(repo: GitRepository, name: str) -> List[str]:
    """Resolve name to an object hash in repo.

       This function is aware of:
        - the HEAD literal
        - short and long hashes
        - tags
        - branches
        - remote branches"""

    candidates = []
    hashRE = re.compile(r"^[0-9A-Fa-f]{40}$")
    smallHashRE = re.compile(r"^[0-9A-Fa-f]{4,40}$")

    # Empty string? Abort.
    if not name.strip():
        return []

    if name == "HEAD":
        return [ref_resolve(repo, "HEAD")]

    if hashRE.match(name):
        # This is a complete hash
        return [name.lower()]
    elif smallHashRE.match(name):
        # This is a small hash. 4 seems to be the minimal length for git to
        # consider something a short hash. This limit is documented in man
        # git-rev-parse
        name = name.lower()
        prefix = name[:2]
        path = repo_dir(repo, "objects", prefix, mkdir=False)
        if path:
            rem = name[2:]
            for f in path.iterdir():
                if str(f).startswith(rem):
                    candidates.append(prefix + str(f))

    # search for branches and tags (with or without "refs" and "heads" or "tags" prefixes)
    for ref_path in [f'refs/heads/{name}', f'refs/tags/{name}', f'refs/{name}', name]:
        ref = repo_file(repo, ref_path)
        assert ref is not None
        if ref.exists():
            candidates.append(ref_resolve(repo, ref_path))

    return candidates


def ref_create(repo: GitRepository, ref_name: str, sha: str) -> None:
    with open(str(repo_file(repo, "refs/" + ref_name)), "w") as fp:
        fp.write(sha + '\n')


def ref_resolve(repo: GitRepository, ref: str) -> str:
    with open(str(repo_file(repo, ref)), 'r') as fp:
        data = fp.read()[:-1]  # .trim()

    if data.startswith("ref: "):
        return ref_resolve(repo, data[5:])

    return data


def ref_list(repo: GitRepository, path: str = None) -> Dict[str, Any]:
    if not path:
        rpath = repo_dir(repo, "refs")
    else:
        rpath = pathlib.Path(path)

    assert rpath is not None

    ret = collections.OrderedDict()
    # Git shows refs sorted. To do the same, we use and OrderedDict
    # and sort the output of listdir
    for f in sorted(rpath.iterdir()):
        can = rpath / f
        if can.is_dir():
            ret[str(f)] = ref_list(repo, str(can))
        else:
            ret[str(f)] = ref_resolve(repo, str(can))  # type: ignore

    return ret
