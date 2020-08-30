import collections
import hashlib
import pathlib
import re
import sys
from typing import Any, Optional, BinaryIO, Dict, List, Set
import zlib

from wyag.repository import GitRepository, repo_file, repo_dir


class GitObject:
    def __init__(self, repo: Optional[GitRepository], fmt: bytes = b'', data: Any = None) -> None:
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


class GitBlob(GitObject):
    def __init__(self, repo: Optional[GitRepository], data: Any = None) -> None:
        super(GitBlob, self).__init__(repo, b'blob', data)

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


# TODO: function name inconsistent
def cat_file(repo: GitRepository, obj: Any, fmt: Optional[bytes] = None) -> None:
    obj = object_find(repo, obj, fmt=fmt)
    obj_content = object_read(repo, obj)
    sys.stdout.buffer.write(obj_content.serialize())


def object_hash(fd: BinaryIO, fmt: bytes, repo: Optional[GitRepository] = None) -> str:
    data = fd.read()

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

    return object_write(obj, repo is not None)


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
    def __init__(self, repo: Optional[GitRepository], data: Any = None, obj_type: bytes = b'commit') -> None:
        self.kvlm: Dict[bytes, List[bytes]] = {}
        super(GitCommit, self).__init__(repo, obj_type, data)

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


class GitTag(GitCommit):
    """Tag object.

       There are two types of tags, lightweight tags are just regular refs to a commit,
       a tree or a blob. Tag objects are regular refs pointing to an object of type tag.
       Unlike lightweight tags, tag objects have an author, a date, an optional PGP
       signature and an optional annotation."""

    def __init__(self, repo: Optional[GitRepository], data: Any = None) -> None:
        super(GitTag, self).__init__(repo, data, obj_type=b'tag')


def tag_create(repo: GitRepository, name: str, reference: str, create_tag_object: bool) -> None:
    # Get the GitObject from the object reference
    sha = object_find(repo, reference)
    assert sha is not None

    if create_tag_object:
        # create tag object (commit)
        tag = GitTag(repo)
        tag.kvlm = collections.OrderedDict()
        tag.kvlm[b'object'] = [sha.encode()]
        tag.kvlm[b'type'] = [b'commit']
        tag.kvlm[b'tag'] = [name.encode()]
        tag.kvlm[b'tagger'] = [b'The tagger']
        tag.kvlm[b''] = [b'This is the commit message that should have come from the user\n']
        tag_sha = object_write(tag)
        # create reference
        ref_create(repo, "tags/" + name, tag_sha)
    else:
        # create lightweight tag (ref)
        ref_create(repo, "tags/" + name, sha)


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
    for path in [f'refs/heads/{name}', f'refs/tags/{name}', f'refs/{name}', name]:
        if repo_file(repo, path).exists():
            candidates.append(ref_resolve(repo, path))

    return candidates


def object_find(repo: GitRepository, name: str, fmt: Optional[bytes] = None, follow: bool = True) -> Optional[str]:
    """Will resolve objects by full hash, short hash, tags, ..."""
    all_shas = object_resolve(repo, name)

    if not all_shas:
        raise ValueError(f"No such reference: {name}")

    if len(all_shas) > 1:
        candidate_str = '\n'.join(all_shas)
        raise ValueError(f"Ambiguous reference {name}: Candidates are:\n - {candidate_str}")

    sha = all_shas[0]

    if not fmt:
        return sha

    while True:
        obj = object_read(repo, sha)

        if obj.fmt == fmt:
            return sha

        if not follow:
            return None

        assert isinstance(obj, GitCommit)

        # Follow tags
        if obj.fmt == b'tag':
            sha = obj.kvlm[b'object'][0].decode("ascii")
        elif obj.fmt == f'commit' and fmt == b'tree':
            sha = obj.kvlm[b'tree'][0].decode('ascii')
        else:
            return None
