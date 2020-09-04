import argparse
import pathlib

from wyag.base import GitObjectTypeError
from wyag.commit import commit_read
from wyag.finder import object_find
from wyag.repository import GitRepository, repo_create, repo_find
from wyag.objects import Sha, object_get_type
from wyag.frontend import tree_write, log_graphviz, file_cat, generic_object_hash, generic_object_read, commit
from wyag.tag import tag_create
from wyag.trees import tree_checkout, tree_read
from wyag.refs import ref_list, show_ref
from wyag.index import read_index, add_all


def cmd_init(args: argparse.Namespace) -> None:
    repo_create(args.path)


def cmd_cat_file(args: argparse.Namespace) -> None:
    repo = repo_find()
    if repo is None:
        raise ValueError("Git repository not found!")

    if args.show_type:
        obj = generic_object_read(repo, args.object)
        print(obj.fmt.decode())
        return

    if args.pretty_print or args.type:
        fmt = args.type.encode() if args.type else None
        file_cat(repo, args.object, fmt=fmt)


def cmd_hash_object(args: argparse.Namespace) -> None:

    with open(args.path, "rb") as fd:
        if args.write:
            sha = generic_object_hash(fd, args.type.encode(), GitRepository("."))
        else:
            sha = generic_object_hash(fd, args.type.encode(), None)
        print(sha)


def cmd_log(args: argparse.Namespace) -> None:
    repo = repo_find()
    assert repo is not None, "Git repository not found"

    print("digraph wyaglog{")
    git_object_sha = object_find(repo, args.commit)
    assert git_object_sha is not None
    log_graphviz(repo, git_object_sha, set())
    print("}")


def cmd_ls_tree(args: argparse.Namespace) -> None:
    repo = repo_find()
    assert repo is not None, "Git repository not found"

    obj_sha = object_find(repo, args.object, fmt=b'tree')
    assert obj_sha is not None
    obj_content = tree_read(repo, obj_sha)

    for item in obj_content.items:
        mode = "0" * (6 - len(item.mode)) + item.mode.decode("ascii")
        fmt = object_get_type(repo, item.sha).decode("ascii")
        print(f"{mode} {fmt} {item.sha}\t{item.path.decode('ascii')}")


def cmd_checkout(args: argparse.Namespace) -> None:
    repo = repo_find()
    assert repo is not None, "Git repository not found"

    obj_sha = object_find(repo, args.commit)
    assert obj_sha is not None

    try:
        commit_contents = commit_read(repo, obj_sha)
        tree_contents = tree_read(repo, Sha(commit_contents.kvlm[b'tree'][0].decode("ascii")))
    except GitObjectTypeError:
        raise ValueError(f"Cannot checkout {args.commit} since it's not a commit!")

    # Verify that path is an empty directory
    path = pathlib.Path(args.path)
    if path.exists():
        if not path.is_dir():
            raise ValueError(f"Not a directory {args.path}!")
        if list(path.iterdir()):
            raise ValueError(f"Not empty {args.path}!")
    else:
        path.mkdir(parents=True)

    tree_checkout(repo, tree_contents, path.resolve())


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


def cmd_commit(args: argparse.Namespace) -> None:
    sha1 = commit(args.author, args.message)
    print(sha1)


def cmd_write_tree(args: argparse.Namespace) -> None:
    idx = read_index()
    repo = repo_find()
    assert repo is not None
    sha_of_tree = tree_write(repo, idx)
    print(sha_of_tree)


def cmd_add(args: argparse.Namespace) -> None:
    all_paths = [pathlib.Path(path) for path in args.paths]
    add_all(all_paths)
