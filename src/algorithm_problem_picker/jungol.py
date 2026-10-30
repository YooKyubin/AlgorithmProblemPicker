"""Sequential, nonpersistent browsing of JUNGOL's rendered public DOM."""

from collections.abc import Callable
from decimal import Decimal, InvalidOperation
import re
import time
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit

from playwright.sync_api import Browser, BrowserContext, Error, JSHandle, Page, Request, sync_playwright

from .jungol_models import Problem, Rated, SearchCriteria, Status, Unrated, UserReference
from .models import CompletedListing, Known, Unavailable, now
from .ports import SourceAccessError, SourceCompletenessError, SourceSchemaError, UserResolutionError


_ORIGIN = "https://jungol.co.kr"
_EMPTY = {"-", "—", "미확인", "미제공"}

# Only DOM is inspected, never application globals or serialized state.
_SNAPSHOT = r"""() => {
    const visible = e => !!e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';
    const texts = selector => [...document.querySelectorAll(selector)].filter(visible).map(e => e.innerText.trim());
    const text = document.querySelector('article')?.innerText || document.body.innerText;
    const tables = [...document.querySelectorAll('article table')].filter(t =>
        [...t.querySelectorAll('th')].some(e => e.innerText.trim() === '문제') &&
        [...t.querySelectorAll('th')].some(e => e.innerText.trim() === '정답률'));
    const rows = tables.flatMap(t => [...t.querySelectorAll('tbody tr')])
        .map(r => {
            const cell = r.querySelector('td[data-col="문제"]');
            const rateCells = [...r.querySelectorAll('td[data-col="정답률"]')];
            const acceptedCells = [...r.querySelectorAll('td[data-col="정답"]')];
            return {
                links: [...(cell?.querySelectorAll('a') || [])].map(a => ({
                    href: a.getAttribute('href'),
                    titles: [...a.querySelectorAll('.title')].map(e => e.innerText.trim()),
                    tiers: [...a.querySelectorAll('img')].map(e => e.getAttribute('src')),
                    missingTier: a.querySelectorAll('[title="난이도 미확인"]').length,
                    unrated: a.matches('.pl-row-link') && !a.querySelector('.pl-card-tier') &&
                             !a.querySelector('img') && !a.querySelector('[title="난이도 미확인"]') && !!a.querySelector('.title')
                })),
                rates: rateCells.map(e => e.innerText.trim()),
                accepted: acceptedCells.map(e => e.innerText.trim()),
                rateEmpty: rateCells.map(e => e.hasAttribute('data-col-empty')),
                acceptedEmpty: acceptedCells.map(e => e.hasAttribute('data-col-empty')),
                rateLinks: [...r.querySelectorAll('td[data-col="정답률"] a')].map(a=>a.getAttribute('href')),
                regular: !!r.querySelector('[aria-label="일반 문제"]')
            };
        });
    const next = [...document.querySelectorAll('article a')].filter(visible).filter(a =>
        a.rel === 'next' || a.getAttribute('aria-label') === '다음 페이지' || a.innerText.trim() === '다음');
    const more = [...document.querySelectorAll('article button')].filter(visible).filter(b =>
        /^(더 불러오기|불러오는 중[.\s…]*|로딩 중[.\s…]*)$/.test(b.innerText.trim()));
    return {rows, tableCount: tables.length, next: next.map(a => a.getAttribute('href')),
        more: more.length, moreDisabled: more.some(b => b.disabled),
        busy: !!document.querySelector('article[aria-busy="true"], article [aria-busy="true"]') ||
              /(^|\n)\s*(로딩 중|불러오는 중)[.\s…]*(\n|$)/.test(text),
        empty: /(^|\n)\s*(조건에 맞는 문제가 없어요\.?|검색 결과가 없습니다\.?|문제가 없습니다\.?|결과가 없습니다\.?|조회된 문제가 없습니다\.?)\s*(\n|$)/.test(text),
        errors: texts('[role="alert"]').filter(Boolean), headings: texts('h1'), gates: texts('[role="dialog"]'),
        challenge: /verify you are human|checking your browser|보안 확인|접근이 제한/i.test(
            [...texts('h1'), ...texts('[role="alert"]')].join('\n')) ||
            !!document.querySelector('#challenge-form, #cf-challenge-running, [name="cf-turnstile-response"]') ||
            (!document.querySelector('article') && /verify you are human|checking your browser/i.test(text))
    };
}"""


# Compare public result identities; decorative mutations are not result updates.
_USER_UPDATE = """root => {
    const signature = () => JSON.stringify({
        handles:[...root.querySelectorAll('.jg-find-result h3')].map(e=>
            [...e.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE).map(n=>n.textContent).join('').trim()),
        targets:[...root.querySelectorAll('.jg-find-result button')].map(e=>
            [e.getAttribute('href'),e.getAttribute('onclick')]),
        empty:[...root.querySelectorAll('.jg-find-note')].some(e=>
            /검색 결과가 없습니다|사용자를 찾을 수 없습니다/.test(e.innerText))
    });
    const state = {initial:signature(), changed:false, loading:false, completed:false};
    const observer = new MutationObserver(mutations => {
        state.changed = signature() !== state.initial;
        const note = [...root.querySelectorAll('.jg-find-note')].map(e => e.innerText).join(' ');
        const busy = root.matches('[aria-busy="true"]') ||
                     /검색 중|로딩|불러오는 중/.test(note);
        if ((state.loading && !busy) || mutations.some(m =>
            m.type === 'attributes' && m.target === root && m.attributeName === 'aria-busy' &&
            m.oldValue === 'true' && m.target.getAttribute('aria-busy') !== 'true')) state.completed = true;
        state.loading = busy;
    });
    observer.observe(root, {childList:true, subtree:true, characterData:true,
                            attributes:true, attributeOldValue:true,
                            attributeFilter:['aria-busy','href','onclick']});
    state.observer = observer;
    return state;
}"""


def _empty_statistic(row: dict, metric: str) -> bool:
    if row[metric] != ['']:
        return False
    marker = 'rateEmpty' if metric == 'rates' else 'acceptedEmpty'
    return row[marker] == [True] or (
        metric == 'rates' and len(row['links']) == 1 and row['rateLinks'] == [row['links'][0]['href']]
    )


class JungolSource:
    def __init__(self, report: Callable[[str], None] = lambda _: None):
        self._report = report
        self._last_start = float('-inf')
        self._http_failure = ""
        self._pending: set[Request] = set()
        self._dom_timeout = 15_000

    def __enter__(self) -> "JungolSource":
        self._manager = sync_playwright()
        self._playwright = self._manager.start()
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        try:
            self._browser = self._playwright.chromium.launch(headless=True, handle_sigint=False)
            self._context = self._browser.new_context(locale="ko-KR", viewport={"width":1280, "height":900})
            self._context.set_default_navigation_timeout(30_000)
            self._context.set_default_timeout(self._dom_timeout)
            self._context.on("request", self._request_started)
            self._context.on("requestfinished", self._request_finished)
            self._context.on("requestfailed", self._request_failed)
            self._context.on("response", self._response)
            self._list_page = self._context.new_page()
            return self
        except BaseException as error:
            self.__exit__(type(error), error, error.__traceback__)
            if isinstance(error, Error):
                raise SourceAccessError(f"Chromium 시작 실패: {error}. playwright install chromium을 확인하세요.") from error
            raise

    def __exit__(self, exc_type, exc, traceback) -> None:
        try:
            if self._context:
                try:
                    self._context.close()
                except Error:
                    # A console Ctrl+C can close the driver before Python unwinds.
                    if exc_type is not KeyboardInterrupt or self._browser.is_connected():
                        raise
        finally:
            try:
                if self._browser:
                    try:
                        self._browser.close()
                    except Error:
                        if exc_type is not KeyboardInterrupt or self._browser.is_connected():
                            raise
            finally:
                self._playwright.stop()

    def _relevant(self, request) -> bool:
        return request.resource_type in {"document", "xhr", "fetch"} and urlsplit(request.url).hostname in {
            "jungol.co.kr", "api.jungol.co.kr"
        }

    def _request_started(self, request) -> None:
        if self._relevant(request):
            self._pending.add(request)

    def _request_finished(self, request) -> None:
        self._pending.discard(request)

    def _request_failed(self, request) -> None:
        self._pending.discard(request)
        if self._relevant(request):
            self._http_failure = f"페이지 전송 실패: {request.failure}"

    def _response(self, response) -> None:
        if self._relevant(response.request) and response.status >= 400:
            self._http_failure = f"공개 페이지 접근 실패: HTTP {response.status}"

    def _pace(self) -> None:
        delay = 1 - (time.monotonic() - self._last_start)
        if delay > 0:
            time.sleep(delay)
        self._last_start = time.monotonic()

    def _goto(self, page: Page, url: str) -> None:
        self._pace()
        try:
            response = page.goto(url, wait_until="domcontentloaded")
        except Error as error:
            raise SourceAccessError(f"정올 탐색 실패: {error}") from error
        if response is None or response.status >= 400:
            raise SourceAccessError(f"정올 탐색 실패: HTTP {response.status if response else '응답 없음'}")
        actual = urlsplit(page.url)
        if (actual.scheme, actual.netloc) != ('https','jungol.co.kr') or actual.path.startswith('/auth/'):
            raise SourceAccessError("로그인 또는 다른 사이트로 이동했습니다.")

    def _check_access(self, snapshot: dict) -> None:
        if self._http_failure:
            raise SourceAccessError(self._http_failure)
        if snapshot['challenge'] or any(re.search(r"로그인.*필요|접근.*권한|접근.*제한", text)
                                         for text in snapshot['headings'] + snapshot['errors'] + snapshot['gates']):
            raise SourceAccessError("로그인 요구 또는 접근 제한 화면입니다.")
        if snapshot['errors']:
            raise SourceAccessError("정올 오류: " + "; ".join(snapshot['errors']))

    def _wait_listing(self, previous: set[int] | None = None) -> dict:
        deadline = time.monotonic() + self._dom_timeout / 1000
        last_snapshot = None
        while True:
            snapshot = self._list_page.evaluate(_SNAPSHOT)
            self._check_access(snapshot)
            if len(snapshot['next']) > 1 or snapshot['more'] > 1 or (snapshot['next'] and snapshot['more']):
                raise SourceSchemaError("목록 진행 컨트롤이 중복됩니다.")
            ready = snapshot['rows'] and all(row['regular'] and all(
                len(row[metric]) == 1 and (row[metric][0] or _empty_statistic(row,metric))
                for metric in ('rates','accepted')) for row in snapshot['rows'])
            if previous is not None and not snapshot['more'] and not snapshot['next']:
                if snapshot['tableCount'] != 1 and not snapshot['empty']:
                    raise SourceSchemaError("문제/정답률 헤더가 있는 목록 표를 식별할 수 없습니다.")
                if ready or snapshot['empty']:
                    for row in snapshot['rows']:
                        self._problem(row)
                    return snapshot
            if not snapshot['busy'] and not snapshot['moreDisabled'] and not self._pending:
                if (ready or snapshot['empty']) and snapshot == last_snapshot:
                    if previous is None:
                        return snapshot
                    ids = {self._problem(row).id for row in snapshot['rows']}
                    if snapshot['next'] or ids - previous:
                        return snapshot
            if time.monotonic() >= deadline:
                if not snapshot['busy'] and not self._pending:
                    for row in snapshot['rows']:
                        if previous is None or any(len(row[metric]) != 1 for metric in ('rates','accepted')):
                            self._problem(row)
                error = SourceSchemaError if previous is None else SourceCompletenessError
                raise error("목록 준비 시간 초과 또는 추가 로드 진행 없음. DOM 구조와 접속 상태를 확인하세요.")
            last_snapshot = snapshot
            self._list_page.wait_for_timeout(50)

    def _problem(self, row: dict) -> Problem:
        identity = f"번호 확인 실패, 원시 링크 {row['links']!r}"
        try:
            if len(row['links']) == 1:
                raw = row['links'][0]['href']
                number = re.fullmatch(r'/problem/([1-9][0-9]*)', raw or '')
                if number:
                    identity = f"문제 {number[1]}"
            if len(row['links']) != 1 or len(row['rates']) != 1 or not row['regular']:
                raise ValueError("문제 링크/정답률 열/일반 문제 표시가 없거나 중복됩니다.")
            link = row['links'][0]
            url = urljoin(_ORIGIN, link['href'])
            match = re.fullmatch(r"https://jungol\.co\.kr/problem/([1-9]\d*)", url)
            if not match or len(link['titles']) != 1:
                raise ValueError("제목 또는 문제 URL 구조가 달라졌습니다.")
            if link['missingTier'] and link['tiers']:
                raise ValueError(f"티어 표시 중복: {link['tiers']!r}, 미확인 {link['missingTier']}개")
            if len(link['tiers']) == 1:
                badge = re.search(r"/solved/(\d+)\.svg(?:\?|$)", link['tiers'][0])
                if not badge:
                    raise ValueError(f"알 수 없는 티어 배지: {link['tiers']!r}")
                tier_value = int(badge[1])
                if not 0 <= tier_value <= 30:
                    raise ValueError(f"티어 배지 범위 오류: {link['tiers']!r}")
                tier = Unrated() if tier_value == 0 else Rated(tier_value)
            elif not link['tiers'] and link['missingTier'] == 1:
                tier = Unavailable()
            elif link['unrated']:
                tier = Unrated()
            else:
                raise ValueError(f"티어 배지가 누락되거나 중복됩니다: {link['tiers']!r}")
            text = row['rates'][0]
            if text in _EMPTY or _empty_statistic(row,'rates'):
                rate = Unavailable()
            elif re.fullmatch(r"\d+(?:\.\d+)?%", text):
                rate = Known(Decimal(text[:-1]))
            else:
                raise ValueError(f"알 수 없는 정답률 표현: {text}")
            if len(row['accepted']) != 1:
                raise ValueError(f"정답 제출 수 열 누락/중복: {row['accepted']!r}")
            text = row['accepted'][0]
            if text in _EMPTY or _empty_statistic(row,'accepted'):
                accepted = Unavailable()
            elif re.fullmatch(r'(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)', text):
                accepted = Known(int(text.replace(',', '')))
            else:
                raise ValueError(f"알 수 없는 정답 제출 수: {text!r}")
            return Problem(id=int(match[1]), title=link['titles'][0], url=url,
                           tier=tier, pass_rate=rate, accepted_count=accepted, listed_at=now())
        except (ValueError, InvalidOperation) as error:
            raise SourceSchemaError(f"{identity}: {error}") from error

    def prepare_user(self, criteria: SearchCriteria) -> UserReference | None:
        return self.resolve_user(criteria.user_handle) if criteria.user_handle else None

    def resolve_user(self, handle: str) -> UserReference:
        self._report(f"공개 사용자 @{handle} 확인 중 · Ctrl+C 취소")
        page = self._list_page
        self._goto(page, _ORIGIN + "/problem?type=problem&sort=idAsc&unrated=include")
        self._wait_listing()
        try:
            page.locator('button').filter(has_text=re.compile(r'^\s*필터(?:\s+\d+)?\s*$')).click()
            page.locator('button').filter(has_text=re.compile(r'^\s*사용자 선택\s*$')).click()
            scope = page.locator('main').filter(has=page.locator('.jg-find-search input')).last
            self._pace()
            state = self._update_user_page(
                lambda: scope.get_by_placeholder('검색', exact=True).fill(handle), handle)
            matches: list[int] = []
            seen_pages: set[int] = set()
            target_page = 1
            while True:
                current = state['page']
                if current in seen_pages:
                    raise UserResolutionError("사용자 검색 페이지가 반복됩니다.")
                seen_pages.add(current)
                self._report(f"사용자 검색 · 페이지 {current} · Ctrl+C 취소")
                exact = [i for i, text in enumerate(state['handles']) if text == '@' + handle]
                if exact:
                    matches.extend(exact)
                    target_page = current
                group_next = scope.locator('button').filter(has=page.locator('svg.lucide-chevron-right'))
                numbered_next = scope.locator('button.page-num').filter(has_text=re.compile(rf'^\s*{current+1}\s*$'))
                if not numbered_next.count() and (not group_next.count() or group_next.is_disabled()):
                    break
                self._pace()
                button = numbered_next if numbered_next.count() else group_next
                state = self._update_user_page(button.click, handle, expected=current+1)
            if len(matches) != 1:
                raise UserResolutionError(f"정확한 사용자 @{handle}: {'없음' if not matches else '식별 모호함'}")
            if current != target_page:
                self._pace()
                first = scope.locator('button').filter(has=page.locator('svg.lucide-chevrons-left'))
                state = self._update_user_page(first.click, handle, expected=1)
                current = state['page']
            while current < target_page:
                self._pace()
                numbered_next = scope.locator('button.page-num').filter(has_text=re.compile(rf'^\s*{current+1}\s*$'))
                group_next = scope.locator('button').filter(has=page.locator('svg.lucide-chevron-right'))
                button = numbered_next if numbered_next.count() else group_next
                state = self._update_user_page(button.click, handle, expected=current+1)
                current = state['page']
            self._pace()
            scope.locator('.jg-find-result button').nth(matches[0]).click()
            page.wait_for_url(re.compile(r'[?&]solvedBy=\d+'))
            params = parse_qs(urlsplit(page.url).query)
            if params.get('solvedByMode') != ['include']:
                raise UserResolutionError("사용자 선택 조건이 적용되지 않았습니다.")
            return UserReference(handle, int(params['solvedBy'][0]), now())
        except Error as error:
            raise UserResolutionError(f"공개 사용자 UI 확인 실패: {error}") from error

    def _update_user_page(self, action: Callable[[], None], handle: str,
                          expected: int | None = None) -> dict:
        page = self._list_page
        scope = page.locator('main').filter(has=page.locator('.jg-find-search input')).last
        update = scope.evaluate_handle(_USER_UPDATE)
        failed = False
        try:
            action()
            return self._wait_user_page(handle, update, expected)
        except BaseException:
            failed = True
            raise
        finally:
            try:
                update.evaluate('state => state.observer.disconnect()')
                update.dispose()
            except Error:
                # Preserve the original failure or Ctrl+C if the driver has gone away.
                if not failed:
                    raise

    def _wait_user_page(self, handle: str, update: JSHandle,
                        expected: int | None = None) -> dict:
        deadline = time.monotonic() + self._dom_timeout / 1000
        last_state = None
        while True:
            snapshot = self._list_page.evaluate(_SNAPSHOT)
            self._check_access(snapshot)
            state = self._list_page.evaluate(r"""() => {
                const root = document.querySelector('.jg-find-search')?.parentElement;
                if (!root) return null;
                const note = [...root.querySelectorAll('.jg-find-note')].map(e => e.innerText).join(' ');
                return {query:root.querySelector('.jg-find-search input').value,
                    page:Number(root.querySelector('button.page-num.active')?.innerText || 1),
                    handles:[...root.querySelectorAll('.jg-find-result h3')].map(e=>
                        [...e.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE).map(n=>n.textContent).join('').trim()),
                    targets:[...root.querySelectorAll('.jg-find-result button')].map(e=>
                        [e.getAttribute('href'),e.getAttribute('onclick')]),
                    empty:/검색 결과가 없습니다|사용자를 찾을 수 없습니다/.test(note),
                    busy:root.matches('[aria-busy="true"]') || !!root.querySelector('[aria-busy="true"]') ||
                         /로딩|검색 중|불러오는 중/.test(note)};
            }""")
            changed = update.evaluate('state => state.changed || state.completed')
            ready = not snapshot['busy'] and not self._pending
            if state and changed and ready and state == last_state and not state['busy'] and (
                bool(state['handles']) != state['empty']
            ) and state['query'] == handle and (expected is None or state['page'] == expected):
                return state
            if time.monotonic() >= deadline:
                raise UserResolutionError("사용자 검색 결과를 완전히 확인할 수 없습니다. 공개 검색 화면을 확인하세요.")
            last_state = state if state and changed and ready and not state['busy'] else None
            self._list_page.wait_for_timeout(50)

    def _load_more(self, previous: set[int]) -> dict:
        self._list_page.get_by_role('button', name='더 불러오기', exact=True).click()
        return self._wait_listing(previous)

    def collect(self, criteria: SearchCriteria, user: UserReference | None) -> CompletedListing[Problem]:
        try:
            return self._collect(criteria, user)
        except Error as error:
            raise SourceAccessError(f"목록 브라우저 작업 실패: {error}") from error

    def _collect(self, criteria: SearchCriteria, user: UserReference | None) -> CompletedListing[Problem]:
        params = {'type': 'problem', 'sort': 'idAsc', 'unrated': 'include'}
        if criteria.min_tier is not None or criteria.max_tier is not None:
            params['unrated'] = 'exclude'
        for name, value in [('minTier', criteria.min_tier), ('maxTier', criteria.max_tier)]:
            if value is not None:
                params[name] = str(value)
        if user:
            params.update(solvedBy=str(user.account_id),
                          solvedByMode='include' if criteria.status == Status.SOLVED else 'exclude')
        self._goto(self._list_page, _ORIGIN + '/problem?' + urlencode(params))
        candidates: dict[int, Problem] = {}
        visited: set[str] = set()
        snapshot = self._wait_listing()
        while True:
            location = urlsplit(self._list_page.url)
            if (location.scheme,location.netloc,location.path) != ('https','jungol.co.kr','/problem'):
                raise SourceAccessError("문제 목록이 다른 origin 또는 경로로 이동했습니다.")
            actual = parse_qs(location.query, keep_blank_values=True)
            filter_keys = {'type','sort','unrated','minTier','maxTier','solvedBy','solvedByMode'}
            if (any(actual.get(key) != [value] for key, value in params.items()) or
                    any(key in actual and key not in params for key in filter_keys) or 'status' in actual):
                raise SourceAccessError("요청한 목록 필터가 적용되지 않았습니다.")
            self._verify_filters(criteria, user)
            self._check_access(snapshot)
            if snapshot['tableCount'] != 1 and not snapshot['empty']:
                raise SourceSchemaError("문제/정답률 헤더가 있는 목록 표를 식별할 수 없습니다.")
            for row in snapshot['rows']:
                candidate = self._problem(row)
                candidates.setdefault(candidate.id, candidate)
            self._report(f"Collecting · 수집 {len(candidates)}개 · Ctrl+C 취소")
            if snapshot['next']:
                visited.add(self._list_page.url)
                next_url = urljoin(self._list_page.url, snapshot['next'][0])
                next_location = urlsplit(next_url)
                if (next_location.scheme,next_location.netloc,next_location.path) != ('https','jungol.co.kr','/problem'):
                    raise SourceSchemaError("다음 페이지 URL이 정올 문제 목록이 아닙니다.")
                if next_url in visited:
                    raise SourceCompletenessError("같은 목록 페이지가 반복됩니다.")
                previous = set(candidates)
                self._goto(self._list_page, next_url)
                snapshot = self._wait_listing()
                if not {self._problem(row).id for row in snapshot['rows']} - previous:
                    raise SourceCompletenessError("다음 페이지에 새 문제가 없습니다.")
            elif snapshot['more']:
                previous = set(candidates)
                self._pace()
                try:
                    snapshot = self._load_more(previous)
                except Error as error:
                    raise SourceCompletenessError(f"추가 목록 조회 실패: {error}") from error
            else:
                return CompletedListing(tuple(candidates.values()))

    def _verify_filters(self, criteria: SearchCriteria, user: UserReference | None) -> None:
        page = self._list_page
        button = page.locator('button').filter(has_text=re.compile(r'^\s*필터(?:\s+\d+)?\s*$'))
        try:
            button.click()
            for label in ('일반 문제', '번호 ↑', '제외' if criteria.min_tier is not None or
                          criteria.max_tier is not None else '포함'):
                radio = page.get_by_role('radio', name=label, exact=True)
                radio.wait_for()
                if radio.get_attribute('aria-checked') != 'true':
                    raise SourceAccessError(f"목록 필터 UI 미적용: {label}")
            for label, expected in [('난이도 하한', criteria.min_tier or 1),
                                    ('난이도 상한', criteria.max_tier or 30)]:
                slider = page.get_by_role('slider', name=label, exact=True)
                if slider.get_attribute('aria-valuenow') != str(expected):
                    raise SourceAccessError(f"목록 필터 UI 미적용: {label}")
            if user:
                page.get_by_text('@' + user.handle, exact=True).wait_for()
            button.click()
        except Error as error:
            raise SourceSchemaError(f"목록 필터 UI 확인 실패: {error}") from error
