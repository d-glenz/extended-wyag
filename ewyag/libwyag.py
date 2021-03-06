import argparse
import logging
import sys

from ewyag.commands import (cmd_init, cmd_cat_file, cmd_hash_object, cmd_log, cmd_ls_tree,
                            cmd_checkout, cmd_show_ref, cmd_tag, cmd_rev_parse, cmd_commit,
                            cmd_write_tree, cmd_add, cmd_ls_files, cmd_update_index,
                            cmd_remote)


_LOG = logging.getLogger('ewyag')


argparser = argparse.ArgumentParser(description="The stupid content tracker")
argparser.add_argument('--verbose', '-v', action='store_true')

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
    "-t",
    dest="show_type",
    action="store_true",
    help="Instead of the content, show the object type identified by <object>",
)
catfilep.add_argument(
    "-p",
    dest="pretty_print",
    action="store_true",
    help="Instead of the content, show the object type identified by <object>",
)
catfilep.add_argument(
    "type",
    metavar="type",
    nargs='?',
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

revparsep = argsubparsers.add_parser("rev-parse", help="Parse revision (or other objects) identifiers")
revparsep.add_argument("--wyag-type",
                       metavar="type",
                       dest="type",
                       choices=["blob", "commit", "tag", "tree"],
                       default=None,
                       help="Specify the expected type")

revparsep.add_argument("name",
                       help="The name to parse")

commitp = argsubparsers.add_parser("commit", help="Record changes to the repository")
commitp.add_argument("author",
                     help="Specify the author")
commitp.add_argument("committer",
                     help="Specify who committed.")
commitp.add_argument("message",
                     help="Specify the commit message")

writetreep = argsubparsers.add_parser("write-tree", help="Create a tree object from the current index")

addp = argsubparsers.add_parser("add", help="Add file contents to the index")
addp.add_argument("paths",
                  nargs='*',
                  help="Add file contents to the index")

addp.add_argument('-A',
                  dest='all',
                  action="store_true",
                  help=("Update the index not only where the working tree has a file matching <pathspec> "
                        "but also where the index already has an entry."))


updateindexp = argsubparsers.add_parser("update-index", help="Modifies the index or directory cache.")
updateindexp.add_argument("--add", action="store_true", help=("If a specified file isn’t in the index already then "
                                                              "it’s added."))
updateindexp.add_argument("paths", nargs="+", help="Files to act on.")


lsfilesp = argsubparsers.add_parser("ls-files", help="Show information about files in the index and the working tree.")
lsfilesp.add_argument("--stage", "-s", action="store_true", help=("Show staged contents' object name, mode bits and "
                                                                  "stage number in the output."))

remotep = argsubparsers.add_parser('remote', help="Manage set of tracked repositories.")
remotep.add_argument('-v', '--verbose', action="store_true")
remotesubparsers = remotep.add_subparsers(title='Sub-Commands', dest='subcommand')

remoteaddp = remotesubparsers.add_parser("add")
remoteaddp.add_argument("name")
remoteaddp.add_argument("url")
remoteaddp.add_argument("--fetch", "-f", action="store_true")
remoteaddp.add_argument("--tags")
remoteaddp.add_argument("-t","--track")
remoteaddp.add_argument("-m","--master")
remoteaddp.add_argument("--mirror", choices=["push", "fetch"])

remotegeturlp = remotesubparsers.add_parser("get-url")
remotegeturlp.add_argument('--push')
remotegeturlp.add_argument('--all')
remotegeturlp.add_argument('name')

remoteremovep = remotesubparsers.add_parser("remove")
remoteremovep.add_argument("name")

remoterenamep = remotesubparsers.add_parser("rename")
remoterenamep.add_argument("old")
remoterenamep.add_argument("new")

remoteprunep = remotesubparsers.add_parser("prune")
remotesetbranchesp = remotesubparsers.add_parser("set-branches")
remotesetheadp = remotesubparsers.add_parser("set-head")
remoteseturlp = remotesubparsers.add_parser("set-url")


def subcommand_main() -> None:
    args = argparser.parse_args()

    _LOG.addHandler(logging.StreamHandler(sys.stdout))
    if args.verbose:
        _LOG.setLevel(logging.DEBUG)
    else:
        _LOG.setLevel(logging.INFO)

    command_dict = {
        "add": cmd_add,
        "cat-file": cmd_cat_file,
        "checkout": cmd_checkout,
        "commit": cmd_commit,
        "hash-object": cmd_hash_object,
        "init": cmd_init,
        "log": cmd_log,
        "ls-tree": cmd_ls_tree,
        "ls-files": cmd_ls_files,
        # "merge": cmd_merge,
        # "rebase": cmd_rebase,
        "rev-parse": cmd_rev_parse,
        "remote": cmd_remote,
        # "rm": cmd_rm,
        "show-ref": cmd_show_ref,
        "tag": cmd_tag,
        "update-index": cmd_update_index,
        "write-tree": cmd_write_tree,
    }

    try:
        target_function = command_dict[args.command]
        target_function(args)
    except KeyError:
        _LOG.warning(f"ewyag: '{args.command}' is not a ewyag command. See 'ewyag --help'.", file=sys.stderr)
