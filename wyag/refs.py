from typing import Dict

from wyag.repository import GitRepository


def show_ref(repo: GitRepository, refs: Dict[str, str], with_hash: bool = True, prefix: str = "") -> None:
    for k, v in refs.items():
        if isinstance(v, str):
            ref_hash = v + " " if with_hash else ""
            ref_prefix = prefix + "/" if prefix else ""
            print(f"{ref_hash}{ref_prefix}{k}")
        else:
            show_ref(repo, v, with_hash=with_hash,
                     prefix=f"{prefix}{'/' if prefix else ''}{k}")
