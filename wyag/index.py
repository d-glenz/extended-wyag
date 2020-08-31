import binascii
from enum import Enum
import hashlib
import stat
import struct
from typing import List, Tuple

from wyag.repository import repo_path, repo_find


class ModeTypes(Enum):
    REGULAR = 1
    SYMLINK = 2
    GITLINK = 3


mode_types = {
    "b1000": ModeTypes.REGULAR,
    "b1010": ModeTypes.SYMLINK,
    "b1110": ModeTypes.GITLINK
}


class GitIndexEntry:
    def __init__(self, ctime_s: int, ctime_n: int, mtime_s: int, mtime_n: int, dev: int, ino: int, mode: int,
                 uid: int, gid: int, size: int, sha1: str, flags: int, path: str) -> None:
        self.ctime = (ctime_s, ctime_n) # The last time a file's metadata changed.  This is a tuple (seconds, nanoseconds)

        self.mtime = (mtime_s, mtime_n) # The last time a file's data changed.  This is a tuple (seconds, nanoseconds)#

        self.dev = dev # The ID of device containing this file#
        self.ino = ino # The file's inode number#
        self.mode = mode # The object type, either b1000 (regular), b1010 (symlink), b1110 (gitlink). #
                         # The object permissions, an integer.#

        self.uid = uid # User ID of owner#
        self.gid = gid # Group ID of ownner (according to stat 2.  Isn'th)#
        self.size = size # Size of this object, in bytes#
        self.obj = sha1 # The object's hash as a hex string#

        self.flags = flags
        # self.flag_assume_valid = flag_assume_valid
        # self.flag_extended = flag_extended
        # self.flag_stage = flag_stage
        # self.flag_name_length = flag_name_length """Length of the name if < 0xFFF (yes, three Fs), -1 otherwise"""

        self.name = path

        self.clean_mode = cleanup_mode(self.mode)
        self.hex_sha = sha_to_hex(self.obj)

        if self.mtype() == ModeTypes.REGULAR:
            assert (self.mode_perms() == "0644" or self.mode_perms() == "0755"), f"mode_type: REGULAR, but mode_perms: {self.mode_perms()!r}"

    def mode_type(self) -> int:
        """The object type, either b1000 (regular), b1010 (symlink), b1110 (gitlink). """
        return (self.mode & (15 << 4*3)) >> 4*3

    def mode_type_str(self) -> str:
        """"{0:b}".format((idx[1].mode & int("1111000000000000", 2)) >> 12)"""
        return "b{0:b}".format(self.mode_type())

    def mtype(self) -> ModeTypes:
        return mode_types[self.mode_type_str()]

    def mode_perms(self) -> str:
        return "0{0:o}".format(self.mode & int("0000000111111111", 2))

def sha_to_hex(sha: str) -> str:
    """Takes a string and returns the hex of the sha within
       https://github.com/dulwich/dulwich/blob/master/dulwich/objects.py"""
    hexsha = binascii.hexlify(sha)
    assert len(hexsha) == 40, "Incorrect length of sha1 string: %d" % hexsha
    return hexsha


def S_ISGITLINK(m: int) -> bool:
    """Check if a mode indicates a submodule.
    Args:
      m: Mode to check
    Returns: a ``boolean``
    """
    S_IFGITLINK = 0o160000
    return (stat.S_IFMT(m) == S_IFGITLINK)


def cleanup_mode(mode: int) -> int:
    """Cleanup a mode value.

    This will return a mode that can be stored in a tree object.

    Args:
      mode: Mode to clean up.
    Returns:
      mode
    """
    if stat.S_ISLNK(mode):
        return stat.S_IFLNK
    elif stat.S_ISDIR(mode):
        return stat.S_IFDIR
    elif S_ISGITLINK(mode):
        return S_IFGITLINK
    ret = stat.S_IFREG | 0o644
    if mode & 0o100:
        ret |= 0o111
    return ret


def read_index() -> List[GitIndexEntry]:
    """Read git index file and return list of IndexEntry objects.
       https://benhoyt.com/writings/pygit/"""

    repo = repo_find()
    assert repo is not None, "Repo is None"

    try:
        data = open(str(repo_path(repo, "index")), 'rb').read()
    except FileNotFoundError:
        print("File .git/index not found!")
        return []
    digest = hashlib.sha1(data[:-20]).digest()
    assert digest == data[-20:], 'invalid index checksum'

    signature, version, num_entries = struct.unpack('!4sLL', data[:12])
    assert signature == b'DIRC', \
        'invalid index signature {}'.format(signature)
    assert version == 2, 'unknown index version {}'.format(version)

    entry_data = data[12:-20]
    entries = []
    i = 0

    while i + 62 < len(entry_data):
        fields_end = i + 62
        fields = struct.unpack('!LLLLLLLLLL20sH', entry_data[i:fields_end])
        path_end = entry_data.index(b'\x00', fields_end)
        path = entry_data[fields_end:path_end]
        entries.append(GitIndexEntry(*(fields + (path.decode(),))))

        entry_len = ((62 + len(path) + 8) // 8) * 8
        i += entry_len

    assert len(entries) == num_entries
    return entries
