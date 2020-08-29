import argparse
from wyag.repository import repo_create


def cmd_init(args: argparse.Namespace) -> None:
    repo_create(args.path)
