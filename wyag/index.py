import binascii
from enum import Enum
import operator
import hashlib
import pathlib
import stat
import struct
from typing import List

from wyag.repository import repo_path, repo_find, repo_file, GitRepository
from wyag.objects import blob_hash


class ModeTypes(Enum):
    REGULAR = 1
    SYMLINK = 2
    GITLINK = 3


mode_types = {
    "b1000": ModeTypes.REGULAR,
    "b1010": ModeTypes.SYMLINK,
    "b1110": ModeTypes.GITLINK
}

S_IFGITLINK = 0o160000


class GitIndexEntry:
    def __init__(self, ctime_s: int, ctime_n: int, mtime_s: int, mtime_n: int, dev: int, ino: int, mode: int,
                 uid: int, gid: int, size: int, sha1: bytes, flags: int, path: str) -> None:
        # The last time a file's metadata changed.
        # This is a tuple (seconds, nanoseconds)
        self.ctime = (ctime_s, ctime_n)

        self.mtime = (mtime_s, mtime_n)  # The last time a file's data changed.  This is a tuple (seconds, nanoseconds)#

        self.dev = dev  # The ID of device containing this file#
        self.ino = ino  # The file's inode number#

        # The object type, either b1000 (regular), b1010 (symlink), b1110 (gitlink). #
        # The object permissions, an integer.#
        self.mode = mode

        self.uid = uid  # User ID of owner#
        self.gid = gid  # Group ID of ownner (according to stat 2.  Isn'th)#
        self.size = size  # Size of this object, in bytes#
        self.obj = sha1  # The object's hash as a hex string#

        self.flags = flags
        # self.flag_assume_valid = flag_assume_valid
        # self.flag_extended = flag_extended
        # self.flag_stage = flag_stage
        # self.flag_name_length = flag_name_length """Length of the name if < 0xFFF (yes, three Fs), -1 otherwise"""

        self.name = path

        self.clean_mode = cleanup_mode(self.mode)
        self.hex_sha = sha_to_hex(self.obj)

        # FIXME
        # if self.mtype() == ModeTypes.REGULAR:
        #     assert (repr(self.mode_perms()) == "0644" or self.mode_perms() == "0755"), (
        #             f"mode_type: REGULAR, but mode_perms: {self.mode_perms()!r} "
        #             f"({self.mode_perms()} not in [0644, 0755])")

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


def sha_to_hex(sha: bytes) -> str:
    """Takes a string and returns the hex of the sha within
       https://github.com/dulwich/dulwich/blob/master/dulwich/objects.py"""
    hexsha = binascii.hexlify(sha)
    assert len(hexsha) == 40, "Incorrect length of sha1 string: %d" % hexsha
    return hexsha.decode()


def S_ISGITLINK(m: int) -> bool:
    """Check if a mode indicates a submodule.
    Args:
      m: Mode to check
    Returns: a ``boolean``
    """
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
        # print("File .git/index not found!")
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


def hash_object(path: pathlib.Path, write: bool, fmt: str) -> str:
    with open(str(path), "rb") as fd:
        if write:
            return blob_hash(fd, GitRepository("."))
        return blob_hash(fd, None)


def write_index(entries: List[GitIndexEntry]) -> None:
    """Write list of index entries objects to git index file.

       https://github.com/benhoyt/pygit/blob/master/pygit.py"""
    packed_entries = []
    for entry in entries:
        # print(f"{type(entry.ctime[0])}:{entry.ctime[0]}, {type(entry.ctime[1])}:{entry.ctime[1]}, {type(entry.mtime[0])}:{entry.mtime[0]},"
        #       f"{type(entry.mtime[1])}:{entry.mtime[1]}, {type(entry.dev)}:{entry.dev}, {type(entry.ino)}:{entry.ino}, "
        #       f"{type(entry.mode)}:{entry.mode}, {type(entry.uid)}:{entry.uid}, {type(entry.gid)}:{entry.gid},"
        #       f"{type(entry.size)}:{entry.size}, {type(entry.obj)}:{entry.obj}, {type(entry.flags)}:{entry.flags}")
        entry_head = struct.pack(
                "!LLLLLLLLLL20sH",
                entry.ctime[0], entry.ctime[1], entry.mtime[0], entry.mtime[1],
                entry.dev, entry.ino, entry.mode, entry.uid, entry.gid,
                entry.size, entry.obj, entry.flags)
        path = entry.name.encode()
        length = ((62 + len(path) + 8) // 8) * 8
        packed_entry = entry_head + path + b'\x00' * (length - 62 - len(path))
        packed_entries.append(packed_entry)
    header = struct.pack('!4sLL', b'DIRC', 2, len(entries))
    all_data = header + b''.join(packed_entries)
    digest = hashlib.sha1(all_data).digest()
    repo = repo_find()
    assert repo is not None
    with open(str(repo_file(repo, 'index')), "wb") as f:
        f.write(all_data + digest)


def add_path(path: pathlib.Path) -> GitIndexEntry:
    """https://github.com/benhoyt/pygit/blob/master/pygit.py"""
    sha1 = hash_object(path, write=True, fmt='blob')
    st = path.stat()
    flags = len(str(path).encode())
    assert flags < (1 << 12)
    entry = GitIndexEntry(int(st.st_ctime), st.st_ctime_ns%1000000000, int(st.st_mtime), st.st_mtime_ns%1000000000,
                          st.st_dev, st.st_ino, st.st_mode, st.st_uid, st.st_gid, st.st_size, bytes.fromhex(sha1),
                          flags, str(path))
    return entry


def add_all(paths: List[pathlib.Path]) -> None:
    """Add all file paths to git index.

       https://github.com/benhoyt/pygit/blob/master/pygit.py"""
    all_entries = read_index()
    entries = [e for e in all_entries if e.name not in paths]
    for path in paths:
        if path.is_dir():
            for subpath in path.rglob('*'):
                if not subpath.is_dir():
                    entries.append(add_path(subpath))
        else:
            entries.append(add_path(path))
    entries.sort(key=operator.attrgetter('name'))
    write_index(entries)
