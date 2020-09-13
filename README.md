# extended-wyag

Extended Write yourself a git

This is an extended version of "Write-yourself-a-Git" (https://github.com/thblt/write-yourself-a-git and https://wyag.thb.lt/).

Several steps were taken to change the structure of wyag:
* Added a `setup.py` and turned the binary `wyag` into an entrypoint in the setup.py.
* Split up `libwyag.py` into several modules.
* Added index handling inspired by pygit (https://github.com/benhoyt/pygit and https://benhoyt.com/writings/pygit/)
* Added commit functionality inspired by pygit
* Added `git tag` functionality from https://github.com/thblt/write-yourself-a-git/pull/11
* Added `git ls-files` command
* Added `git update-index` command
* Added `git write-tree` command
