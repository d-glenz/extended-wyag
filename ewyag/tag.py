import collections
from typing import Optional, Any

from ewyag.commit import GitCommit
from ewyag.finder import object_find
from ewyag.repository import GitRepository
from ewyag.objects import object_write
from ewyag.refs import ref_create


class GitTag(GitCommit):
    """Tag object.

       There are two types of tags, lightweight tags are just regular refs to a commit,
       a tree or a blob. Tag objects are regular refs pointing to an object of type tag.
       Unlike lightweight tags, tag objects have an author, a date, an optional PGP
       signature and an optional annotation."""

    def __init__(self, repo: Optional[GitRepository], data: Any = None) -> None:
        super(GitTag, self).__init__(repo, data, obj_type=b'tag')


def tag_create(repo: GitRepository, name: str, reference: str, create_tag_object: bool) -> None:
    # Get the GitObject from the object reference
    sha = object_find(repo, reference)
    assert sha is not None

    if create_tag_object:
        # create tag object (commit)
        tag = GitTag(repo)
        tag.kvlm = collections.OrderedDict()
        tag.kvlm[b'object'] = [sha.encode()]
        tag.kvlm[b'type'] = [b'commit']
        tag.kvlm[b'tag'] = [name.encode()]
        tag.kvlm[b'tagger'] = [b'The tagger']
        tag.kvlm[b''] = [b'This is the commit message that should have come from the user\n']
        tag_sha = object_write(tag)
        # create reference
        ref_create(repo, "tags/" + name, tag_sha)
    else:
        # create lightweight tag (ref)
        ref_create(repo, "tags/" + name, sha)
