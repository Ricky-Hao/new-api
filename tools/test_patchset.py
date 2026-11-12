"""Real Git regression tests, adapted from the LibreChat source in SOURCES.md.

Copyright (c) 2026 LibreChat. MIT license: tools/LICENSE.LibreChat.
"""
import contextlib
import copy
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import patchset

CLI = Path(__file__).with_name('patchset.py').resolve()


class PatchsetTests(unittest.TestCase):
    def setUp(self):
        work = CLI.parents[1] / '.work'
        work.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix='tool-test-', dir=work)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / 'catalog'
        self.target = Path(temporary.name) / 'application'
        self.root.mkdir()
        self.target.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Patchset test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'commit.gpgsign', 'false')
        self.write('file.txt', 'base\n')
        self.write('.gitignore', 'node_modules/\nignored.txt\n')
        self.write('web/check.test.ts', '// runner fixture\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD').decode().strip()
        self.manifest = {'format': 1, 'upstream': str(self.target),
                         'base': self.base, 'patches': []}
        self.add_patch('first', 'base', 'first')
        self.add_patch('second', 'first', 'second', ['first'])
        self.save()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.target), *args],
                                       stderr=subprocess.PIPE)

    def write(self, path, text):
        destination = self.target / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text)

    def add_patch(self, name, before, after, dependencies=None):
        directory = self.root / 'patches' / name
        directory.mkdir(parents=True)
        (directory / 'README.md').write_text(f'# {name}\n')
        (directory / 'changes.patch').write_text(
            'diff --git a/file.txt b/file.txt\n--- a/file.txt\n+++ b/file.txt\n'
            f'@@ -1 +1 @@\n-{before}\n+{after}\n')
        entry = {'id': name, 'status': 'keep', 'depends_on': dependencies or [],
                 'patch': f'patches/{name}/changes.patch', 'paths': ['file.txt'],
                 'tests': f'patches/{name}/tests.json'}
        self.manifest['patches'].append(entry)
        self.set_checks(entry, [{'name': 'content contract', 'tier': 'focused', 'cwd': '.',
                                'requires': ['file.txt'], 'command': [sys.executable, '-c',
                                "from pathlib import Path; assert Path('file.txt').read_text() == 'second\\n'"]}])
        return entry

    def set_checks(self, entry, checks):
        (self.root / entry['tests']).write_text(json.dumps({'checks': checks}))

    def save(self):
        (self.root / 'manifest.json').write_text(json.dumps(self.manifest))

    def cli(self, action, *args, target=None):
        return subprocess.run([sys.executable, str(CLI), '--root', str(self.root), action,
                               '--target', str(target or self.target), *args],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def assert_clean(self):
        self.assertEqual(self.git('status', '--porcelain'), b'')
        self.assertEqual((self.target / 'file.txt').read_text(), 'base\n')

    def test_selection_includes_transitive_dependencies_once_in_manifest_order(self):
        self.add_patch('third', 'second', 'third', ['second'])
        chosen = patchset.select(self.manifest, ['third', 'first', 'third'])
        self.assertEqual([p['id'] for p in chosen], ['first', 'second', 'third'])
        self.manifest['patches'][2]['status'] = 'local'
        self.assertEqual(patchset.select(self.manifest, statuses=['local']), chosen)
        with self.assertRaisesRegex(patchset.Failure, 'Unknown patch ids'):
            patchset.select(self.manifest, ['typo'])
        self.save()
        result = self.cli('apply', '--only', 'third')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.target / 'file.txt').read_text(), 'third\n')

    def test_check_preserves_target_and_apply_stages_complete_selection(self):
        result = self.cli('check', '--only', 'second')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_clean()
        result = self.cli('apply', '--only', 'second')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.target / 'file.txt').read_text(), 'second\n')
        self.assertEqual(self.git('show', ':file.txt'), b'second\n')
        self.assertEqual(self.git('rev-parse', 'HEAD').decode().strip(), self.base)
        duplicate = self.cli('apply')
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn('Repeated application is refused', duplicate.stderr)
        self.assertEqual((self.target / 'file.txt').read_text(), 'second\n')

    def test_later_conflict_does_not_leave_earlier_changes(self):
        path = self.root / self.manifest['patches'][1]['patch']
        path.write_text(path.read_text().replace('-first\n', '-not-the-base\n'))
        for action in ('check', 'apply'):
            with self.subTest(action=action):
                result = self.cli(action)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Preflight stopped at second', result.stderr)
                self.assert_clean()

    def test_dirty_index_worktree_and_untracked_files_are_preserved(self):
        self.write('file.txt', 'staged user work\n')
        self.git('add', 'file.txt')
        self.write('file.txt', 'unstaged user work\n')
        self.write('untracked.txt', 'untracked user work\n')
        before = self.git('status', '--porcelain')
        result = self.cli('apply')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Target has changes', result.stderr)
        self.assertEqual(self.git('status', '--porcelain'), before)
        self.assertEqual(self.git('show', ':file.txt'), b'staged user work\n')
        self.assertEqual((self.target / 'file.txt').read_text(), 'unstaged user work\n')
        self.assertEqual((self.target / 'untracked.txt').read_text(), 'untracked user work\n')

    def test_wrong_base_is_refused_without_switching_head(self):
        self.git('commit', '--allow-empty', '-qm', 'different base')
        head = self.git('rev-parse', 'HEAD')
        result = self.cli('apply')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('differs from fixed base', result.stderr)
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        self.assert_clean()

    def test_inventory_mismatch_and_duplicate_ids_are_rejected(self):
        self.manifest['patches'][1]['paths'] = ['other.txt']
        self.save()
        result = self.cli('apply')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Payload path inventory differs', result.stderr)
        self.assert_clean()
        self.manifest['patches'].append(copy.deepcopy(self.manifest['patches'][0]))
        self.save()
        with self.assertRaisesRegex(patchset.Failure, 'Duplicate id'):
            patchset.load_manifest(self.root)

    def test_dependency_order_and_empty_contract_are_rejected(self):
        self.manifest['patches'].reverse()
        self.save()
        with self.assertRaisesRegex(patchset.Failure, 'out-of-order dependency'):
            patchset.load_manifest(self.root)
        self.manifest['patches'].reverse()
        self.set_checks(self.manifest['patches'][0], [])
        self.save()
        with self.assertRaisesRegex(patchset.Failure, 'Empty test contract'):
            patchset.load_manifest(self.root)

    def test_skip_requires_documented_replacement_in_selected_target(self):
        entry = self.manifest['patches'][0]
        entry.update(status='upstream', patch=None, paths=[],
                     replacement={'commit': self.base, 'evidence': 'reviewed base helper'})
        self.save()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(patchset.applicable(self.target, [entry]), [])
        entry['replacement']['evidence'] = ''
        self.save()
        with self.assertRaisesRegex(patchset.Failure, 'Replacement evidence missing'):
            patchset.load_manifest(self.root)
        entry['replacement'].update(commit='0' * 40, evidence='absent commit')
        with self.assertRaises(patchset.Failure):
            patchset.applicable(self.target, [entry])
        self.assert_clean()

    def test_generate_is_independent_repeatable_and_protects_edits(self):
        generated = self.target.parent / 'generated'
        result = self.cli('generate', '--source', str(self.target), target=generated)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((generated / '.git').is_dir())
        self.assertEqual((generated / 'file.txt').read_text(), 'second\n')
        for action in ('generate', 'verify', 'test'):
            result = self.cli(action, target=generated)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_clean()
        (generated / 'file.txt').write_text('user edit\n')
        result = self.cli('generate', target=generated)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((generated / 'file.txt').read_text(), 'user edit\n')
        subprocess.run(['git', '-C', str(generated), 'add', 'file.txt'], check=True)
        result = self.cli('generate', target=generated)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('differs from manifest tree', result.stderr)
        self.assertEqual((generated / 'file.txt').read_text(), 'user edit\n')

    def test_failed_generation_does_not_expose_partial_target(self):
        path = self.root / self.manifest['patches'][1]['patch']
        path.write_text(path.read_text().replace('-first\n', '-conflict\n'))
        generated = self.target.parent / 'generated'
        result = self.cli('generate', target=generated)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Preflight stopped at second', result.stderr)
        self.assertFalse(generated.exists())
        self.assert_clean()

    def test_verify_refuses_extra_untracked_work(self):
        self.assertEqual(self.cli('apply').returncode, 0)
        self.write('untracked.txt', 'user work\n')
        result = self.cli('verify')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('untracked files', result.stderr)
        self.assertEqual((self.target / 'untracked.txt').read_text(), 'user work\n')

    def test_apply_preserves_ignored_file_collision_without_partial_changes(self):
        entry = self.manifest['patches'][1]
        entry['paths'].append('ignored.txt')
        with (self.root / entry['patch']).open('a') as patch:
            patch.write('diff --git a/ignored.txt b/ignored.txt\nnew file mode 100644\n'
                        '--- /dev/null\n+++ b/ignored.txt\n@@ -0,0 +1 @@\n+new file\n')
        self.save()
        self.write('ignored.txt', 'user data\n')
        result = self.cli('apply')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.target / 'ignored.txt').read_text(), 'user data\n')
        self.assert_clean()

    def test_command_uses_application_cwd_deduplicates_and_propagates_failure(self):
        check = {'name': 'cwd contract', 'tier': 'focused', 'cwd': 'web',
                 'requires': ['web/check.test.ts'], 'command': [sys.executable, '-c',
                 "from pathlib import Path; assert Path('check.test.ts').is_file(); print('executed once')"]}
        for entry in self.manifest['patches']:
            self.set_checks(entry, [check])
        self.assertEqual(self.cli('apply').returncode, 0)
        result = self.cli('test')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count('executed once'), 1)
        check['command'] = [sys.executable, '-c', 'raise SystemExit(9)']
        self.set_checks(self.manifest['patches'][0], [check])
        result = self.cli('test')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('exit status 9', result.stderr)
        result = self.cli('test', '--tier', 'project')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('No checks in tier', result.stderr)
        check['requires'] = ['missing.go']
        self.set_checks(self.manifest['patches'][0], [check])
        result = self.cli('test')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('entry missing', result.stderr)

    def test_paths_cannot_escape_checkout(self):
        for path in ('../outside', '/absolute'):
            with self.assertRaises(patchset.Failure):
                patchset.inside(self.target, path)
        (self.target / 'escape').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(patchset.Failure):
            patchset.inside(self.target, 'escape/manifest.json')


if __name__ == '__main__':
    unittest.main()
