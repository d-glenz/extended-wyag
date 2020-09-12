import configparser
import logging
import pathlib

from typing import Any, Optional


_LOG = logging.getLogger('ewyag.repository')


class GitRepository:
    """A git repository"""

    def __init__(self, path: str, force: bool = False) -> None:
        self.worktree = pathlib.Path(path)
        self.gitdir = self.worktree / ".git"
        self.conf = None

        if not (force or self.gitdir.is_dir()):
            # (or any parent up to mount point {})")
            raise ValueError(f"Not a git repository {str(path)}")

        self.conf = configparser.ConfigParser()
        cf = repo_file(self, "config")

        if cf and cf.exists():
            self.conf.read([str(cf)])
        elif not force:
            raise ValueError("Configuration file missing")

        if not force:
            vers = int(self.conf.get("core", "repositoryformatversion"))
            if vers != 0:
                raise ValueError(f"Unsupported repositoryformatversion {vers}")


def repo_path(repo: GitRepository, *path: str) -> pathlib.Path:
    """Compute path under repo's gitdir."""
    return repo.gitdir.joinpath(*path)


def repo_file(repo: GitRepository, *path: str, write: bool = False,
              mkdir: bool = False) -> Optional[pathlib.Path]:
    """Same as repo_path, but create dirname(*path) if absent. For
       example, repo_file(r, "refs", "remotes", "origin", "HEAD") will create
       .git/refs/remotes/origin."""

    if repo_dir(repo, *path[:-1], mkdir=mkdir):
        _LOG.debug(f"Path({'/'.join(path)}{', w=T' if write else ''})")
        return repo_path(repo, *path)

    return None


def repo_dir(repo: GitRepository, *path: str,
             mkdir: bool = False) -> Optional[pathlib.Path]:
    """Same as repo_path, but mkdir *path if absent if mkdir"""

    rpath = repo_path(repo, *path)

    if rpath.exists():
        if rpath.is_dir():
            return rpath
        raise ValueError(f"Not a directory {rpath}")

    if mkdir:
        _LOG.debug(f"Path('{rpath}').mkdir(parents=True)")
        rpath.mkdir(parents=True)
        return rpath

    return None


def repo_create(path: str) -> GitRepository:
    """Create a new repository at path."""

    repo = GitRepository(path, True)

    # First, we make sure the path either doens't exist or is an
    # empty dir

    if repo.worktree.exists():
        if not repo.worktree.is_dir():
            raise ValueError(f"{path} is not a directory!")
        if list(repo.worktree.iterdir()):
            # raise ValueError(f"{path} is not empty!")
            pass
    else:
        _LOG.debug(f"Path('{repo.worktree}').mkdir(parents=True)")
        repo.worktree.mkdir(parents=True)

    assert(repo_dir(repo, "branches", mkdir=True))
    assert(repo_dir(repo, "objects", mkdir=True))
    assert(repo_dir(repo, "refs", "tags", mkdir=True))
    assert(repo_dir(repo, "refs", "heads", mkdir=True))

    # .git/description
    desc_f = repo_file(repo, "description", write=True)
    if desc_f:
        with open(str(desc_f), "w") as f:
            f.write("Unnamed repository: edit this file 'description' to name the repository.\n")

    # .git/HEAD
    head_f = repo_file(repo, "HEAD", write=True)
    if head_f:
        with open(str(head_f), "w") as f:
            f.write("ref: refs/heads/master\n")

    # .git/config
    cfg_f = repo_file(repo, "config", write=True)
    if cfg_f:
        with open(str(cfg_f), "w") as f:
            config = repo_default_config()
            config.write(f)

    return repo


def repo_default_config() -> configparser.ConfigParser:
    ret = configparser.ConfigParser()

    ret.add_section("core")
    ret.set("core", "repositoryformatversion", "0")
    ret.set("core", "filemode", "false")
    ret.set("core", "bare", "false")

    return ret


def repo_find(path: str = '.', required: bool = True) -> Optional[GitRepository]:
    try:
        rpath = pathlib.Path(path).resolve()
    except FileNotFoundError as e:
        raise e

    if (rpath / ".git").is_dir():
        return GitRepository(path)

    # If we haven't returned, recurse in parent
    try:
        parent = (rpath / '..').resolve()
    except FileNotFoundError as e:
        raise e

    if parent == rpath:
        # bottom case
        # Path('/') / '..' == Path('/')
        # if parent == path, then path is root
        if required:
            # (or any parent up to mount point {})")
            raise ValueError(f"Not a git repository (or any parent up to mount point {parent}).")

        return None

    return repo_find(str(parent), required)


def write_file(path: str, data: Any) -> None:
    """Write data bytes to file at given path."""
    with open(path, 'wb') as f:
        f.write(data)
