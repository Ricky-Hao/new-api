#!/usr/bin/env python3
"""Generate new-api from a pinned upstream and the manifest's ordered Git diffs.

Adapted from Ricky-Hao/LibreChat f02d9b1d81a5e61661d69bea05e9278c162a3fd7.
Copyright (c) 2026 LibreChat. MIT license: tools/LICENSE.LibreChat.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = {'keep', 'feature', 'local', 'awaiting-upstream'}
STATUSES = ACTIVE | {'upstream', 'replaced'}
TIERS = {'focused', 'project'}


class Failure(Exception):
    pass


def require(condition, message):
    if not condition:
        raise Failure(message)


def inside(root, relative):
    path = Path(relative)
    require(not path.is_absolute() and '..' not in path.parts, f'Unsafe path: {relative}')
    resolved = (root / path).resolve()
    require(resolved.is_relative_to(root.resolve()), f'Path escapes checkout: {relative}')
    return resolved


def git(target, *args, env=None, data=None):
    result = subprocess.run(['git', '-C', str(target), *args], input=data,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if result.returncode:
        raise Failure(f'git {" ".join(args)} failed in {target}:\n'
                      + result.stderr.decode(errors='replace'))
    return result.stdout


def load_manifest(root=ROOT):
    manifest = json.loads((root / 'manifest.json').read_text())
    require(manifest['format'] == 1, 'Unsupported manifest format')
    require(re.fullmatch(r'[0-9a-f]{40}', manifest['base']), 'Base must be a full commit SHA')
    require(bool(manifest['upstream']), 'Upstream repository missing')
    seen = set()
    for entry in manifest['patches']:
        name = entry['id']
        require(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name), f'Invalid id: {name}')
        require(name not in seen, f'Duplicate id: {name}')
        require(entry['status'] in STATUSES, f'Unknown status: {name}')
        require(set(entry['depends_on']) <= seen, f'Missing or out-of-order dependency: {name}')
        require(entry['status'] not in ACTIVE or entry['patch'], f'Active patch missing: {name}')
        if entry['status'] not in ACTIVE:
            require(entry['patch'] is None and entry['paths'] == [], f'Retired payload: {name}')
            require(re.fullmatch(r'[0-9a-f]{40}', entry['replacement']['commit']),
                    f'Replacement commit missing: {name}')
            require(bool(entry['replacement']['evidence']), f'Replacement evidence missing: {name}')
        seen.add(name)
        if entry['patch']:
            require(inside(root, entry['patch']).is_file(), f'Payload missing: {name}')
        require(inside(root, f'patches/{name}/README.md').is_file(), f'Guide missing: {name}')
        contract = inside(root, entry['tests'])
        require(contract.is_file(), f'Test contract missing: {name}')
        checks = json.loads(contract.read_text())['checks']
        require(bool(checks), f'Empty test contract: {name}')
        for check in checks:
            validate_check(check)
    return manifest


def validate_check(check):
    require(bool(check['name']) and check['tier'] in TIERS, 'Invalid check name or tier')
    require(bool(check['requires']), f'No check entry paths: {check["name"]}')
    require(isinstance(check['command'], list) and bool(check['command'])
            and all(isinstance(arg, str) and arg for arg in check['command']),
            f'Command must be a nonempty argument array: {check["name"]}')


def select(manifest, only=None, statuses=None):
    entries = manifest['patches']
    known = {p['id']: p for p in entries}
    wanted = set(only) if only else {p['id'] for p in entries
                                    if not statuses or p['status'] in statuses}
    require(wanted <= known.keys(), f'Unknown patch ids: {sorted(wanted - known.keys())}')
    pending = list(wanted)
    while pending:
        for dependency in known[pending.pop()]['depends_on']:
            if dependency not in wanted:
                wanted.add(dependency)
                pending.append(dependency)
    require(bool(wanted), 'Selection is empty')
    return [p for p in entries if p['id'] in wanted]


def checkout(target):
    target = target.resolve()
    top = Path(git(target, 'rev-parse', '--show-toplevel').decode().strip()).resolve()
    require(top == target, '--target must name the application Git checkout root')
    return target


def fixed_base(target, base):
    head = git(target, 'rev-parse', 'HEAD').decode().strip()
    require(head == base, f'Target HEAD {head} differs from fixed base {base}; '
            'nothing applied. Adapt the patch set explicitly; the tool never changes base.')


def clean_base(target, base):
    require(not git(target, 'status', '--porcelain', '--untracked-files=all'),
            f'Target has changes or untracked files: {target}; nothing applied. '
            'Repeated application is refused. Use a fresh checkout for a new selection.')
    fixed_base(target, base)


def applicable(target, entries):
    result = []
    for entry in entries:
        if entry['status'] in ACTIVE:
            result.append(entry)
            continue
        commit = entry['replacement']['commit']
        git(target, 'merge-base', '--is-ancestor', commit, 'HEAD')
        print(f'SKIP {entry["id"]}: {entry["status"]}, included commit {commit}')
    return result


def payload(root, target, entry):
    path = inside(root, entry['patch'])
    stats = git(target, 'apply', '--numstat', '-z', str(path)).split(b'\0')
    paths = []
    for stat in filter(None, stats):
        _, _, name = stat.split(b'\t', 2)
        relative = name.decode()
        require('.git' not in Path(relative).parts, f'Git metadata in payload: {relative}')
        inside(target, relative)
        paths.append(relative)
    require(paths and len(paths) == len(set(paths)), f'Empty or duplicate diff paths: {entry["id"]}')
    require(set(paths) == set(entry['paths']), f'Payload path inventory differs: {entry["id"]}')
    return path.read_bytes()


def prepare(root, target, manifest, entries):
    entries = applicable(target, entries)
    # Preflight the entire sequence with a private index. A later conflict cannot
    # leave earlier patches in the user's index or working tree.
    git_dir = git(target, 'rev-parse', '--absolute-git-dir').decode().strip()
    with tempfile.TemporaryDirectory(prefix='patchset-', dir=git_dir) as temporary:
        env = {**os.environ, 'GIT_INDEX_FILE': str(Path(temporary) / 'index')}
        git(target, 'read-tree', manifest['base'], env=env)
        for entry in entries:
            try:
                git(target, 'apply', '--cached', '--binary', '--whitespace=nowarn', '-',
                    env=env, data=payload(root, target, entry))
            except Failure as error:
                raise Failure(f'Preflight stopped at {entry["id"]}. Target unchanged.\n{error}') from error
        result_tree = git(target, 'write-tree', env=env).decode().strip()
        combined = git(target, 'diff', '--binary', '--full-index', '--no-ext-diff',
                       '--no-renames', manifest['base'], result_tree)
    return entries, result_tree, combined


def apply(root, target, manifest, entries, write=False):
    clean_base(target, manifest['base'])
    entries, result_tree, combined = prepare(root, target, manifest, entries)
    if write and combined:
        clean_base(target, manifest['base'])
        git(target, 'apply', '--index', '--binary', '--whitespace=nowarn', '-', data=combined)
    action = 'APPLIED (staged)' if write else 'CHECKED (no application files changed)'
    print(f'{action}: {len(entries)} patches; tree {result_tree}')
    return result_tree


def verify(root, target, manifest, entries):
    fixed_base(target, manifest['base'])
    git(target, 'diff', '--exit-code')
    require(not git(target, 'ls-files', '--others', '--exclude-standard'),
            'Generated checkout has untracked files; preserve and write back your work first')
    _, expected, _ = prepare(root, target, manifest, entries)
    actual = git(target, 'write-tree').decode().strip()
    require(actual == expected, f'Generated tree {actual} differs from manifest tree {expected}; '
            'preserve and write back your work first')
    print(f'VERIFIED: base {manifest["base"]}; tree {actual}')
    return actual


def generate(root, target, manifest, entries, source=None):
    if target.exists():
        return verify(root, checkout(target), manifest, entries)
    target.parent.mkdir(parents=True, exist_ok=True)
    # An independent clone can be renamed safely; failed generation never exposes
    # a partially patched application or borrows a worktree's index.
    with tempfile.TemporaryDirectory(prefix='patchset-generate-', dir=target.parent) as temporary:
        application = Path(temporary) / 'application'
        git(target.parent, 'clone', '--no-checkout', '--no-hardlinks',
            str(source or manifest['upstream']), str(application))
        git(application, 'checkout', '--detach', manifest['base'])
        apply(root, application, manifest, entries)
        tree = apply(root, application, manifest, entries, write=True)
        application.rename(target)
    print(f'GENERATED: {target}; base {manifest["base"]}; tree {tree}')
    return tree


def contracts(root, target, entries, tier):
    checks = []
    seen = set()
    for entry in entries:
        contract = json.loads(inside(root, entry['tests']).read_text())
        for check in contract['checks']:
            validate_check(check)
            if tier != 'all' and check['tier'] != tier:
                continue
            key = json.dumps(check, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            cwd = inside(target, check['cwd'])
            require(cwd.is_dir(), f'Check directory missing: {cwd}')
            for path in check['requires']:
                require(inside(target, path).is_file(), f'Test/check entry missing: {path}')
            checks.append(check)
    require(bool(checks), f'No checks in tier {tier}; nothing was run')
    return checks


def test(root, target, entries, tier='focused'):
    for check in contracts(root, target, entries, tier):
        print(f'RUN: {check["name"]} ({check["cwd"]})', flush=True)
        subprocess.run(check['command'], cwd=inside(target, check['cwd']), check=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT, help=argparse.SUPPRESS)
    parser.add_argument('action', choices=['list', 'check', 'apply', 'generate', 'verify', 'test'])
    parser.add_argument('--target', type=Path)
    parser.add_argument('--source', type=Path, help='generate from a local Git repository (offline)')
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--only', nargs='+', metavar='ID', help='include ids and their dependencies')
    selection.add_argument('--status', nargs='+', choices=sorted(STATUSES))
    parser.add_argument('--tier', choices=[*sorted(TIERS), 'all'], default='focused')
    args = parser.parse_args(argv)
    root = args.root.resolve()
    manifest = load_manifest(root)
    entries = select(manifest, args.only, args.status)
    if args.action == 'list':
        for entry in entries:
            print(f'{entry["id"]}\t{entry["status"]}\t'
                  f'deps={",".join(entry["depends_on"]) or "-"}\t{entry["patch"] or "no payload"}')
        return
    require(args.target is not None, '--target is required')
    target = args.target.resolve()
    require(target != root, 'Use an application checkout, not the patch repository')
    require(args.source is None or args.action == 'generate', '--source is only for generate')
    if args.action == 'generate':
        generate(root, target, manifest, entries, args.source.resolve() if args.source else None)
        return
    target = checkout(target)
    if args.action in {'test', 'verify'}:
        verify(root, target, manifest, entries)
        if args.action == 'test':
            test(root, target, entries, args.tier)
    else:
        apply(root, target, manifest, entries, args.action == 'apply')


if __name__ == '__main__':
    try:
        main()
    except (Failure, OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
