import argparse
from wyag.repository import GitRepository, repo_create, repo_find
from wyag.objects import cat_file, object_hash, object_find
from wyag.kvlm import log_graphviz


def cmd_init(args: argparse.Namespace) -> None:
    repo_create(args.path)


def cmd_cat_file(args: argparse.Namespace) -> None:
    repo = repo_find()
    if repo is None:
        raise ValueError("Git repository not found!")

    cat_file(repo, args.object, fmt=args.type.encode())


def cmd_hash_object(args: argparse.Namespace) -> None:

    with open(args.path, "rb") as fd:
        if args.write:
            sha = object_hash(fd, args.type.encode(), GitRepository("."))
        else:
            sha = object_hash(fd, args.type.encode(), None)
        print(sha)


def cmd_log(args: argparse.Namespace) -> None:
    repo = repo_find()
    assert repo is not None, "Git repository not found"

    print("digraph wyaglog{")
    git_object = object_find(repo, args.commit)
    log_graphviz(repo, git_object, set())
    print("}")
