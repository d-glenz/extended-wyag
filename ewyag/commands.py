import argparse
import logging
import pathlib

from ewyag.base import GitObjectTypeError
from ewyag.commit import commit_read
from ewyag.finder import object_find
from ewyag.repository import GitRepository, repo_create, repo_find, repo_path
from ewyag.objects import Sha, object_get_type
from ewyag.frontend import tree_write, log_graphviz, file_cat, generic_object_hash, generic_object_read, commit
from ewyag.tag import tag_create
from ewyag.trees import tree_checkout, tree_read
from ewyag.refs import ref_list, show_ref
from ewyag.index import read_index, add_all


_LOG = logging.getLogger('ewyag.commands')


def cmd_init(args: argparse.Namespace) -> None:
    repo_create(args.path)


def cmd_cat_file(args: argparse.Namespace) -> None:
    repo = repo_find()
    if repo is None:
        raise ValueError("Git repository not found!")

    if args.show_type:
        obj = generic_object_read(repo, args.object)
        _LOG.info(obj.fmt.decode())
        return

    if args.pretty_print or args.type:
        fmt = args.type.encode() if args.type else None
        file_cat(repo, args.object, fmt=fmt)


def cmd_hash_object(args: argparse.Namespace) -> None:
    sha = generic_object_hash(open(args.path, "rb"), args.type.encode(), GitRepository(".") if args.write else None)
    _LOG.info(sha)


def cmd_log(args: argparse.Namespace) -> None:
    repo = repo_find()
    assert repo is not None, "Git repository not found"

    _LOG.info("digraph ewyaglog{")
    git_object_sha = object_find(repo, args.commit)
    assert git_object_sha is not None
    log_graphviz(repo, git_object_sha, set())
    _LOG.info("}")


def cmd_ls_tree(args: argparse.Namespace) -> None:
    repo = repo_find()
    assert repo is not None, "Git repository not found"

    obj_sha = object_find(repo, args.object, fmt=b'tree')
    assert obj_sha is not None
    obj_content = tree_read(repo, obj_sha)

    for item in obj_content.items:
        mode = "0" * (6 - len(item.mode)) + item.mode.decode("ascii")
        fmt = object_get_type(repo, item.sha).decode("ascii")
        _LOG.info(f"{mode} {fmt} {item.sha}\t{item.path.decode('ascii')}")


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

    _LOG.info(object_find(repo, args.name, fmt, follow=True))


def cmd_commit(args: argparse.Namespace) -> None:
    sha1 = commit(args.author, args.message)
    _LOG.info(sha1)


def cmd_write_tree(args: argparse.Namespace) -> None:
    idx = read_index()
    repo = repo_find()
    assert repo is not None
    sha_of_tree = tree_write(repo, idx)
    _LOG.info(sha_of_tree)


def cmd_ls_files(args: argparse.Namespace) -> None:
    if args.stage:
        idx = read_index()
        for entry in idx:
            print(f"{entry.mode:o} {entry.hex_sha} {entry.flag_stage}\t{entry.name}")


def cmd_add(args: argparse.Namespace) -> None:
    if args.all:
        repo = repo_find()
        assert repo is not None
        all_paths = [repo_path(repo, '.').parent]
    else:
        all_paths = [pathlib.Path(path) for path in args.paths]
    add_all(all_paths)


def cmd_update_index(args: argparse.Namespace) -> None:
    if args.add:
        cmd_add(args)


def cmd_remote(args: argparse.Namespace) -> None:
    repo = repo_find()
    remotes = {}
    for section in repo.conf.sections():
        if not section.startswith('remote '):
            continue
        remote_name = section.split('"')[1]
        remotes[remote_name] = {
            "fetch": repo.conf.get(section, "url"),
            "pull": repo.conf.get(section, "url")
        }

    if args.subcommand == "add":
        section = f'remote "{args.name}"'
        repo.add_to_config(section,
                           {"url": args.url,
                            "fetch": f"+refs/heads/*:refs/remotes/{args.name}/*"})
    elif args.subcommand == "remove":
        section = f'remote "{args.name}"'
        repo.conf.remove_section(f'remote "{args.name}"')
        repo.write_config()
    elif args.subcommand == "get-url":
        print(remotes[args.name]['fetch'])
    elif args.subcommand == "prune":
        pass
    elif args.subcommand == "rename":
        old = f'remote "{args.old}"'
        new = f'remote "{args.new}"'
        repo.conf.add_section(new)
        for option_name in repo.conf.options(old):
            value = repo.conf.get(old, option_name)
            repo.conf.remove_option(old, option_name)
            repo.conf.set(new, option_name, value)
        repo.conf.remove_section(old)
        repo.write_config()
    elif args.subcommand == "set-branches":
        pass
    elif args.subcommand == "set-head":
        pass
    elif args.subcommand == "set-url":
        pass
    elif args.subcommand is None:
        for remote, value in remotes.items():
            if args.verbose:
                print(f"{remote}\t{value['fetch']} (fetch)")
                print(f"{remote}\t{value['pull']} (push)")
            else:
                print(f"remote")
    else:
        raise ValueError(f"Unknown subcommand to remote {args.subcommand}")
