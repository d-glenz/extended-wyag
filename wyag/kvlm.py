"""Suitable for both commits and tags"""

import collections
from typing import Dict, List, Optional, Any, Set

from wyag.objects import GitObject, object_read
from wyag.repository import GitRepository


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
    message = kvlm[b'']
    if isinstance(message, bytearray):
        ret += b'\n' + b''.join(message)
    else:
        raise ValueError("message is List[bytes]")

    return ret


class GitCommit(GitObject):
    def __init__(self, repo: Optional[GitRepository], data: Any = None) -> None:
        self.kvlm: Dict[bytes, List[bytes]] = {}
        super(GitCommit, self).__init__(repo, b'commit', data)

    def deserialize(self, data):
        self.kvlm = kvlm_parse(data)

    def serialize(self):
        return kvlm_serialize(self.kvlm)


def log_graphviz(repo: GitRepository, sha: str, seen: Set[str]) -> None:
    if sha in seen:
        return
    seen.add(sha)

    commit = object_read(repo, sha)
    assert isinstance(commit, GitCommit)
    assert commit.fmt == b'commit'

    if b'parent' not in commit.kvlm.keys():
        # Base case: the initial commit.
        return

    parents = commit.kvlm[b'parent']

    for p in parents:
        print("c_{0} -> c_{1};".format(sha, p.decode("ascii")))
        log_graphviz(repo, p.decode("ascii"), seen)
