import collections
import logging
import pathlib
from typing import Any, Dict

from ewyag.repository import GitRepository, repo_file, repo_dir


_LOG = logging.getLogger('ewyag.refs')


def show_ref(repo: GitRepository, refs: Dict[str, str], with_hash: bool = True, prefix: str = "") -> None:
    for k, v in refs.items():
        if isinstance(v, str):
            ref_hash = v + " " if with_hash else ""
            ref_prefix = prefix + "/" if prefix else ""
            _LOG.info(f"{ref_hash}{ref_prefix}{k}")
        else:
            show_ref(repo, v, with_hash=with_hash,
                     prefix=f"{prefix}{'/' if prefix else ''}{k}")


def ref_create(repo: GitRepository, ref_name: str, sha: str) -> None:
    with open(str(repo_file(repo, "refs/" + ref_name, write=True)), "w") as fp:
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
