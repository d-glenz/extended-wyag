import collections
import pathlib
import re
from typing import Dict, Any, List

from wyag.repository import repo_file, repo_dir, GitRepository


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


def show_ref(repo: GitRepository, refs: Dict[str, str], with_hash: bool = True, prefix: str = "") -> None:
    for k, v in refs.items():
        if isinstance(v, str):
            ref_hash = v + " " if with_hash else ""
            ref_prefix = prefix + "/" if prefix else ""
            print(f"{ref_hash}{ref_prefix}{k}")
        else:
            show_ref(repo, v, with_hash=with_hash,
                     prefix=f"{prefix}{'/' if prefix else ''}{k}")


def object_resolve(repo: GitRepository, name: str) -> List[str]:
    """Resolve name to an object hash in repo.

       This function is aware of:
        - the HEAD literal
        - short and long hashes
        - tags
        - branches
        - remote branches"""

    candidates = []
    hashRE = re.compile(r"^[0-9A-Fa-f]{1,16}$")
    smallHashRE = re.compile(r"^[0-9A-Fa-f]{1,16}$")  # noqa: F841

    # Empty string? Abort.
    if not name.strip():
        return []

    if name == "HEAD":
        return [ref_resolve(repo, "HEAD")]

    if hashRE.match(name):
        if len(name) == 40:
            # This is a complete hash
            return [name.lower()]
        if len(name) >= 4:
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

    return candidates
