import argparse
import pathlib

from wyag.repository import GitRepository, repo_create, repo_find
from wyag.objects import cat_file, object_hash, object_find, object_read, log_graphviz, GitCommit, ref_list, tag_create
from wyag.trees import GitTree, tree_checkout
from wyag.refs import show_ref


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
    assert git_object is not None
    log_graphviz(repo, git_object, set())
    print("}")


def cmd_ls_tree(args: argparse.Namespace) -> None:
    repo = repo_find()
    assert repo is not None, "Git repository not found"

    obj = object_find(repo, args.object, fmt=b'tree')
    assert obj is not None
    obj_content = object_read(repo, obj)
    assert isinstance(obj_content, GitTree)

    for item in obj_content.items:
        mode = "0" * (6 - len(item.mode)) + item.mode.decode("ascii")
        fmt = object_read(repo, item.sha).fmt.decode("ascii")
        print(f"{mode} {fmt} {item.sha}\t{item.path.decode('ascii')}")


def cmd_checkout(args: argparse.Namespace) -> None:
    repo = repo_find()
    assert repo is not None, "Git repository not found"

    obj = object_find(repo, args.commit)
    assert obj is not None
    obj_contents = object_read(repo, obj)
    # assert isinstance(obj, GitCommit)

    # If the object is a commit, we grab its tree
    if isinstance(obj_contents, GitCommit):
        if obj_contents.fmt == b'commit':
            obj_contents = object_read(repo, obj_contents.kvlm[b'tree'][0].decode("ascii"))

    assert isinstance(obj_contents, GitTree)

    # Verify that path is an empty directory
    path = pathlib.Path(args.path)
    if path.exists():
        if not path.is_dir():
            raise ValueError(f"Not a directory {args.path}!")
        if list(path.iterdir()):
            raise ValueError(f"Not empty {args.path}!")
    else:
        path.mkdir(parents=True)

    tree_checkout(repo, obj_contents, path.resolve())


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


def cmd_rev_parse(args: argparse.Namespace) -> None:
    if args.type:
        fmt = args.type.encode()

    repo = repo_find()
    assert repo is not None

    print(object_find(repo, args.name, fmt, follow=True))
