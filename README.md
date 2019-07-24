# BTRFS to Git

![pyenv](https://img.shields.io/badge/python-3.5%20%7C%203.6%20%7C%203.7-blue.svg)

This script provides a quick preview of results of `btrfs restore`, which is useful for undeleting files.

According to [btrfs restore](https://btrfs.wiki.kernel.org/index.php/Restore), in order to restore the deleted files, one must try all the "well blocks" and figure out which blocks contain the needed files by running dry-runs.

This script tries all the "well blocks", generates files list, and converts it into a directory structure and a git repo.

Thus, the differences between "well blocks" can be viewed by genernal git operations, such as `git log` and `git diff`.

Note that this script doesn't not track the changes of the file content.
This script only records the existence and type of a file.
A regular file is represented by a file containing a single character 'R', and a symbolic link is represented by a single 'S'.
