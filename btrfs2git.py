#!/usr/bin/env python3
import argparse
import functools
import logging
import os
import re
import shutil
from subprocess import check_call, check_output, DEVNULL, PIPE, run
import tempfile

os.putenv('GIT_AUTHOR_DATE', 'unix:100000000')
os.putenv('GIT_COMMITTER_DATE', 'unix:100000000')
WB = re.compile(r'^Well block (\d+)\(gen: (\d+) level: ')
RT = re.compile(r'^Found tree root at (\d+) gen (\d+) level ')


@functools.lru_cache(typed=True)
def write_object(b):
    return check_output(['git', 'hash-object', '-w', '--stdin'], input=b, cwd=args.path).strip()


def exclude(path):
    if {'__pycache__', 'node_modules'}.intersection(path.split(os.sep)[1:]):
        return True
    if os.path.splitext(path)[1] in {'.pyc', '.pyo'}:
        return True
    return False


def handle_restore(proc, m):
    _p = re.escape(args.path)
    REGULAR = re.compile(r'^Restoring (%s/.+)$' % _p)
    SYMLINK = re.compile(r"^SYMLINK: '(%s/.+)' => '.*'$" % _p)
    info, dirs = [], set()
    for ff in reversed(proc.stdout.decode().splitlines()):
        try:
            if ff.startswith('Restoring '):
                F = REGULAR
            elif ff.startswith('SYMLINK: '):
                F = SYMLINK
            else:
                continue
            path = F.match(ff).group(1)
            if exclude(path):
                continue
            path = path[len(args.path)+1:]
            dirs.add(os.path.dirname(path))
            if path not in dirs:
                info.append(b'%s %s\t%s' % (b'100644', write_object(ff[0].encode('ascii')), path.encode()))
        except Exception:
            logging.exception('Exception happens when processing "%s"', ff)
            raise
    new_idx = tempfile.mkstemp()[1]
    os.unlink(new_idx)
    os.putenv('GIT_INDEX_FILE', new_idx)
    check_call(['git', 'update-index', '-z', '--remove', '--index-info'],
               input=b'\0'.join(info), cwd=args.path, stderr=DEVNULL)
    if os.path.isfile(new_idx):
        shutil.move(new_idx, os.path.join(args.path, '.git', 'index'))
        os.unsetenv('GIT_INDEX_FILE')
    check_call(['git', 'commit', '--allow-empty', '-m', m], cwd=args.path, stdout=DEVNULL)


def main():
    processed = check_output(['git', 'log', '--format=%s'], cwd=args.path).decode().splitlines()

    for l in reversed(tuple(args.roots)):
        if l.startswith('Well block '):
            BLK = WB
        elif l.startswith('Found tree root '):
            BLK = RT
        else:
            continue
        for d in os.listdir(args.path):
            if d != '.git':
                try:
                    shutil.rmtree(os.path.join(args.path, d))
                except NotADirectoryError:
                    os.unlink(os.path.join(args.path, d))
        assert os.listdir(args.path) == ['.git'], os.listdir(args.path)
        b, g = BLK.match(l).groups()
        if g == os.getenv('STOP'):
            break
        m = '{b} {g}'.format(b=b, g=g)
        if m in processed:
            logging.info('Already processed "%s"', m)
            continue
        proc = run(['btrfs', 'restore', '-vDiSt', b, args.device, args.path], stdout=PIPE, stderr=DEVNULL)
        if proc.returncode != 0:
            logging.warning('Failed to restore "%s"', m)
            continue
        handle_restore(proc, m)
    else:
        m = 'latest'
        if m not in processed:
            proc = run(['btrfs', 'restore', '-vDiS', args.device, args.path], stdout=PIPE, stderr=DEVNULL)
            if proc.returncode != 0:
                logging.warning('Failed to restore "%s"', m)
            handle_restore(proc, m)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('device', help='See btrfs-restore(8)')
    parser.add_argument('path', help='Path to an initialized git repo.')
    parser.add_argument('roots', help='Output from `btrfs-find-root "$device"`', type=argparse.FileType())
    args = parser.parse_args()
    main()
