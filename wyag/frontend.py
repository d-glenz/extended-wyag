from typing import Any, Optional

from wyag.base import zlib_read
from wyag.repository import repo_file, GitRepository
from wyag.objects import object_find, Sha
from wyag.objects import GitObject, GitCommit, GitBlob, GitTag
from wyag.trees import GitTree


def generic_object_read(repo: GitRepository, sha: Sha) -> GitObject:
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

    # Pick constructor
    if fmt == b'commit':
        return GitCommit(repo, raw[y+1:])
    elif fmt == b'tree':
        return GitTree(repo, raw[y+1:])
    elif fmt == b'tag':
        return GitTag(repo, raw[y+1:])
    elif fmt == b'blob':
        return GitBlob(repo, raw[y+1:])
    else:
        raise ValueError(f"Unknown type {fmt.decode('ascii')} for object {sha}")


# TODO: function name inconsistent
def cat_file(repo: GitRepository, obj: Any, fmt: Optional[bytes] = None) -> None:
    obj = object_find(repo, obj, fmt=fmt)
    obj_content = generic_object_read(repo, obj)
    print(obj_content.pretty_print())
