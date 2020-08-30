import argparse
import collections  # noqa: F401
import hashlib  # noqa: F401
import os  # noqa: F401
import re  # noqa: F401
import sys
from typing import List
import zlib  # noqa: F401

from wyag.commands import (cmd_init, cmd_cat_file, cmd_hash_object, cmd_log,
                           cmd_ls_tree, cmd_checkout, cmd_show_ref, cmd_tag)

argparser = argparse.ArgumentParser(description="The stupid content tracker")
argsubparsers = argparser.add_subparsers(title='Commands', dest='command')
argsubparsers.required = True

initp = argsubparsers.add_parser("init", help="Initialize a new, empty repository.")
initp.add_argument(
    "path",
    metavar="directory",
    nargs="?",
    default=".",
    help="Where to create the repository.",
)

catfilep = argsubparsers.add_parser("cat-file", help="Provide content of repository objects")
catfilep.add_argument(
    "type",
    metavar="type",
    choices=["blob", "commit", "tag", "tree"],
    help="Specify the type",
)
catfilep.add_argument(
    "object",
    metavar="object",
    help="The object to display",
)

hashobjectp = argsubparsers.add_parser("hash-object",
                                       help="Compute object ID and optionally creates a blob from a file")
hashobjectp.add_argument(
    "-t",
    metavar="type",
    dest="type",
    choices=["blob", "commit", "tag", "tree"],
    default="blob",
    help="Specify the type",
)
hashobjectp.add_argument(
    "-w",
    dest="write",
    action="store_true",
    help="Actually write the object into the database"
)
hashobjectp.add_argument(
    "path",
    help="Read object from <file>",
)

logp = argsubparsers.add_parser("log", help="Display history of a given commit.")

logp.add_argument("commit",
                  default="HEAD",
                  nargs="?",
                  help="Commit to start at.")

lstreep = argsubparsers.add_parser("ls-tree", help="Pretty-print a tree object.")
lstreep.add_argument("object",
                     help="The object to show")

checkoutp = argsubparsers.add_parser("checkout", help="checkout a commit inside of a directory.")
checkoutp.add_argument("commit",
                       help="The commit or tree to checkout.")

checkoutp.add_argument("path",
                       help="The EMPTY directory to checkout on.")


showrefp = argsubparsers.add_parser("show-ref", help="List references.")

tagp = argsubparsers.add_parser("tag", help="List and create tags")
tagp.add_argument("-a",
                  action="store_true",
                  dest="create_tag_object",
                  help="Whether to create a tag object")

tagp.add_argument("name",
                  nargs="?",
                  help="The new tag's name")
tagp.add_argument("object",
                  default="HEAD",
                  nargs="?",
                  help="The object the new tag will point to")


def main(argv: List[str] = sys.argv[1:]) -> None:
    args = argparser.parse_args(argv)

    command_dict = {
        # "add": cmd_add,
        "cat-file": cmd_cat_file,
        "checkout": cmd_checkout,
        # "commit": cmd_commit,
        "hash-object": cmd_hash_object,
        "init": cmd_init,
        "log": cmd_log,
        "ls-tree": cmd_ls_tree,
        # "merge": cmd_merge,
        # "rebase": cmd_rebase,
        # "rev-parse": cmd_rev_parse,
        # "rm": cmd_rm,
        "show-ref": cmd_show_ref,
        "tag": cmd_tag,
    }

    try:
        target_function = command_dict[args.command]
        target_function(args)
    except KeyError:
        print(f"wyag: '{args.command}' is not a wyag command. See 'wyag --help'.", file=sys.stderr)
