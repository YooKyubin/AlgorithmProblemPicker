import importlib.util
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _git(directory, *arguments):
    return subprocess.run(['git', '-C', str(directory), *arguments], check=True,
                          capture_output=True, text=True, encoding='utf-8').stdout.strip()


@pytest.fixture
def updater(monkeypatch):
    spec = importlib.util.spec_from_file_location('update_tool', ROOT / 'scripts/update_tool.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr('sys.argv', ['update_tool.py'])
    monkeypatch.setattr(module.shutil, 'which', lambda command: command)
    return module


@pytest.fixture
def checkout(tmp_path, monkeypatch, updater):
    monkeypatch.setenv('GIT_ALLOW_PROTOCOL', 'file')
    monkeypatch.setenv('GIT_AUTHOR_NAME', 'Update test')
    monkeypatch.setenv('GIT_AUTHOR_EMAIL', 'update@example.invalid')
    monkeypatch.setenv('GIT_COMMITTER_NAME', 'Update test')
    monkeypatch.setenv('GIT_COMMITTER_EMAIL', 'update@example.invalid')
    upstream = tmp_path / 'upstream'
    upstream.mkdir()
    _git(upstream, 'init', '-b', 'main')
    (upstream / 'release.txt').write_text('initial', encoding='utf-8')
    _git(upstream, 'add', 'release.txt')
    _git(upstream, 'commit', '-m', 'Initial release')
    project = tmp_path / '외부 project'
    project.mkdir()
    _git(project, 'init')
    _git(project, 'submodule', 'add', str(upstream), 'tools/algo-pick')
    (upstream / 'release.txt').write_text('updated', encoding='utf-8')
    _git(upstream, 'commit', '-am', 'New release')
    tool = project / 'tools/algo-pick'
    monkeypatch.setattr(updater, 'ROOT', tool)
    return tool


@pytest.mark.parametrize('fail_sync', [False, True])
def test_update_fetches_source_and_stops_on_runtime_failure(checkout, updater, monkeypatch, fail_sync):
    run = subprocess.run
    runtime_calls = []

    def run_command(command, **kwargs):
        if command[0] != 'uv':
            return run(command, **kwargs)
        runtime_calls.append(command)
        if fail_sync:
            raise subprocess.CalledProcessError(7, command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(updater.subprocess, 'run', run_command)
    assert updater.main() == (7 if fail_sync else 0)
    assert (checkout / 'release.txt').read_text(encoding='utf-8') == 'updated'
    assert len(runtime_calls) == (1 if fail_sync else 2)
    assert all(command[1:3] == ['--directory', str(checkout)] for command in runtime_calls)


def test_update_preserves_conflicting_local_changes(checkout, updater, monkeypatch):
    (checkout / 'release.txt').write_text('local edit', encoding='utf-8')
    run = subprocess.run

    def run_command(command, **kwargs):
        assert command[0] != 'uv', 'A failed source update must not change the runtime.'
        return run(command, **kwargs)

    monkeypatch.setattr(updater.subprocess, 'run', run_command)
    assert updater.main() != 0
    assert (checkout / 'release.txt').read_text(encoding='utf-8') == 'local edit'


@pytest.mark.parametrize('git_checkout', [False, True])
def test_update_rejects_non_submodule_installations(tmp_path, updater, monkeypatch, git_checkout):
    if git_checkout:
        _git(tmp_path, 'init')
    monkeypatch.setattr(updater, 'ROOT', tmp_path)
    run = subprocess.run

    def run_command(command, **kwargs):
        assert 'update' not in command and command[0] != 'uv'
        return run(command, **kwargs)

    monkeypatch.setattr(updater.subprocess, 'run', run_command)
    assert updater.main() == 1
