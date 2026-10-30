"""Export a source snapshot for use inside another project (standard library only)."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRECTORIES = {'.venv', '__pycache__'}


def _source_revision() -> tuple[str | None, bool | None]:
    if not (ROOT / '.git').exists():
        return None, None
    commit = subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True, encoding='utf-8').strip()
    status = subprocess.check_output(
        ['git', '-C', str(ROOT), 'status', '--porcelain', '--untracked-files=all'],
        text=True, encoding='utf-8')
    return commit, bool(status.strip())


def export_tool(target: Path) -> Path:
    target = target.expanduser()
    if target.exists() or target.is_symlink():
        raise ValueError(f'대상 경로가 이미 존재합니다. 덮어쓰지 않습니다: {target}')
    target = target.resolve()
    if target.is_relative_to(ROOT) and not target.is_relative_to(ROOT / 'dist'):
        raise ValueError('원본 저장소 내부로 내보낼 때는 dist/ 아래의 새 경로를 사용하세요.')

    files = {
        'pyproject.toml': (ROOT / 'pyproject.toml').read_bytes(),
        'uv.lock': (ROOT / 'uv.lock').read_bytes(),
        '.python-version': (ROOT / '.python-version').read_bytes(),
        'README.md': (ROOT / 'docs' / 'standalone.md').read_bytes(),
        'vscode-tasks.example.json': (ROOT / 'examples' / 'vscode' / 'tasks.json').read_bytes(),
        '.gitignore': b'.venv/\n__pycache__/\n*.py[cod]\n',
    }
    source_root = ROOT / 'src'
    # Fail before creating the target if this is not a complete source distribution.
    (source_root / 'algorithm_problem_picker' / '__init__.py').read_bytes()
    for path in sorted(source_root.rglob('*')):
        relative = path.relative_to(source_root)
        if any(part in IGNORED_DIRECTORIES or part.endswith('.egg-info') for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError(f'소스의 심볼릭 링크는 내보낼 수 없습니다: {relative}')
        if path.is_file() and path.suffix not in {'.pyc', '.pyo', '.pyd'}:
            files[f'src/{relative.as_posix()}'] = path.read_bytes()

    project = tomllib.loads(files['pyproject.toml'].decode('utf-8'))['project']
    commit, dirty = _source_revision()
    manifest = {
        'schema_version': 1,
        'project': project['name'],
        'version': project['version'],
        'source_commit': commit,
        'source_dirty': dirty,
        'exported_at': datetime.now(timezone.utc).isoformat(),
        'files': {name: hashlib.sha256(content).hexdigest() for name, content in sorted(files.items())},
    }
    files['export-manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')

    # mkdir refuses an existing target even if it appeared after the initial check.
    target.mkdir(parents=True, exist_ok=False)
    for name, content in files.items():
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as stream:
            stream.write(content)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description='jpick 소스와 실행 설정을 다른 프로젝트용 폴더로 복사합니다.')
    parser.add_argument('--target', type=Path, required=True, help='새로 만들 대상 폴더 (예: ../algorithm/tools/jpick)')
    args = parser.parse_args()
    try:
        target = export_tool(args.target)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'내보내기 실패: {error}', file=sys.stderr)
        return 1
    print(f'내보내기 완료: {target}')
    print('다음 단계: 복사본의 README.md에 따라 실행 환경과 Chromium을 설치하세요.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
