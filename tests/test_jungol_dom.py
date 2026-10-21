from pathlib import Path
import json
from urllib.parse import urlencode

import pytest
from playwright.sync_api import sync_playwright

from algorithm_problem_picker.jungol import JungolSource
from algorithm_problem_picker.models import Known, SearchCriteria, Unavailable, Unrated, UserReference, now
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


def test_list_distinct_metrics(source):
    serve(source, html('list.html'))
    listing = source.collect(SearchCriteria(), None)
    assert len(listing.candidates) == 3
    assert listing.candidates[0].pass_rate.value.as_tuple().exponent == -2
    assert isinstance(listing.candidates[1].tier, Unrated)
    assert isinstance(listing.candidates[2].pass_rate, Unavailable)
    assert listing.candidates[0].accepted_count == Known(6510)
    assert listing.candidates[1].accepted_count == Known(0)
    assert isinstance(listing.candidates[2].accepted_count, Unavailable)


@pytest.mark.parametrize('text,expected', [('0',Known(0)),(' 3,145 ',Known(3145)),('3145',Known(3145)),
    ('-',Unavailable()),('—',Unavailable()),('미확인',Unavailable()),('미제공',Unavailable())])
def test_accepted_cell_values(source, text, expected):
    serve(source, html('list.html').replace('>6510<','>'+text+'<'))
    assert source.collect(SearchCriteria(),None).candidates[0].accepted_count == expected


@pytest.mark.parametrize('cell', ['', '<td data-col="정답"></td>',
    '<td data-col="정답"><a href="/problem/1000"></a></td>',
    '<td data-col="정답">1</td><td data-col="정답">2</td>',
    *['<td data-col="정답">'+text+'</td>' for text in ['31,45','3 145','-1','1.5','unknown','１２','1,000,00']]])
def test_invalid_accepted_is_schema_failure(source, cell):
    source._dom_timeout = 200
    serve(source, html('list.html').replace('<td data-col="정답">6510</td>',cell))
    with pytest.raises(SourceSchemaError, match='1000.*정답'):
        source.collect(SearchCriteria(),None)


@pytest.mark.parametrize('operation', ['list','recommend'])
@pytest.mark.parametrize('filtered', [False,True])
@pytest.mark.parametrize('status', ['all','solved','unsolved'])
def test_actual_picker_has_no_detail_requests(source, monkeypatch, operation, filtered, status):
    from algorithm_problem_picker.service import Picker
    requests = []
    source._context.on('request', lambda request: requests.append(request.url) if request.resource_type == 'document' else None)
    body = html('tier-pagination.html')
    params = dict(type='problem',sort='idAsc',unrated='include',page=2)
    if status != 'all':
        params.update(solvedBy='42',solvedByMode='include' if status == 'solved' else 'exclude')
        monkeypatch.setattr(source,'resolve_user',lambda handle: UserReference(handle,42,now()))
    first = body.replace('</article>','<a rel="next" href="?'+urlencode(params)+'">다음</a></article>')
    second = body.replace('1000','1003').replace('1001','1004').replace('1002','1005')
    serve(source, lambda url: second if 'page=2' in url else first)
    criteria = SearchCriteria(min_accepted=0 if filtered else None,status=status,user_handle='' if status == 'all' else 'Sample')
    result = getattr(Picker(source),operation)(criteria,**({'limit':1} if operation == 'list' else {'count':1}))
    assert result.fetched_count == 6 and result.returned_count == 1
    assert result.eligible_count == (4 if filtered else 6)
    assert len(requests) == 2 and all('/problem?' in url for url in requests)
    assert len(source._context.pages) == 1


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


def test_accepted_waits_for_nonempty_public_cell(source):
    body = html('list.html').replace('>6510<','><')
    body += '''<script>setTimeout(()=>document.querySelector('td[data-col="정답"]').textContent='6,510',150)</script>'''
    serve(source,body)
    assert source.collect(SearchCriteria(),None).candidates[0].accepted_count == Known(6510)


@pytest.mark.parametrize('replacement', ['<td data-col="other">','<td data-col="問題">'])
def test_missing_problem_cell_fails_instead_of_dropping_row(source, replacement):
    serve(source,html('list.html').replace('<td data-col="문제">',replacement,1))
    source._dom_timeout = 200
    with pytest.raises(SourceSchemaError,match='문제 링크'):
        source.collect(SearchCriteria(),None)


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


@pytest.mark.parametrize('bounds', [dict(min_tier=9, max_tier=14), dict(min_tier=9), dict(max_tier=14)])
@pytest.mark.parametrize('navigation', ['first', 'next', 'more'])
def test_tier_absence_preserved_across_listing(source, bounds, navigation):
    body = html('tier-pagination.html')
    addition = body.split('<tbody>')[1].split('</tbody>')[0].replace('1000', '1003').replace('1001', '1004').replace('1002', '1005')
    if navigation == 'next':
        first = body.replace('</article>', '<a rel="next" href="?'+urlencode(
            dict(type='problem', sort='idAsc', unrated='exclude', **{
                {'min_tier':'minTier','max_tier':'maxTier'}[k]:v for k,v in bounds.items()}, page=2))+'">다음</a></article>')
        second = body.replace(body.split('<tbody>')[1].split('</tbody>')[0], addition)
        serve(source, lambda url: second if 'page=2' in url else first)
    elif navigation == 'more':
        body = body.replace('</article>', '<button id="more">더 불러오기</button></article>')
        body += '<script>document.querySelector("#more").onclick=function(){document.querySelector("tbody").insertAdjacentHTML("beforeend", ROW);this.remove()}</script>'.replace('ROW', json.dumps(addition))
        serve(source, body)
    else:
        serve(source, body)
    listing = source.collect(SearchCriteria(**bounds), None)
    assert len(listing.candidates) == (3 if navigation == 'first' else 6)
    assert isinstance(listing.candidates[1].tier, Unrated)
    assert isinstance(listing.candidates[2].tier, Unavailable)


@pytest.mark.parametrize('bounds', [dict(min_tier=10), dict(max_tier=8), dict(min_tier=10,max_tier=14)])
def test_rated_outside_range_has_diagnostics(source, bounds):
    serve(source, html('tier-pagination.html'))
    with pytest.raises(SourceAccessError, match='1000.*9.*요청') as caught:
        source.collect(SearchCriteria(**bounds), None)
    if len(bounds) == 1:
        assert '제한 없음' in str(caught.value)


@pytest.mark.parametrize('replacement', ['', '<img src="/solved/99.svg">', '<img src="/solved/9.svg"><img src="/solved/10.svg">'])
def test_tier_schema_diagnostics(source, replacement):
    serve(source, html('tier-pagination.html').replace('<img src="/solved/9.svg">', replacement))
    with pytest.raises(SourceSchemaError, match='1000.*티어'):
        source.collect(SearchCriteria(min_tier=9), None)


@pytest.mark.parametrize('change', ['url', 'duplicate', 'ui'])
def test_filters_reverified_after_more(source, change):
    body = html('tier-pagination.html').replace('</article>', '<button id="more">더 불러오기</button></article>')
    update = {'url': "history.replaceState(null,'',location.href.replace('minTier=9','minTier=8'))",
              'duplicate': "history.replaceState(null,'',location.href+'&minTier=9')",
              'ui': "document.querySelector('[aria-label=\"난이도 하한\"]').setAttribute('aria-valuenow','8')"}[change]
    addition = body.split('<tbody>')[1].split('</tbody>')[0].replace('1000','1003')
    body += '<script>document.querySelector("#more").onclick=function(){UPDATE;document.querySelector("tbody").insertAdjacentHTML("beforeend", ROW);this.remove()}</script>'.replace('UPDATE',update).replace('ROW',json.dumps(addition))
    serve(source, body)
    with pytest.raises(SourceAccessError):
        source.collect(SearchCriteria(min_tier=9), None)


@pytest.mark.parametrize('status', ['solved', 'unsolved'])
def test_public_user_filters_preserved(source, status):
    serve(source, html('tier-pagination.html'))
    listing = source.collect(SearchCriteria(min_tier=9,status=status,user_handle='Sample'), UserReference('Sample',42,now()))
    assert len(listing.candidates) == 3
    assert 'solvedBy=42' in source._list_page.url
    assert 'solvedByMode='+('include' if status == 'solved' else 'exclude') in source._list_page.url


@pytest.mark.parametrize('navigation',['first','next'])
@pytest.mark.parametrize('key',['type','sort','unrated','minTier','maxTier','solvedBy','solvedByMode'])
def test_required_filters_cannot_be_lost_on_any_page(source, navigation, key):
    params = dict(type='problem',sort='idAsc',unrated='exclude',minTier=9,maxTier=14,
                  solvedBy=42,solvedByMode='include',page=2)
    params.pop(key)
    body = html('tier-pagination.html')
    if navigation == 'first':
        body += '<script>const lost=new URL(location.href);lost.searchParams.delete(KEY);history.replaceState(null,"",lost)</script>'.replace('KEY',json.dumps(key))
        serve(source,body)
    else:
        first = body.replace('</article>','<a rel="next" href="?'+urlencode(params)+'">다음</a></article>')
        second = body.replace('1000','1003').replace('1001','1004').replace('1002','1005')
        serve(source,lambda url:second if 'page=2' in url else first)
    with pytest.raises(SourceAccessError):
        source.collect(SearchCriteria(min_tier=9,max_tier=14,status='solved',user_handle='Sample'),UserReference('Sample',42,now()))


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
        Progress(stage=Stage.COLLECTING).advance(Stage.COMPLETE)


@pytest.mark.xfail(strict=True, raises=AssertionError, reason='001/T041: request completion precedes public result DOM')
@pytest.mark.parametrize('operation', ['list','recommend'])
def test_known_t041_delayed_rows_after_completed_request(source, operation):
    from algorithm_problem_picker.service import Picker
    addition = html('pagination.html').split('<tbody>')[1].split('</tbody>')[0]
    body = html('list.html').replace('</article>','<button id="more">더 불러오기</button></article>')
    body += '''<script>document.querySelector('#more').onclick=async function(){
        this.disabled=true; await fetch('/fixture-more');this.remove();
        setTimeout(()=>document.querySelector('tbody').insertAdjacentHTML('beforeend',ROW),400)
        }</script>'''.replace('ROW',json.dumps(addition))
    serve(source,body)
    source._context.route('**/fixture-more',lambda route:route.fulfill(status=204))
    try:
        result = getattr(Picker(source),operation)(SearchCriteria())
    except SourceCompletenessError:
        return  # A proven failure also prevents an incomplete success result.
    assert result.fetched_count == result.eligible_count == 4


@pytest.mark.xfail(strict=True, raises=AssertionError, reason='001/T041: empty load requires public completion evidence')
def test_known_t041_empty_request_alone_is_not_completion(source):
    body = html('list.html').replace('</article>','<button id="more">더 불러오기</button></article>')
    body += '''<script>document.querySelector('#more').onclick=async function(){
        this.disabled=true;await fetch('/fixture-more');this.remove()};</script>'''
    serve(source,body)
    source._context.route('**/fixture-more',lambda route:route.fulfill(status=204))
    source._dom_timeout = 250
    try:
        source.collect(SearchCriteria(),None)
    except SourceCompletenessError:
        return
    assert False, 'transport completion alone returned CompletedListing'


@pytest.mark.xfail(strict=True, raises=UserResolutionError, reason='001/T042: completed search request precedes result DOM')
@pytest.mark.parametrize('page_change', [False,True])
def test_known_t042_delayed_user_results_after_completed_request(source, page_change):
    body = user_listing().replace('@Sample ', '@Other ')
    if page_change:
        body = body.replace('</main>','''<nav><button class="page-num active">1</button>
            <button class="page-num" id="next-user">2</button></nav></main>''')
        body += '''<script>document.querySelector('#next-user').onclick=async function(){
            document.querySelector('button.active').classList.remove('active');this.classList.add('active');
            await fetch('/fixture-search');setTimeout(()=>document.querySelector('.jg-find-result h3').textContent='@Sample',400)};</script>'''
    else:
        body += '''<script>document.querySelector('.jg-find-search input').oninput=async()=>{
            await fetch('/fixture-search');setTimeout(()=>document.querySelector('.jg-find-result h3').textContent='@Sample',400)};</script>'''
    serve(source,body)
    source._context.route('**/fixture-search',lambda route:route.fulfill(status=204))
    assert source.resolve_user('Sample').account_id == 42


@pytest.mark.xfail(strict=True, raises=AssertionError, reason='001/T042: same handle needs its current result completion')
def test_known_t042_same_handle_refresh_after_completed_request(source):
    body = user_listing()+'''<script>document.querySelector('.jg-find-search input').oninput=async()=>{
        await fetch('/fixture-search');setTimeout(()=>{
        document.querySelector('.jg-find-result button').setAttribute('onclick',"location.href='/problem?solvedBy=84&solvedByMode=include'")},400)};</script>'''
    serve(source,body)
    source._context.route('**/fixture-search',lambda route:route.fulfill(status=204))
    assert source.resolve_user('Sample').account_id == 84


@pytest.mark.xfail(strict=True, raises=AssertionError, reason='001/T042: delayed empty search must replace previous match')
def test_known_t042_empty_result_after_completed_request(source):
    body = user_listing()+'''<script>document.querySelector('.jg-find-search input').oninput=async()=>{
        await fetch('/fixture-search');setTimeout(()=>{
        document.querySelector('.jg-find-result').remove();
        document.querySelector('#users').insertAdjacentHTML('beforeend','<p class="jg-find-note">검색 결과가 없습니다</p>')},400)};</script>'''
    serve(source,body)
    source._context.route('**/fixture-search',lambda route:route.fulfill(status=204))
    try:
        source.resolve_user('Sample')
    except UserResolutionError:
        assert source._list_page.locator('.jg-find-result').count() == 0
        return
    assert False, 'stale previous match resolved before empty current results'
