import argparse
import pathlib

from wyag.repository import GitRepository, repo_create, repo_find
from wyag.objects import cat_file, object_hash, object_find, object_read, log_graphviz, GitCommit, tag_create
from wyag.trees import GitTree, tree_checkout
from wyag.refs import ref_list, show_ref


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


def cmd_ls_tree(args: argparse.Namespace) -> None:
    repo = repo_find()
    assert repo is not None, "Git repository not found"

    obj = object_read(repo, object_find(repo, args.object, fmt=b'tree'))
    assert isinstance(obj, GitTree)

    for item in obj.items:
        mode = "0" * (6 - len(item.mode)) + item.mode.decode("ascii")
        fmt = object_read(repo, item.sha).fmt.decode("ascii")
        print(f"{mode} {fmt} {item.sha}\t{item.path.decode('ascii')}")


def cmd_checkout(args: argparse.Namespace) -> None:
    repo = repo_find()
    assert repo is not None, "Git repository not found"

    obj = object_read(repo, object_find(repo, args.commit))
    # assert isinstance(obj, GitCommit)

    # If the object is a commit, we grab its tree
    if isinstance(obj, GitCommit):
        if obj.fmt == b'commit':
            obj = object_read(repo, obj.kvlm[b'tree'][0].decode("ascii"))

    assert isinstance(obj, GitTree)

    # Verify that path is an empty directory
    path = pathlib.Path(args.path)
    if path.exists():
        if not path.is_dir():
            raise ValueError(f"Not a directory {args.path}!")
        if list(path.iterdir()):
            raise ValueError(f"Not empty {args.path}!")
    else:
        path.mkdir(parents=True)

    tree_checkout(repo, obj, path.resolve())


def cmd_show_ref(args: argparse.Namespace) -> None:
    repo = repo_find()
    assert repo is not None
    refs = ref_list(repo)
    show_ref(repo, refs, prefix="refs")


def cmd_tag(args: argparse.Namespace) -> None:
    repo = repo_find()
    assert repo is not None

    if args.name:
        tag_create(repo,
                   args.name,
                   args.object,
                   args.create_tag_object)
    else:
        refs = ref_list(repo)
        show_ref(repo, refs["tags"], with_hash=False)
