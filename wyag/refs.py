import collections
import pathlib
from typing import Dict, Any

from wyag.repository import repo_file, repo_dir, GitRepository
from wyag.objects import object_find, object_write
from wyag.kvlm import GitTag


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


def tag_create(repo: GitRepository, name: str, reference: str, create_tag_object: bool) -> None:
    # Get the GitObject from the object reference
    sha = object_find(repo, reference)

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
