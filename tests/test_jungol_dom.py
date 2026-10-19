from pathlib import Path
import json

import pytest
from playwright.sync_api import sync_playwright

from algorithm_problem_picker.jungol import JungolSource
from algorithm_problem_picker.models import Known, SearchCriteria, Unavailable, Unrated
from algorithm_problem_picker.ports import SourceAccessError, SourceCompletenessError, SourceSchemaError, UserResolutionError

FIXTURES = Path(__file__).parent / 'fixtures' / 'jungol'


@pytest.fixture
def source(monkeypatch):
    # Throttling is tested separately; fixture browsing does not contact the site.
    monkeypatch.setattr('algorithm_problem_picker.jungol.time.sleep', lambda _: None)
    with JungolSource() as source:
        source._context.route('**/*', lambda route: route.abort())
        yield source
    assert not source._browser.is_connected()


def serve(source, pages, status=200):
    def route(request):
        url = request.request.url
        html = pages(url) if callable(pages) else pages
        request.fulfill(status=status, content_type='text/html; charset=utf-8', body=html)
    source._context.route('https://jungol.co.kr/**', route)


def html(name):
    return (FIXTURES / name).read_text(encoding='utf-8')


def test_list_and_detail_distinct_metrics(source):
    serve(source, lambda url: html('detail.html' if url.endswith('/1000') else 'list.html'))
    listing = source.collect(SearchCriteria(), None)
    assert len(listing.candidates) == 3
    assert listing.candidates[0].pass_rate.value.as_tuple().exponent == -2
    assert isinstance(listing.candidates[1].tier, Unrated)
    assert isinstance(listing.candidates[2].pass_rate, Unavailable)
    result = source.read_details(listing.candidates[0])
    assert result.solver_count == Known(5171)
    assert result.pass_rate == listing.candidates[0].pass_rate
    assert result.listed_at == listing.candidates[0].listed_at


def test_next_page_and_duplicate_first_record(source):
    first = html('list.html').replace('</article>', '<a rel="next" href="/problem?page=2&type=problem&sort=idAsc&unrated=include">다음</a></article>')
    second = html('pagination.html').replace('</tbody>', html('list.html').split('<tbody>')[1].split('</tbody>')[0] + '</tbody>')
    serve(source, lambda url: second if 'page=2' in url else first)
    assert [p.id for p in source.collect(SearchCriteria(), None).candidates] == [1000,1001,1002,1003]


def test_cursor_loading_and_end(source):
    addition = html('pagination.html').split('<tbody>')[1].split('</tbody>')[0]
    first = html('list.html').replace('</article>', '<button id="more">더 불러오기</button></article>')
    first += '''<script>document.querySelector('#more').onclick=function(){
        this.textContent='로딩 중...'; setTimeout(()=>{
        document.querySelector('tbody').insertAdjacentHTML('beforeend', ROW);this.remove()},80)
        }</script>'''.replace('ROW', json.dumps(addition))
    serve(source, first)
    assert len(source.collect(SearchCriteria(), None).candidates) == 4


def test_cursor_disappears_before_delayed_rows(source):
    addition = html('pagination.html').split('<tbody>')[1].split('</tbody>')[0]
    body = html('list.html').replace('</article>', '<button id="more">더 불러오기</button></article>')
    body += '''<script>document.querySelector('#more').onclick=function(){
        this.remove(); setTimeout(()=>{
        document.querySelector('tbody').insertAdjacentHTML('beforeend', ROW)},400)
        }</script>'''.replace('ROW', json.dumps(addition))
    serve(source, body)
    assert [p.id for p in source.collect(SearchCriteria(), None).candidates] == [1000,1001,1002,1003]


def test_cursor_disappears_without_completion_evidence(source):
    serve(source, html('list.html').replace('</article>',
        '<button onclick="this.remove()">더 불러오기</button></article>'))
    source._dom_timeout = 200
    with pytest.raises(SourceCompletenessError):
        source.collect(SearchCriteria(), None)


def test_cursor_waits_for_loading_and_delayed_next_button(source):
    addition = html('pagination.html').split('<tbody>')[1].split('</tbody>')[0]
    body = html('list.html').replace('</article>', '<button id="more">더 불러오기</button></article>')
    body += '''<script>document.querySelector('#more').onclick=function(){
        this.remove(); const article=document.querySelector('article');
        article.setAttribute('aria-busy','true');
        setTimeout(()=>document.querySelector('tbody').insertAdjacentHTML('beforeend', ROW),80);
        setTimeout(()=>{article.removeAttribute('aria-busy');
        article.insertAdjacentHTML('beforeend','<button>더 불러오기</button>')},400)
        }</script>'''.replace('ROW', json.dumps(addition))
    serve(source, body)
    source._dom_timeout = 650
    with pytest.raises(SourceCompletenessError):
        source.collect(SearchCriteria(), None)
    assert source._list_page.get_by_role('button', name='더 불러오기', exact=True).count() == 1


def test_cursor_completed_empty_request_is_terminal(source):
    body = html('list.html').replace('</article>', '<button id="more">더 불러오기</button></article>')
    body += '''<script>document.querySelector('#more').onclick=async function(){
        this.disabled=true; await fetch('/fixture-more'); this.remove();
        }</script>'''
    serve(source, body)
    source._context.route('**/fixture-more', lambda route: route.fulfill(status=204))
    assert len(source.collect(SearchCriteria(), None).candidates) == 3


def test_repeating_page_fails(source):
    serve(source, html('list.html').replace('</article>', '<a rel="next" href="?type=problem&sort=idAsc&unrated=include">다음</a></article>'))
    with pytest.raises(SourceCompletenessError):
        source.collect(SearchCriteria(), None)


def test_no_progress_cursor_fails(source):
    serve(source, html('list.html').replace('</article>', '<button>더 불러오기</button></article>'))
    source._dom_timeout = 150
    with pytest.raises(SourceCompletenessError):
        source.collect(SearchCriteria(), None)


def test_empty_vs_temporarily_empty(source):
    serve(source, html('empty.html'))
    assert not source.collect(SearchCriteria(), None).candidates
    body = repr(html('list.html').split('<article>')[1].split('</article>')[0])
    serve(source, '<article>로딩 중...</article><script>setTimeout(()=>document.querySelector("article").innerHTML=' + body + ',80)</script>')
    assert len(source.collect(SearchCriteria(), None).candidates) == 3


def test_partial_hydration_and_empty_alert(source):
    initial = html('list.html').replace('data-col="정답률"', 'data-pending="정답률"')
    initial += '''<div role="alert"></div><script>setTimeout(()=>{
        document.querySelectorAll('[data-pending]').forEach(e=>e.setAttribute('data-col','정답률'))
        },80)</script>'''
    serve(source, initial)
    assert len(source.collect(SearchCriteria(), None).candidates) == 3


def test_explicit_empty_rate_anchor_is_unavailable(source):
    serve(source, html('list.html').replace('47.45%', '<a href="/problem/1000"></a>'))
    assert isinstance(source.collect(SearchCriteria(), None).candidates[0].pass_rate, Unavailable)


@pytest.mark.parametrize('status,body', [(403,'denied'),(429,'limited'),(200,html('error.html')),
    (200,'<h1>로그인이 필요합니다</h1>'), (200,'<h1>Verify you are human</h1>')])
def test_access_failure(source, status, body):
    serve(source, body, status)
    with pytest.raises(SourceAccessError):
        source.collect(SearchCriteria(), None)


@pytest.mark.parametrize('body', [html('list.html').replace('/solved/1.svg','/solved/99.svg'),
    html('list.html').replace('47.45%', 'bad metric'), '<article><h1>전체 문제</h1><p>new layout</p></article>'])
def test_schema_change_not_unknown(source, body):
    serve(source, body)
    source._dom_timeout = 150
    with pytest.raises(SourceSchemaError):
        source.collect(SearchCriteria(), None)


def test_detail_identity_mismatch(source):
    serve(source, html('list.html'))
    candidate = source.collect(SearchCriteria(), None).candidates[0]
    serve(source, html('detail.html').replace('/problem/1000','/problem/1001'))
    with pytest.raises(SourceSchemaError):
        source.read_details(candidate)


def test_explicit_empty_solver_stat(source):
    serve(source, html('list.html'))
    candidate = source.collect(SearchCriteria(), None).candidates[0]
    serve(source, html('detail.html').replace('5,171',''))
    assert isinstance(source.read_details(candidate).solver_count, Unavailable)


@pytest.mark.parametrize('placeholder', ['0', ''])
def test_detail_waits_for_loaded_solver_stat(source, placeholder):
    serve(source, html('list.html'))
    candidate = source.collect(SearchCriteria(), None).candidates[0]
    body = html('detail.html').replace('5,171', placeholder).replace('<article>', '<article aria-busy="true">')
    body += '''<script>setTimeout(()=>{
        document.querySelector('[title="맞힌 사람"] .num').textContent='5,171';
        document.querySelector('article').removeAttribute('aria-busy')},400)</script>'''
    serve(source, body)
    result = source.read_details(candidate)
    assert result.solver_count == Known(5171)
    assert result.tier == candidate.tier and result.pass_rate == candidate.pass_rate
    assert source._detail_page.locator('article').get_attribute('aria-busy') is None


def test_loaded_zero_solver_stat_is_known(source):
    serve(source, html('list.html'))
    candidate = source.collect(SearchCriteria(), None).candidates[0]
    serve(source, html('detail.html').replace('5,171', '0'))
    assert source.read_details(candidate).solver_count == Known(0)


@pytest.mark.parametrize('failure', ['loading', 'schema', 'access'])
def test_detail_never_returns_placeholder_on_loading_failure(source, failure):
    serve(source, html('list.html'))
    candidate = source.collect(SearchCriteria(), None).candidates[0]
    body = html('detail.html').replace('<article>', '<article aria-busy="true">')
    if failure != 'loading':
        replacement = '<h1>로그인이 필요합니다</h1>' if failure == 'access' else '<h1>new layout</h1>'
        body += '<script>setTimeout(()=>{document.querySelector("article").outerHTML=BODY},100)</script>'.replace(
            'BODY', json.dumps('<article>' + replacement + '</article>'))
    serve(source, body)
    source._dom_timeout = 250
    with pytest.raises(SourceAccessError if failure == 'access' else SourceSchemaError):
        source.read_details(candidate)


@pytest.mark.parametrize('matches', [0, 1, 2])
def test_exact_user_resolution(source, matches):
    users = html('user.html')
    listing = html('list.html').split('<table>')[1].split('</table>')[0]
    users = users.replace('</article>', '<table>' + listing + '</table></article>')
    if matches == 0:
        users = users.replace('@Sample ', '@SampleExtra ')
    if matches == 2:
        users = users.replace('</main>', '<div class="jg-find-result"><button><h3>@Sample</h3></button></div></main>')
    serve(source, users)
    if matches == 1:
        user = source.resolve_user('Sample')
        assert user.handle == 'Sample' and user.account_id == 42
    else:
        with pytest.raises(UserResolutionError):
            source.resolve_user('Sample')


def test_user_pagination_waits_for_new_results_and_scans_last_group(source):
    users = html('user.html').replace('@Sample ', '@Other1 ')
    table = html('list.html').split('<table>')[1].split('</table>')[0]
    users = users.replace('</article>', '<table>' + table + '</table></article>')
    users = users.replace('</main>', '''<nav class="paginator">
      <button onclick="selectPage(1)"><svg class="lucide-chevrons-left"></svg></button>
      <button class="page-num active" onclick="selectPage(1)">1</button>
      <button class="page-num" onclick="selectPage(2)">2</button>
      <button class="page-num" onclick="selectPage(3)">3</button>
      <button disabled><svg class="lucide-chevron-right"></svg></button>
      </nav></main><script>function selectPage(n){
      document.querySelectorAll('.page-num').forEach(e=>e.classList.toggle('active',Number(e.textContent)===n));
      setTimeout(()=>{document.querySelector('.jg-find-result h3').textContent=n===2?'@Sample':'@Other'+n},150)
      }</script>''')
    serve(source, users)
    assert source.resolve_user('Sample').account_id == 42


def user_listing():
    table = html('list.html').split('<table>')[1].split('</table>')[0]
    return html('user.html').replace('</article>', '<table>' + table + '</table></article>')


@pytest.mark.parametrize('empty', [False, True])
def test_user_search_waits_for_current_query_results(source, empty):
    body = user_listing()
    if not empty:
        body = body.replace('@Sample ', '@Other ')
    update = ("document.querySelector('.jg-find-result').remove();"
              "document.querySelector('#users').insertAdjacentHTML('beforeend',"
              "'<p class=\"jg-find-note\">검색 결과가 없습니다</p>')") if empty else (
                  "document.querySelector('.jg-find-result h3').textContent='@Sample'")
    body += '''<script>document.querySelector('.jg-find-search input').oninput=()=>{
        setTimeout(()=>{UPDATE},400)}</script>'''.replace('UPDATE', update)
    serve(source, body)
    if empty:
        with pytest.raises(UserResolutionError, match='없음'):
            source.resolve_user('Sample')
        assert source._list_page.locator('.jg-find-note').inner_text() == '검색 결과가 없습니다'
    else:
        assert source.resolve_user('Sample').account_id == 42


def test_user_search_same_handles_waits_for_own_request(source):
    requests = []
    body = user_listing() + '''<script>
        document.querySelector('.jg-find-search input').oninput=()=>{
        setTimeout(()=>fetch('/fixture-search'),400)};
        </script>'''
    serve(source, body)
    def search(route):
        requests.append(route.request.url)
        route.fulfill(status=204)
    source._context.route('**/fixture-search', search)
    assert source.resolve_user('Sample').account_id == 42
    assert len(requests) == 1


def test_user_search_without_update_evidence_fails(source):
    serve(source, user_listing() + '''<script>
        document.querySelector('.jg-find-search input').oninput=()=>{};
        </script>''')
    source._dom_timeout = 200
    with pytest.raises(UserResolutionError, match='완전히'):
        source.resolve_user('Sample')


def test_user_cancel_preserves_interrupt_when_observer_cleanup_fails(source, monkeypatch):
    from playwright.sync_api import Error, Locator
    serve(source, user_listing())
    def cancel(*args):
        raise KeyboardInterrupt()
    class DisconnectedObserver:
        def evaluate(self, *args):
            raise Error('driver disconnected during cleanup')
        def dispose(self):
            pass
    monkeypatch.setattr(source, '_wait_user_page', cancel)
    monkeypatch.setattr(Locator, 'evaluate_handle', lambda *args: DisconnectedObserver())
    with pytest.raises(KeyboardInterrupt):
        source.resolve_user('Sample')


def test_user_pages_with_same_handles_still_detect_ambiguity(source):
    body = user_listing().replace('</main>', '''<nav>
        <button class="page-num active" onclick="selectPage(1)">1</button>
        <button class="page-num" onclick="selectPage(2)">2</button></nav></main>''')
    body += '''<script>
        document.querySelector('.jg-find-search input').oninput=()=>{
            document.querySelector('.jg-find-result h3').textContent='@Sample'};
        function selectPage(n){
            document.querySelectorAll('.page-num').forEach(e=>
                e.classList.toggle('active',Number(e.textContent)===n));
            setTimeout(()=>{document.querySelector('.jg-find-result h3').textContent='@Sample'},150)
        }</script>'''
    serve(source, body)
    source._dom_timeout = 600
    with pytest.raises(UserResolutionError, match='모호'):
        source.resolve_user('Sample')


def test_filter_not_applied(source):
    serve(source, html('list.html'))
    with pytest.raises(SourceAccessError):
        source.collect(SearchCriteria(min_tier=2), None)


@pytest.mark.parametrize('error', [RuntimeError('failure'), KeyboardInterrupt()])
def test_cleanup_on_failure_and_cancel(monkeypatch, error):
    browser = context = None
    with pytest.raises(type(error)):
        with JungolSource() as source:
            browser, context = source._browser, source._context
            raise error
    assert not browser.is_connected()
    assert not context.pages


def test_navigation_timeout_is_failure(source):
    from playwright.sync_api import TimeoutError
    def fail(*args, **kwargs):
        raise TimeoutError('navigation timeout')
    source._list_page.goto = fail
    with pytest.raises(SourceAccessError):
        source.collect(SearchCriteria(), None)


def test_progress_cannot_present_incomplete_collection():
    from algorithm_problem_picker.models import Progress, Stage
    with pytest.raises(AssertionError):
        Progress(stage=Stage.COLLECTING).advance(Stage.PRESENTED)
