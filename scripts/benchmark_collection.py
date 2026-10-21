"""Replay fixed public HTML against isolated baseline/current CLI processes."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import random
import re
from statistics import median
import subprocess
import sys
import tempfile
from time import perf_counter
from urllib.parse import parse_qs, urlsplit


ROOT = Path(__file__).resolve().parents[1]
COMMANDS = {
    'list': ['list', '--sort', 'id', '--order', 'asc', '--limit', '1'],
    'recommend': ['recommend', '--count', '1'],
}


def _git(*args: str) -> str:
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True, encoding='utf-8').strip()


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _worker(args: argparse.Namespace) -> None:
    source_root = args.source_root.resolve()
    fixtures = args.fixtures.resolve()
    sys.path.insert(0, str(source_root))
    from typer.testing import CliRunner
    from algorithm_problem_picker import cli, jungol, models, service

    imports = {module.__name__: str(Path(module.__file__).resolve()) for module in (cli, jungol, models, service)}
    if not all(Path(path).is_relative_to(source_root) for path in imports.values()):
        raise RuntimeError(f'Wrong source import: {imports}')
    sample = {
        'command': args.command, 'label': args.label, 'imports': imports,
        'python': sys.version, 'executable': sys.executable,
        'dependencies': {name: version(name) for name in ('typer','rich','playwright','pytest')},
        'detail_requests': 0, 'blocked_requests': [], 'listing_seconds': 0,
    }
    original_enter = jungol.JungolSource.__enter__
    original_collect = jungol.JungolSource.collect
    original_list = service.Picker.list
    original_recommend = service.Picker.recommend

    def route(request):
        url = urlsplit(request.request.url)
        # Images are deliberately not loaded; DOM src attributes remain intact.
        if request.request.resource_type not in {'document','xhr','fetch'}:
            request.abort()
            return
        detail = re.fullmatch(r'/problem/([1-9][0-9]*)', url.path)
        if url.scheme == 'https' and url.netloc == 'jungol.co.kr' and detail:
            sample['detail_requests'] += 1
            name = f'detail-{detail[1]}.html'
            if args.label != 'baseline':
                sample['blocked_requests'].append(request.request.url)
                request.abort()
                return
        elif url.scheme == 'https' and url.netloc == 'jungol.co.kr' and url.path == '/problem':
            params = parse_qs(url.query, keep_blank_values=True)
            expected = {'type':['problem'],'sort':['idAsc'],'unrated':['include']}
            if any(params.get(k) != v for k,v in expected.items()) or set(params) - {*expected,'page'}:
                sample['blocked_requests'].append(request.request.url)
                request.abort()
                return
            page = params.get('page',['1'])
            name = f'page-{page[0]}.html' if len(page) == 1 else ''
        else:
            name = ''
        path = fixtures / name
        if not path.is_file():
            sample['blocked_requests'].append(request.request.url)
            request.abort()
            return
        request.fulfill(content_type='text/html; charset=utf-8', body=path.read_text(encoding='utf-8'))

    def enter(source):
        result = original_enter(source)
        sample['browser'] = source._browser.version
        source._context.route('**/*', route)
        return result

    def collect(source, criteria, user):
        started = perf_counter()
        listing = original_collect(source, criteria, user)
        sample['listing_seconds'] += perf_counter() - started
        sample['candidate_ids'] = sorted(p.id for p in listing.candidates)
        return listing

    def observe(method):
        def invoke(picker, *positional, **kwargs):
            result = method(picker, *positional, **kwargs)
            sample.update(fetched=result.fetched_count, eligible=result.eligible_count,
                          returned=result.returned_count, shortage=result.shortage,
                          selected_ids=[p.id for p in result.problems])
            # The commands have no filters: every observed candidate is eligible.
            if result.eligible_count != len(sample['candidate_ids']):
                raise RuntimeError('Unfiltered eligible population differs from collected IDs')
            sample['eligible_ids'] = sample['candidate_ids']
            return result
        return invoke

    jungol.JungolSource.__enter__ = enter
    jungol.JungolSource.collect = collect
    service.Picker.list = observe(original_list)
    service.Picker.recommend = observe(original_recommend)
    random.seed(20261021)
    runner = CliRunner()
    started = perf_counter()
    result = runner.invoke(cli.app, COMMANDS[args.command])
    sample['total_seconds'] = perf_counter() - started
    sample.update(exit_code=result.exit_code, stdout=result.stdout, stderr=result.stderr)
    if result.exception:
        sample['exception'] = repr(result.exception)
    print(json.dumps(sample, ensure_ascii=True))


def _failures(samples: list[dict], runs: int) -> list[str]:
    failures = []
    expected_ids = [1000,1001,1002,1003]
    groups = defaultdict(list)
    for sample in samples:
        groups[sample['command'],sample['label']].append(sample)
        label = f"{sample['command']}/{sample['label']}/{sample['run']}"
        if sample.get('exit_code') != 0 or sample.get('blocked_requests'):
            failures.append(f'{label}: command failed or unexpected request blocked')
        if sample.get('candidate_ids') != expected_ids or sample.get('eligible_ids') != expected_ids:
            failures.append(f'{label}: candidate/eligible IDs differ from fixed population')
        if (sample.get('fetched'),sample.get('eligible'),sample.get('returned'),sample.get('shortage')) != (4,4,1,0):
            failures.append(f'{label}: result counts differ')
        details = sample.get('detail_requests',0)
        if (sample['label'] == 'baseline' and details != 4) or (sample['label'] == 'current' and details != 0):
            failures.append(f'{label}: invalid detail request count {details}')
        if sample['command'] == 'list' and sample.get('selected_ids') != [1000]:
            failures.append(f'{label}: unexpected list order')
        if not set(sample.get('selected_ids',[])) <= set(expected_ids):
            failures.append(f'{label}: selected ID outside population')
    for command in COMMANDS:
        baseline = groups[command,'baseline']
        current = groups[command,'current']
        if len(baseline) != runs or len(current) != runs:
            failures.append(f'{command}: missing runs')
        elif median(s['total_seconds'] for s in current) >= median(s['total_seconds'] for s in baseline):
            failures.append(f'{command}: current total median did not decrease')
    return failures


def _report(metadata: dict, samples: list[dict], failures: list[str]) -> str:
    lines = ['# Local collection replay benchmark', '',
             '고정 HTML 로컬 재생 결과다. 실사이트의 개선율로 일반화하지 않는다.', '',
             'CLI import 후 명령 호출 직전부터 출력·브라우저 정리까지 전체 시간을 측정했다. '
             '별도 프로세스 시작/import 시간은 제외한다. 제품의 기본 1초 시작 간격과 30초/15초 제한을 유지했다.', '',
             '## Environment and source identity', '', '```json',
             json.dumps(metadata,ensure_ascii=False,indent=2), '```', '',
             '## Raw timings', '',
             '| Command | Version | Run | Fetched/eligible/returned | Detail requests | Total seconds | Collect seconds |',
             '| --- | --- | ---: | --- | ---: | ---: | ---: |']
    for sample in samples:
        lines.append(f"| {sample['command']} | {sample['label']} | {sample['run']} | "
                     f"{sample.get('fetched')}/{sample.get('eligible')}/{sample.get('returned')} | "
                     f"{sample.get('detail_requests')} | {sample['total_seconds']:.6f} | {sample.get('listing_seconds',0):.6f} |")
    lines += ['', '## Medians', '', '| Command | Version | Total seconds | Collect seconds |',
              '| --- | --- | ---: | ---: |']
    for command in COMMANDS:
        for label in ('baseline','current'):
            group = [s for s in samples if s['command'] == command and s['label'] == label]
            if group:
                lines.append(f"| {command} | {label} | {median(s['total_seconds'] for s in group):.6f} | "
                             f"{median(s.get('listing_seconds',0) for s in group):.6f} |")
    lines += ['', '## Verdict', '', 'FAIL' if failures else 'PASS', '']
    lines += [f'- {failure}' for failure in failures]
    if metadata['runs'] < 3:
        lines += ['Smoke run only; SC-008 requires at least three runs per version and command.']
    lines += ['', '## Full samples (import paths, output and diagnostics)', '', '```json',
              json.dumps(samples,ensure_ascii=False,indent=2),'```','']
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-ref', default='c37208f5a80628df5d7126972d31461b2517177d')
    parser.add_argument('--runs',type=int,default=3)
    parser.add_argument('--output',type=Path,default=ROOT/'specs/002-improve-list-collection/collection-benchmark.md')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--source-root',type=Path,help=argparse.SUPPRESS)
    parser.add_argument('--fixtures',type=Path,default=ROOT/'tests/fixtures/jungol/benchmark',help=argparse.SUPPRESS)
    parser.add_argument('--command',choices=COMMANDS,help=argparse.SUPPRESS)
    parser.add_argument('--label',choices=['baseline','current'],help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        _worker(args)
        return 0
    if args.runs < 1:
        parser.error('--runs must be positive')
    fixtures = args.fixtures.resolve()
    baseline_ref = _git('rev-parse','--verify',f'{args.baseline_ref}^{{commit}}')
    dirty = _git('status','--porcelain')
    metadata = {
        'measured_at':datetime.now(timezone.utc).isoformat(), 'platform':platform.platform(),
        'python':sys.version, 'executable':sys.executable, 'runs':args.runs,
        'baseline_revision':baseline_ref, 'baseline_dirty':False,
        'current_revision':_git('rev-parse','HEAD'), 'current_dirty':bool(dirty),'current_status':dirty,
        'commands':COMMANDS, 'fixture_root':str(fixtures),
        'fixture_sha256':{p.name:_hash(p) for p in sorted(fixtures.glob('*.html'))},
        'harness_path':str(Path(__file__).resolve()), 'harness_sha256':_hash(Path(__file__)),
        'lock_sha256':_hash(ROOT/'uv.lock'),
        'current_source_sha256':{p.name:_hash(p) for p in sorted((ROOT/'src/algorithm_problem_picker').glob('*.py'))},
        'dependencies':{name:version(name) for name in ('typer','rich','playwright','pytest')},
    }
    samples = []
    with tempfile.TemporaryDirectory(prefix='jpick-benchmark-') as temporary:
        checkout = Path(temporary)/'baseline'
        for relative in _git('ls-tree','-r','--name-only',baseline_ref,'--','src/algorithm_problem_picker').splitlines():
            path = checkout/relative
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(subprocess.check_output(['git','-C',str(ROOT),'show',f'{baseline_ref}:{relative}']))
        # Alternate versions to reduce systematic order effects.
        for command in COMMANDS:
            for run in range(1,args.runs+1):
                for label,source_root in [('baseline',checkout/'src'),('current',ROOT/'src')]:
                    process = subprocess.run([
                        sys.executable,'-u',str(Path(__file__).resolve()),'--worker',
                        '--source-root',str(source_root.resolve()),'--fixtures',str(fixtures),
                        '--command',command,'--label',label,
                    ],cwd=temporary,capture_output=True,text=True,encoding='utf-8',timeout=180)
                    if process.returncode:
                        sample = dict(command=command,label=label,exit_code=process.returncode,
                                      total_seconds=0,listing_seconds=0,exception=process.stderr)
                    else:
                        sample = json.loads(process.stdout)
                    sample['run'] = run
                    samples.append(sample)
                    print(f"{command}/{label}/{run}: exit={sample['exit_code']} total={sample['total_seconds']:.3f}s",flush=True)
    failures = _failures(samples,args.runs)
    args.output.resolve().write_text(_report(metadata,samples,failures),encoding='utf-8')
    print(f"{'FAIL' if failures else 'PASS'}: {args.output.resolve()}",flush=True)
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
