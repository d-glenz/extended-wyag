import collections
from typing import Any, Dict, List, Optional

from ewyag.base import Sha, zlib_read, GitObjectTypeError
from ewyag.objects import GitObject
from ewyag.repository import GitRepository, repo_file


def kvlm_parse(raw: bytearray, start: int = 0, dct: Dict[bytes, List[bytes]] = None) -> Dict[bytes, List[bytes]]:
    """Parse "Key-Value List with Message"""
    if not dct:
        # As of python3.7, all dictionaries are insertion-ordered
        dct = collections.OrderedDict()
        # You cannot declare the argument as dct=OrderedDict() or all
        # calls to the function will use the same dictionary (default args are only evaluated
        # on the first run).

    # We search for the next space and the next newline
    spc = raw.find(b' ', start)
    nl = raw.find(b'\n', start)

    # If space appears before newline, we have a keyword

    # Base case
    # =========
    # If newline appears first (or there's no space at all, in which case find returns -1), we
    # assume a blank line. A blank line means the remainder of the data is the message.
    if (spc < 0) or (nl < spc):
        assert nl == start
        dct[b''] = [raw[start+1:]]
        return dct

    # Recursive case
    # ==============
    # we read a key-value pair and recurse for the next.
    key = raw[start:spc]

    # Find the end of the value. Continuation lines begin with a space, so we lop until we find
    # a "\n" followed by a space.
    end = start
    while True:
        end = raw.find(b'\n', end+1)
        if raw[end+1] != ord(' '):
            break

    # Grab the value
    # Also drop the leading space on continuation lines
    value = raw[spc+1:end].replace(b'\n ', b'\n')

    # Don't overwrite existing data contents
    if key in dct:
        dct[key].append(value)
    else:
        dct[key] = [value]

    return kvlm_parse(raw, start=end+1, dct=dct)


def kvlm_serialize(kvlm: Dict[bytes, List[bytes]]) -> bytes:
    ret = b''

    # Output fields
    for k in kvlm.keys():
        # Skip the message itself
        if k == b'':
            continue
        val = kvlm[k]

        for v in val:
            ret += k + b' ' + (v.replace(b'\n', b'\n ')) + b'\n'

    # Append message
    ret += b'\n' + b''.join(kvlm[b''])
    return ret


class GitCommit(GitObject):
    def __init__(self, repo: Optional[GitRepository], data: Any = None, obj_type: bytes = b'commit') -> None:
        self.kvlm: Dict[bytes, List[bytes]] = {}
        super(GitCommit, self).__init__(repo, obj_type, data)

    def deserialize(self, data: Any) -> None:
        self.kvlm = kvlm_parse(data)

    def serialize(self) -> Any:
        return kvlm_serialize(self.kvlm)

    def pretty_print(self) -> str:
        return kvlm_serialize(self.kvlm).decode()


def commit_read(repo: GitRepository, sha: Sha) -> GitCommit:
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

    if fmt != b'commit':
        raise GitObjectTypeError(f"Unknown type {fmt.decode('ascii')} for object {sha}")

    return GitCommit(repo, raw[y+1:])
