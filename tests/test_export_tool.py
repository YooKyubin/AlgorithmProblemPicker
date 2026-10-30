import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def source_archive(tmp_path):
    root = tmp_path / 'source archive'
    for name in ('scripts/export_tool.py', 'pyproject.toml', 'uv.lock', '.python-version',
                 'docs/standalone.md', 'examples/vscode/tasks.json'):
        destination = root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    package = root / 'src' / 'algorithm_problem_picker'
    package.mkdir(parents=True)
    (package / '__init__.py').write_text('"""Export fixture."""\n', encoding='utf-8')
    (package / 'data.json').write_text('{"preserve": true}', encoding='utf-8')
    cache = package / '__pycache__'
    cache.mkdir()
    (cache / '__init__.cpython-312.pyc').write_bytes(b'cache')
    (package / 'old.pyc').write_bytes(b'cache')
    (root / '.venv').mkdir()
    (root / '.venv' / 'not-for-export').write_bytes(b'local environment')
    return root


def _export(root, target):
    return subprocess.run([sys.executable, '-X', 'utf8', str(root / 'scripts' / 'export_tool.py'),
                           '--target', str(target)], capture_output=True, text=True, encoding='utf-8')


def test_export_archive_preserves_payload_and_records_integrity(source_archive, tmp_path):
    target = tmp_path / '풀이 project' / 'tools' / 'algo-pick'
    result = _export(source_archive, target)
    assert result.returncode == 0, result.stderr
    assert (target / 'src/algorithm_problem_picker/data.json').read_bytes() == b'{"preserve": true}'
    assert not (target / '.venv').exists()
    assert not (target / 'src/algorithm_problem_picker/__pycache__').exists()
    assert not (target / 'src/algorithm_problem_picker/old.pyc').exists()
    assert not (target / 'scripts').exists()
    assert not (target / 'tests').exists()
    manifest = json.loads((target / 'export-manifest.json').read_text(encoding='utf-8'))
    assert manifest['source_commit'] is None and manifest['source_dirty'] is None
    project = tomllib.loads((source_archive / 'pyproject.toml').read_text(encoding='utf-8'))['project']
    assert manifest['version'] == project['version']
    assert project['scripts'] == {'algo-pick': 'algorithm_problem_picker.cli:app'}
    exported = {path.relative_to(target).as_posix(): path for path in target.rglob('*') if path.is_file()}
    assert set(manifest['files']) == set(exported) - {'export-manifest.json'}
    for name, digest in manifest['files'].items():
        assert hashlib.sha256(exported[name].read_bytes()).hexdigest() == digest
    for name in ('pyproject.toml', 'uv.lock', '.python-version'):
        assert (target / name).read_bytes() == (source_archive / name).read_bytes()
    assert (target / 'README.md').read_bytes() == (source_archive / 'docs/standalone.md').read_bytes()
    assert (target / 'vscode-tasks.example.json').read_bytes() == (
        source_archive / 'examples/vscode/tasks.json').read_bytes()


@pytest.mark.parametrize('with_content', [False, True])
def test_existing_target_is_never_modified(source_archive, tmp_path, with_content):
    target = tmp_path / 'existing'
    target.mkdir()
    if with_content:
        (target / 'keep.txt').write_bytes(b'do not overwrite')
    result = _export(source_archive, target)
    assert result.returncode == 1
    assert '덮어쓰지 않습니다' in result.stderr
    assert sorted(path.name for path in target.iterdir()) == (['keep.txt'] if with_content else [])
    if with_content:
        assert (target / 'keep.txt').read_bytes() == b'do not overwrite'


def test_missing_required_file_fails_before_creating_target(source_archive, tmp_path):
    (source_archive / 'uv.lock').unlink()
    target = tmp_path / 'incomplete'
    result = _export(source_archive, target)
    assert result.returncode == 1
    assert not target.exists()


def test_vscode_template_connects_inputs_and_uses_relative_project_path():
    template = json.loads((ROOT / 'examples/vscode/tasks.json').read_text(encoding='utf-8'))
    inputs = {entry['id'] for entry in template['inputs']}
    referenced = set()
    for task in template['tasks']:
        assert task['type'] == 'process' and task['command'] == 'uv'
        directory = task['args'].index('--directory')
        assert task['args'][directory + 1] == '${workspaceFolder}/tools/algo-pick'
        if task['label'] != '정올: 설치':
            command = task['args'].index('algo-pick')
            assert task['args'][command + 1:command + 3] == ['--platform', 'jungol']
            assert task['args'][command + 3] in {'list', 'recommend'}
        for arg in task['args']:
            if arg.startswith('${input:'):
                referenced.add(arg[len('${input:'):-1])
    assert referenced == inputs
