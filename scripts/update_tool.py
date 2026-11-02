"""Update a Git submodule checkout and prepare its local runtime."""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description='algo-pick submodule의 소스, uv 환경, Chromium을 순서대로 업데이트합니다.')
    parser.parse_args()
    for command in ('git', 'uv'):
        if shutil.which(command) is None:
            print(f'업데이트 실패: {command} 명령을 설치하고 PATH를 확인하세요.', file=sys.stderr)
            return 1
    if not (ROOT / '.git').exists():
        print('업데이트 실패: Git submodule 설치본에서 실행하세요. 독립 복사본은 자동 갱신할 수 없습니다.',
              file=sys.stderr)
        return 1
    try:
        parent = subprocess.run(
            ['git', '-C', str(ROOT), 'rev-parse', '--show-superproject-working-tree'],
            check=True, capture_output=True, text=True, encoding='utf-8').stdout.strip()
        if not parent:
            print('업데이트 실패: Git submodule 설치본에서 실행하세요. 일반 clone은 git pull로 갱신하세요.',
                  file=sys.stderr)
            return 1
        project = Path(parent).resolve()
        relative = ROOT.relative_to(project).as_posix()
        steps = (
            ('소스 갱신', ['git', '-C', str(project), 'submodule', 'update', '--init', '--remote', '--', relative]),
            ('실행 환경 동기화', ['uv', '--directory', str(ROOT), 'sync', '--locked', '--no-dev']),
            ('Chromium 설치', ['uv', '--directory', str(ROOT), 'run', '--locked', '--no-dev',
                              'playwright', 'install', 'chromium']),
        )
        for index, (label, command) in enumerate(steps, start=1):
            print(f'[{index}/{len(steps)}] {label}', flush=True)
            subprocess.run(command, check=True)
    except subprocess.CalledProcessError as error:
        print(f'업데이트 실패: 명령 종료 코드 {error.returncode}. 오류를 해결한 뒤 다시 실행하세요.',
              file=sys.stderr)
        if error.stderr:
            print(error.stderr, file=sys.stderr)
        return error.returncode
    except OSError as error:
        print(f'업데이트 실패: {error}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('업데이트를 취소했습니다.', file=sys.stderr)
        return 130
    print(f'업데이트 완료: {ROOT}')
    print('외부 프로젝트에서 변경된 submodule 커밋 참조를 확인하고 커밋하세요.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
