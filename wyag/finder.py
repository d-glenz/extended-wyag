import re
from typing import List, Optional

from wyag.base import Sha
from wyag.commit import commit_read
from wyag.objects import object_get_type
from wyag.refs import ref_resolve
from wyag.repository import GitRepository, repo_dir, repo_file


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


def object_find(repo: GitRepository, name: str, fmt: Optional[bytes] = None, follow: bool = True) -> Optional[Sha]:
    """Will resolve objects by full hash, short hash, tags, ..."""
    all_shas = object_resolve(repo, name)

    if not all_shas:
        raise ValueError(f"No such reference: {name}")

    if len(all_shas) > 1:
        candidate_str = '\n'.join(all_shas)
        raise ValueError(f"Ambiguous reference {name}: Candidates are:\n - {candidate_str}")

    sha = all_shas[0]

    if not fmt:
        return Sha(sha)

    while True:
        obj_fmt = object_get_type(repo, Sha(sha))

        if obj_fmt == fmt:
            return Sha(sha)

        if not follow:
            return None

        commit = commit_read(repo, Sha(sha))

        # Follow tags
        if obj_fmt == b'tag':
            sha = commit.kvlm[b'object'][0].decode("ascii")
        elif obj_fmt == b'commit' and fmt == b'tree':
            sha = commit.kvlm[b'tree'][0].decode('ascii')
        else:
            return None
