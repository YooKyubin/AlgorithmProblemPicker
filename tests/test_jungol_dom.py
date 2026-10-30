from pathlib import Path
from decimal import Decimal
import json
from urllib.parse import urlencode

import pytest
from playwright.sync_api import sync_playwright

from algorithm_problem_picker.jungol import JungolSource
from algorithm_problem_picker.models import Known, Unavailable, now
from algorithm_problem_picker.jungol_models import Rated, SearchCriteria, Unrated, UserReference
from algorithm_problem_picker.jungol_policy import JungolPolicy
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


def serve_statistics(source, body, navigation):
    if navigation == 'first':
        serve(source,body)
        return 1000
    rows = body.split('<tbody>')[1].split('</tbody>')[0]
    addition = rows.replace('1000','1003').replace('1001','1004').replace('1002','1005')
    first = html('site-listing.html').replace('</article>','<button id="more">더 불러오기</button></article>')
    first += '''<script>document.querySelector('#more').onclick=function(){
        const article=document.querySelector('article');article.setAttribute('aria-busy','true');
        document.querySelector('tbody').insertAdjacentHTML('beforeend',ROW);this.remove();
        article.removeAttribute('aria-busy');
    };</script>'''.replace('ROW',json.dumps(addition))
    serve(source,first)
    return 1003


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


@pytest.mark.parametrize('navigation', ['first','more'])
@pytest.mark.parametrize('missing', ['accepted','rate','both'])
@pytest.mark.parametrize('marker', ['data-col-empty','data-col-empty="false"'])
def test_explicit_empty_statistics_are_unavailable(source, navigation, missing, marker):
    source._dom_timeout = 500
    body = html('site-listing.html')
    if missing in {'accepted','both'}:
        body = body.replace('<td data-col="정답">6510</td>','<td data-col="정답" '+marker+'> </td>',1)
    if missing in {'rate','both'}:
        body = body.replace('<td data-col="정답률">47.45%</td>','<td data-col="정답률" '+marker+'> </td>',1)
    number = serve_statistics(source,body,navigation)
    listing = source.collect(SearchCriteria(min_tier=9,max_tier=13),None)
    target = next(problem for problem in listing.candidates if problem.id == number)
    assert target.tier == Rated(8)
    assert target.accepted_count == (Unavailable() if missing in {'accepted','both'} else Known(6510))
    assert target.pass_rate == (Unavailable() if missing in {'rate','both'} else Known(Decimal('47.45')))
    assert len(listing.candidates) == (3 if navigation == 'first' else 6)
    zero = next(problem for problem in listing.candidates if problem.id == number+1)
    assert zero.accepted_count == Known(0) and zero.pass_rate == Known(Decimal('0.00'))
    assert zero.pass_rate.value.as_tuple().exponent == -2


@pytest.mark.parametrize('operation', ['list','recommend'])
def test_empty_statistics_listing_reaches_numeric_filters(source, operation):
    from algorithm_problem_picker.service import Picker
    source._dom_timeout = 500
    body = html('site-listing.html').replace('<td data-col="정답">6510</td>',
        '<td data-col="정답" data-col-empty></td>',1).replace('<td data-col="정답률">47.45%</td>',
        '<td data-col="정답률" data-col-empty></td>',1)
    serve_statistics(source,body,'more')
    options = dict(limit=1) if operation == 'list' else dict(count=1)
    result = getattr(Picker(JungolPolicy(), source),operation)(SearchCriteria(min_tier=9,max_tier=13,
        min_rate=Decimal('0'),max_accepted=0),**options)
    assert result.fetched_count == 6 and result.eligible_count == 2 and result.returned_count == 1
    assert result.omitted_unknown_count == 1 and result.problems[0].id in {1001,1004}
    assert result.problems[0].accepted_count == Known(0)


@pytest.mark.parametrize('column,original,text,expected', [
    ('정답','6510','0',Known(0)),('정답','6510','3145',Known(3145)),
    ('정답','6510','3,145',Known(3145)),('정답률','47.45%','0.00%',Known(Decimal('0.00'))),
    ('정답률','47.45%','47.45%',Known(Decimal('47.45')))])
def test_empty_marker_keeps_numeric_statistics(source, column, original, text, expected):
    body = html('site-listing.html').replace('<td data-col="'+column+'">'+original+'</td>',
        '<td data-col="'+column+'" data-col-empty>'+text+'</td>',1)
    serve(source,body)
    problem = source.collect(SearchCriteria(),None).candidates[0]
    assert (problem.accepted_count if column == '정답' else problem.pass_rate) == expected
    if column == '정답률':
        assert problem.pass_rate.value.as_tuple().exponent == -2


@pytest.mark.parametrize('text', ['-','—','미확인','미제공'])
def test_rate_unavailable_tokens_remain_supported(source, text):
    serve(source,html('site-listing.html').replace('47.45%',text,1))
    assert source.collect(SearchCriteria(),None).candidates[0].pass_rate == Unavailable()


@pytest.mark.parametrize('column,original,value', [('정답','6510','6,510'),('정답률','47.45%','47.45%')])
def test_unmarked_empty_statistic_waits_for_value(source, monkeypatch, column, original, value):
    source._dom_timeout = 750
    serve(source,html('site-listing.html').replace('>'+original+'<','><',1))
    wait = source._list_page.wait_for_timeout
    polls = []
    def hydrate(delay):
        polls.append(delay)
        if len(polls) == 3:
            source._list_page.locator('td[data-col="'+column+'"]').first.evaluate('(cell,value)=>cell.textContent=value',value)
        wait(delay)
    monkeypatch.setattr(source._list_page,'wait_for_timeout',hydrate)
    problem = source.collect(SearchCriteria(),None).candidates[0]
    assert len(polls) >= 3
    assert (problem.accepted_count if column == '정답' else problem.pass_rate) == (
        Known(6510) if column == '정답' else Known(Decimal('47.45')))


@pytest.mark.parametrize('navigation', ['first','more'])
@pytest.mark.parametrize('column,original', [('정답','6510'),('정답률','47.45%')])
@pytest.mark.parametrize('content', ['', '<a href="/problem/1001"></a>'])
def test_unmarked_empty_statistic_never_becomes_unavailable(source, navigation, column, original, content):
    source._dom_timeout = 200
    body = html('site-listing.html').replace('>'+original+'<','>'+content+'<',1)
    number = serve_statistics(source,body,navigation)
    if navigation == 'first':
        with pytest.raises(SourceSchemaError,match=str(number)+'.*'+column):
            source.collect(SearchCriteria(),None)
    else:
        with pytest.raises(SourceCompletenessError):
            source.collect(SearchCriteria(),None)


@pytest.mark.parametrize('navigation', ['first','more'])
@pytest.mark.parametrize('column,original,bad', [('정답','6510','31,45'),('정답률','47.45%','bad metric')])
@pytest.mark.parametrize('structure', ['missing','duplicate','malformed'])
def test_invalid_marked_statistic_has_diagnostics(source, navigation, column, original, bad, structure):
    source._dom_timeout = 200
    cell = '<td data-col="'+column+'">'+original+'</td>'
    empty = '<td data-col="'+column+'" data-col-empty></td>'
    replacement = {'missing':'','duplicate':empty+empty,
                   'malformed':'<td data-col="'+column+'" data-col-empty>'+bad+'</td>'}[structure]
    number = serve_statistics(source,html('site-listing.html').replace(cell,replacement,1),navigation)
    with pytest.raises(SourceSchemaError,match=str(number)+'.*'+column):
        source.collect(SearchCriteria(),None)


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
    result = getattr(Picker(JungolPolicy(), source),operation)(criteria,**({'limit':1} if operation == 'list' else {'count':1}))
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
        document.querySelector('article').setAttribute('aria-busy','true');
        this.disabled=true;this.textContent='로딩 중...'; setTimeout(()=>{
        document.querySelector('tbody').insertAdjacentHTML('beforeend', ROW);this.remove();
        document.querySelector('article').removeAttribute('aria-busy')},80)
        }</script>'''.replace('ROW', json.dumps(addition))
    serve(source, first)
    assert len(source.collect(SearchCriteria(), None).candidates) == 4


def test_cursor_absence_finishes_before_future_rows(source):
    addition = html('pagination.html').split('<tbody>')[1].split('</tbody>')[0]
    body = html('list.html').replace('</article>','<button id="more">더 불러오기</button></article>')
    body += '''<script>document.querySelector('#more').onclick=function(){
        document.querySelector('article').setAttribute('aria-busy','true');this.remove();
        document.addEventListener('fixture-finish',()=>{
            document.querySelector('tbody').insertAdjacentHTML('beforeend',ROW);
            document.querySelector('article').removeAttribute('aria-busy');
        },{once:true});
    };</script>'''.replace('ROW',json.dumps(addition))
    serve(source,body)
    source._dom_timeout = 250
    assert [p.id for p in source.collect(SearchCriteria(),None).candidates] == [1000,1001,1002]
    source._list_page.evaluate("document.dispatchEvent(new Event('fixture-finish'))")
    assert source._list_page.locator('tbody tr').count() == 4


def test_cursor_absence_needs_no_completion_notice(source):
    serve(source,html('list.html').replace('</article>',
        '<button onclick="this.remove()">더 불러오기</button></article>'))
    source._dom_timeout = 200
    assert len(source.collect(SearchCriteria(),None).candidates) == 3


def test_cursor_absence_does_not_wait_for_future_button(source):
    addition = html('pagination.html').split('<tbody>')[1].split('</tbody>')[0]
    body = html('list.html').replace('</article>','<button id="more">더 불러오기</button></article>')
    body += '''<script>document.querySelector('#more').onclick=async function(){
        const article=document.querySelector('article');article.setAttribute('aria-busy','true');
        await fetch('/fixture-more');this.remove();
        document.addEventListener('fixture-finish',()=>{
            document.querySelector('tbody').insertAdjacentHTML('beforeend',ROW);
            article.insertAdjacentHTML('beforeend','<button>더 불러오기</button>');
            article.removeAttribute('aria-busy');
        },{once:true});
    };</script>'''.replace('ROW',json.dumps(addition))
    serve(source,body)
    source._context.route('**/fixture-more',lambda route:route.fulfill(status=204))
    source._dom_timeout = 250
    assert len(source.collect(SearchCriteria(),None).candidates) == 3
    source._list_page.evaluate("document.dispatchEvent(new Event('fixture-finish'))")
    assert source._list_page.locator('tbody tr').count() == 4
    assert source._list_page.get_by_role('button',name='더 불러오기',exact=True).count() == 1


@pytest.mark.parametrize('public_completion', [False,True])
def test_cursor_empty_request_finishes_with_or_without_notice(source, public_completion):
    body = html('list.html').replace('</article>','<button id="more">더 불러오기</button></article>')
    body += '''<script>document.querySelector('#more').onclick=async function(){
        const article=document.querySelector('article');
        START;this.disabled=true;await fetch('/fixture-more');this.remove();END;
    };</script>'''.replace('START',"article.setAttribute('aria-busy','true')" if public_completion else '').replace(
        'END',"article.removeAttribute('aria-busy')" if public_completion else '')
    serve(source,body)
    source._context.route('**/fixture-more',lambda route:route.fulfill(status=204))
    source._dom_timeout = 250
    assert len(source.collect(SearchCriteria(),None).candidates) == 3


def test_repeating_page_fails(source):
    serve(source, html('list.html').replace('</article>', '<a rel="next" href="?type=problem&sort=idAsc&unrated=include">다음</a></article>'))
    with pytest.raises(SourceCompletenessError):
        source.collect(SearchCriteria(), None)


def test_no_progress_cursor_fails(source):
    serve(source, html('list.html').replace('</article>', '<button>더 불러오기</button></article>'))
    source._dom_timeout = 150
    with pytest.raises(SourceCompletenessError):
        source.collect(SearchCriteria(), None)


def test_absent_cursor_uses_one_current_snapshot_despite_busy_pending(source, monkeypatch):
    from algorithm_problem_picker.jungol import _SNAPSHOT
    body = html('list.html').replace('</article>','<button id="more">더 불러오기</button></article>')
    body += '''<script>document.querySelector('#more').onclick=function(){
        document.querySelector('article').setAttribute('aria-busy','true');
        fetch('/fixture-held');this.remove();
    };</script>'''
    serve(source,body)
    held = []
    source._context.route('**/fixture-held',lambda route:held.append(route))
    snapshots = []
    evaluate = source._list_page.evaluate
    def observe(expression, *args):
        snapshot = evaluate(expression,*args)
        if expression == _SNAPSHOT and snapshot['busy']:
            snapshots.append(snapshot)
        return snapshot
    monkeypatch.setattr(source._list_page,'evaluate',observe)
    source._dom_timeout = 250
    assert len(source.collect(SearchCriteria(),None).candidates) == 3
    assert held and source._pending and len(snapshots) == 1
    held[0].fulfill(status=204)


@pytest.mark.parametrize('initial_empty', [False,True])
def test_final_empty_current_listing_keeps_accumulated_candidates(source, initial_empty):
    body = html('site-listing.html')
    if initial_empty:
        rows = body.split('<tbody>')[1].split('</tbody>')[0]
        body = body.replace(rows,'').replace('</article>','<p>검색 결과가 없습니다.</p></article>')
    body = body.replace('</article>','<button id="more">더 불러오기</button></article>')
    body += '''<script>document.querySelector('#more').onclick=function(){
        document.querySelector('tbody').innerHTML='';this.remove();
        document.querySelector('article').insertAdjacentHTML('beforeend','<p>검색 결과가 없습니다.</p>');
    };</script>'''
    serve(source,body)
    source._dom_timeout = 250
    assert len(source.collect(SearchCriteria(),None).candidates) == (0 if initial_empty else 3)


@pytest.mark.parametrize('controls', ['<button>더 불러오기</button><button>더 불러오기</button>',
    '<a rel="next" href="?page=2">다음</a><a rel="next" href="?page=3">다음</a>',
    '<a rel="next" href="?page=2">다음</a><button>더 불러오기</button>'])
def test_duplicate_controls_after_click_remain_schema_failure(source, controls):
    body = html('list.html').replace('</article>','<button id="more">더 불러오기</button></article>')
    body += '''<script>document.querySelector('#more').onclick=function(){
        this.remove();document.querySelector('article').insertAdjacentHTML('beforeend',CONTROLS);
    };</script>'''.replace('CONTROLS',json.dumps(controls))
    serve(source,body)
    source._dom_timeout = 200
    with pytest.raises(SourceSchemaError,match='컨트롤'):
        source.collect(SearchCriteria(),None)


@pytest.mark.parametrize('page_kind', ['valid','no-new-id','repeated','foreign'])
def test_more_to_numbered_page_keeps_page_validation(source, page_kind):
    params = 'type=problem&sort=idAsc&unrated=include'
    href = {'valid':'?'+params+'&page=2','no-new-id':'?'+params+'&page=2',
            'repeated':'?'+params,'foreign':'https://example.com/problem?page=2'}[page_kind]
    body = html('list.html').replace('</article>','<button id="more">더 불러오기</button></article>')
    body += '''<script>document.querySelector('#more').onclick=function(){
        this.outerHTML=NEXT;
    };</script>'''.replace('NEXT',json.dumps('<a rel="next" href="'+href+'">다음</a>'))
    second = html('list.html') if page_kind == 'no-new-id' else html('pagination.html')
    serve(source,lambda url:second if 'page=2' in url else body)
    source._dom_timeout = 300
    if page_kind == 'valid':
        assert [p.id for p in source.collect(SearchCriteria(),None).candidates] == [1000,1001,1002,1003]
    else:
        with pytest.raises(SourceSchemaError if page_kind == 'foreign' else SourceCompletenessError):
            source.collect(SearchCriteria(),None)


@pytest.mark.parametrize('update,error', [
    ("document.querySelector('img').src='/solved/99.svg'",SourceSchemaError),
    ("document.querySelector('td[data-col=\"정답\"]').textContent='bad'",SourceSchemaError),
    ("document.querySelector('table').remove()",SourceSchemaError),
    ("document.querySelector('article').insertAdjacentHTML('beforeend','<div role=\"alert\">실패</div>')",SourceAccessError)])
def test_absent_cursor_does_not_hide_invalid_current_listing(source, update, error):
    body = html('list.html').replace('</article>','<button id="more">더 불러오기</button></article>')
    body += '<script>document.querySelector("#more").onclick=function(){this.remove();UPDATE;};</script>'.replace('UPDATE',update)
    serve(source,body)
    source._dom_timeout = 200
    with pytest.raises(error):
        source.collect(SearchCriteria(),None)


@pytest.mark.parametrize('operation', ['list','recommend'])
def test_retained_cursor_collects_entire_population_before_limit(source, monkeypatch, operation):
    from algorithm_problem_picker.service import Picker
    body = html('site-listing.html')
    row = body.split('<tbody>')[1].split('</tbody>')[0].split('</tr>')[0]+'</tr>'
    first = row.replace('1000','1003')
    last = row.replace('1000','1004').replace('6510','99999')
    duplicate = row.replace('범위 밖 문제','later duplicate')
    body = body.replace('</article>','<button id="more">더 불러오기</button></article>')
    body += '''<script>document.querySelector('#more').onclick=function(){
        if(!this.dataset.step){document.querySelector('tbody').insertAdjacentHTML('beforeend',FIRST);this.dataset.step='1';}
        else{document.querySelector('tbody').insertAdjacentHTML('beforeend',LAST);this.remove();}
    };</script>'''.replace('FIRST',json.dumps(first)).replace('LAST',json.dumps(last+duplicate))
    serve(source,body)
    documents = []
    source._context.on('request',lambda request:documents.append(request.url) if request.resource_type == 'document' else None)
    def sample(items, k):
        assert k == 1 and [item.id for item in items] == [1000,1001,1002,1003,1004]
        assert items[0].title == '범위 밖 문제'
        return items[-1:]
    monkeypatch.setattr('random.sample',sample)
    source._dom_timeout = 250
    options = dict(limit=1,sort='accepted',order='desc') if operation == 'list' else dict(count=1)
    result = getattr(Picker(JungolPolicy(), source),operation)(SearchCriteria(min_tier=9,max_tier=13),**options)
    assert result.fetched_count == result.eligible_count == 5 and result.returned_count == 1
    assert result.problems[0].id == 1004 and result.problems[0].tier == Rated(8)
    assert len(documents) == 1 and '/problem?' in documents[0]


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


def test_user_search_same_handles_without_dom_completion_fails(source):
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
    source._dom_timeout = 650
    with pytest.raises(UserResolutionError, match='완전히'):
        source.resolve_user('Sample')
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
    serve(source,user_listing())
    interrupt = KeyboardInterrupt('original')
    def cancel(*args):
        raise interrupt
    class DisconnectedObserver:
        def evaluate(self, *args):
            raise Error('driver disconnected during cleanup')
        def dispose(self):
            pass
    monkeypatch.setattr(source,'_wait_user_page',cancel)
    monkeypatch.setattr(Locator,'evaluate_handle',lambda *args:DisconnectedObserver())
    with pytest.raises(KeyboardInterrupt) as caught:
        source.resolve_user('Sample')
    assert caught.value is interrupt


def test_cancel_during_load_more_preserves_interrupt(source, monkeypatch):
    from playwright.sync_api import Locator
    serve(source,html('list.html').replace('</article>','<button>더 불러오기</button></article>'))
    interrupt = KeyboardInterrupt('original')
    wait = source._wait_listing
    def cancel(previous=None, *args):
        if previous is not None:
            raise interrupt
        return wait()
    monkeypatch.setattr(source,'_wait_listing',cancel)
    monkeypatch.setattr(Locator,'evaluate_handle',lambda *args:pytest.fail('listing observer must be removed'))
    with pytest.raises(KeyboardInterrupt) as caught:
        source.collect(SearchCriteria(),None)
    assert caught.value is interrupt


def test_user_pages_with_same_handles_still_detect_ambiguity(source):
    body = user_listing().replace('</main>', '''<nav>
        <button class="page-num active" onclick="selectPage(1)">1</button>
        <button class="page-num" onclick="selectPage(2)">2</button></nav></main>''')
    body += '''<script>
        document.querySelector('.jg-find-search input').oninput=()=>{
            document.querySelector('#users').setAttribute('aria-busy','true');
            document.querySelector('.jg-find-result h3').textContent='@Sample';
            document.querySelector('#users').removeAttribute('aria-busy')};
        function selectPage(n){
            document.querySelector('#users').setAttribute('aria-busy','true');
            document.querySelectorAll('.page-num').forEach(e=>
                e.classList.toggle('active',Number(e.textContent)===n));
            setTimeout(()=>{document.querySelector('.jg-find-result h3').textContent='@Sample';
                document.querySelector('#users').removeAttribute('aria-busy')},150)
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
        body += '''<script>document.querySelector("#more").onclick=function(){
            document.querySelector('article').setAttribute('aria-busy','true');
            document.querySelector("tbody").insertAdjacentHTML("beforeend", ROW);this.remove();
            document.querySelector('article').removeAttribute('aria-busy')
        }</script>'''.replace('ROW', json.dumps(addition))
        serve(source, body)
    else:
        serve(source, body)
    listing = source.collect(SearchCriteria(**bounds), None)
    assert len(listing.candidates) == (3 if navigation == 'first' else 6)
    assert isinstance(listing.candidates[1].tier, Unrated)
    assert isinstance(listing.candidates[2].tier, Unavailable)


@pytest.mark.parametrize('bounds', [dict(min_tier=9,max_tier=13), dict(min_tier=9), dict(max_tier=10)])
@pytest.mark.parametrize('navigation', ['first','next','more'])
@pytest.mark.parametrize('operation', ['list','recommend'])
def test_rated_site_results_preserved_across_listing(source, monkeypatch, bounds, navigation, operation):
    from algorithm_problem_picker.service import Picker
    body = html('site-listing.html')
    rows = body.split('<tbody>')[1].split('</tbody>')[0]
    addition = rows.replace('1000','1003').replace('1001','1004').replace('1002','1005')
    if navigation == 'next':
        params = dict(type='problem',sort='idAsc',unrated='exclude',page=2)
        params.update({{'min_tier':'minTier','max_tier':'maxTier'}[key]:value for key,value in bounds.items()})
        first = body.replace('</article>','<a rel="next" href="?'+urlencode(params)+'">다음</a></article>')
        second = body.replace(rows,addition)
        serve(source,lambda url:second if 'page=2' in url else first)
    elif navigation == 'more':
        body = body.replace('</article>','<button id="more">더 불러오기</button></article>')
        body += '''<script>document.querySelector('#more').onclick=function(){
            const article=document.querySelector('article');article.setAttribute('aria-busy','true');
            document.querySelector('tbody').insertAdjacentHTML('beforeend',ROW);this.remove();
            article.removeAttribute('aria-busy');
        };</script>'''.replace('ROW',json.dumps(addition))
        serve(source,body)
    else:
        serve(source,body)
    messages = []
    monkeypatch.setattr(source,'_report',messages.append)
    result = getattr(Picker(JungolPolicy(), source),operation)(SearchCriteria(**bounds),
        **({'limit':10} if operation == 'list' else {'count':10}))
    expected_ids = [1000,1001,1002] if navigation == 'first' else [1000,1001,1002,1003,1004,1005]
    problems = sorted(result.problems,key=lambda problem:problem.id)
    assert [problem.id for problem in problems] == expected_ids
    assert [problem.tier for problem in problems] == [Rated(8),Rated(10),Rated(13)] * (1 if navigation == 'first' else 2)
    assert problems[1].accepted_count == Known(0) and problems[1].pass_rate.value == 0
    assert problems[1].pass_rate.value.as_tuple().exponent == -2
    assert result.fetched_count == result.eligible_count == result.returned_count == len(expected_ids)
    assert result.omitted_unknown_count == 0
    assert len(messages) == (1 if navigation == 'first' else 2)
    assert all(message.startswith('Collecting · 수집 ') for message in messages)


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
    body += '''<script>document.querySelector("#more").onclick=function(){
        document.querySelector('article').setAttribute('aria-busy','true');
        UPDATE;document.querySelector("tbody").insertAdjacentHTML("beforeend", ROW);this.remove();
        document.querySelector('article').removeAttribute('aria-busy')
    }</script>'''.replace('UPDATE',update).replace('ROW',json.dumps(addition))
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


@pytest.mark.parametrize('operation', ['list','recommend'])
@pytest.mark.parametrize('public_completion', [False,True])
def test_t041_current_rows_after_request_are_complete(source, operation, public_completion):
    from algorithm_problem_picker.service import Picker
    addition = html('pagination.html').split('<tbody>')[1].split('</tbody>')[0]
    body = html('list.html').replace('</article>','<button id="more">더 불러오기</button></article>')
    body += '''<script>document.querySelector('#more').onclick=async function(){
        START;this.disabled=true;await fetch('/fixture-more');this.remove();
        document.addEventListener('fixture-finish',()=>{
            document.querySelector('tbody').insertAdjacentHTML('beforeend',ROW);END;
        },{once:true});
    };</script>'''.replace('ROW',json.dumps(addition)).replace(
        'START',"document.querySelector('article').setAttribute('aria-busy','true')" if public_completion else '').replace(
        'END',"document.querySelector('article').removeAttribute('aria-busy')" if public_completion else '')
    serve(source,body)
    source._context.route('**/fixture-more',lambda route:route.fulfill(status=204))
    source._dom_timeout = 250
    stages = []
    result = getattr(Picker(JungolPolicy(), source,lambda progress:stages.append(progress.stage)),operation)(
        SearchCriteria(),**({'limit':1} if operation == 'list' else {'count':1}))
    assert result.fetched_count == result.eligible_count == 3 and result.returned_count == 1
    assert stages == ['Collecting','Processing','Complete']
    source._list_page.evaluate("document.dispatchEvent(new Event('fixture-finish'))")
    assert source._list_page.locator('tbody tr').count() == 4


def test_t041_empty_request_button_absence_is_completion(source):
    body = html('list.html').replace('</article>','<button id="more">더 불러오기</button></article>')
    body += '''<script>document.querySelector('#more').onclick=async function(){
        this.disabled=true;await fetch('/fixture-more');this.remove()};</script>'''
    serve(source,body)
    source._context.route('**/fixture-more',lambda route:route.fulfill(status=204))
    source._dom_timeout = 250
    assert len(source.collect(SearchCriteria(),None).candidates) == 3


@pytest.mark.parametrize('page_change', [False,True])
def test_t042_delayed_user_results_after_completed_request(source, page_change):
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


def test_t042_same_handle_refresh_after_completed_request(source):
    body = user_listing()+'''<script>document.querySelector('.jg-find-search input').oninput=async()=>{
        await fetch('/fixture-search');setTimeout(()=>{
        document.querySelector('.jg-find-result button').setAttribute('onclick',"location.href='/problem?solvedBy=84&solvedByMode=include'")},400)};</script>'''
    serve(source,body)
    source._context.route('**/fixture-search',lambda route:route.fulfill(status=204))
    assert source.resolve_user('Sample').account_id == 84


def test_t042_empty_result_after_completed_request(source):
    body = user_listing()+'''<script>document.querySelector('.jg-find-search input').oninput=async()=>{
        await fetch('/fixture-search');setTimeout(()=>{
        document.querySelector('.jg-find-result').remove();
        document.querySelector('#users').insertAdjacentHTML('beforeend','<p class="jg-find-note">검색 결과가 없습니다</p>')},400)};</script>'''
    serve(source,body)
    source._context.route('**/fixture-search',lambda route:route.fulfill(status=204))
    with pytest.raises(UserResolutionError, match='없음'):
        source.resolve_user('Sample')
    assert source._list_page.locator('.jg-find-result').count() == 0


@pytest.mark.parametrize('operation', ['list','recommend'])
def test_t041_current_rows_do_not_wait_for_future_control(source, operation):
    from algorithm_problem_picker.service import Picker
    addition = html('pagination.html').split('<tbody>')[1].split('</tbody>')[0]
    body = html('list.html').replace('</article>','<button id="more">더 불러오기</button></article>')
    body += '''<script>document.querySelector('#more').onclick=async function(){
        this.disabled=true;await fetch('/fixture-more');this.remove();
        document.querySelector('tbody').insertAdjacentHTML('beforeend',ROW);
        document.addEventListener('fixture-finish',()=>{
            const button=document.createElement('button');button.textContent='더 불러오기';
            button.onclick=function(){
                document.querySelector('tbody').insertAdjacentHTML('beforeend',LAST);this.remove();
            };document.querySelector('article').append(button);
        },{once:true});
    };</script>'''.replace('ROW',json.dumps(addition)).replace('LAST',json.dumps(addition.replace('1003','1004')))
    serve(source,body)
    source._context.route('**/fixture-more',lambda route:route.fulfill(status=204))
    source._dom_timeout = 250
    result = getattr(Picker(JungolPolicy(), source),operation)(SearchCriteria(),
        **({'limit':1} if operation == 'list' else {'count':1}))
    assert result.fetched_count == result.eligible_count == 4 and result.returned_count == 1
    source._list_page.evaluate("document.dispatchEvent(new Event('fixture-finish'))")
    source._list_page.get_by_role('button',name='더 불러오기',exact=True).click()
    assert source._list_page.locator('tbody tr').count() == 5


@pytest.mark.parametrize('same_handle', [False,True])
@pytest.mark.parametrize('intermediate', ['marker','same-heading','profile-link'])
def test_t042_intermediate_result_change_is_not_current_results(source, same_handle, intermediate):
    body = user_listing()
    if not same_handle:
        body = body.replace('@Sample ','@Other ')
    if intermediate == 'profile-link':
        body += '''<script>document.querySelector('.jg-find-result').insertAdjacentHTML('beforeend',
            '<a href="/user/previous">프로필</a>')</script>'''
    marker = {
        'marker':"document.querySelector('.jg-find-result').insertAdjacentHTML('beforeend','<span>updating</span>')",
        'same-heading':"document.querySelector('.jg-find-result h3').innerHTML='<span>updating</span>'+document.querySelector('.jg-find-result h3').innerHTML",
        'profile-link':"document.querySelector('.jg-find-result a').setAttribute('href','/user/current')",
    }[intermediate]
    update = ("document.querySelector('.jg-find-result button').setAttribute('onclick',"
              "\"location.href='/problem?solvedBy=84&solvedByMode=include'\")" if same_handle else
              "document.querySelector('.jg-find-result h3').textContent='@Sample'")
    body += '''<script>document.querySelector('.jg-find-search input').oninput=async()=>{
        MARKER;await fetch('/fixture-search');setTimeout(()=>{UPDATE},500)
    };</script>'''.replace('MARKER',marker).replace('UPDATE',update)
    serve(source,body)
    source._context.route('**/fixture-search',lambda route:route.fulfill(status=204))
    source._dom_timeout = 900
    assert source.resolve_user('Sample').account_id == (84 if same_handle else 42)


def test_t042_decorative_change_without_completion_fails(source):
    body = user_listing()+'''<script>document.querySelector('.jg-find-search input').oninput=async()=>{
        document.querySelector('.jg-find-result').insertAdjacentHTML('beforeend','<span>updating</span>');
        await fetch('/fixture-search');
    };</script>'''
    serve(source,body)
    source._context.route('**/fixture-search',lambda route:route.fulfill(status=204))
    source._dom_timeout = 250
    with pytest.raises(UserResolutionError,match='완전히'):
        source.resolve_user('Sample')


def test_unrelated_loading_cycle_does_not_complete_user_search(source):
    body = user_listing()+'''<script>document.querySelector('.jg-find-search input').oninput=()=>{
        const decoration=document.createElement('span');
        document.querySelector('.jg-find-result').append(decoration);
        decoration.setAttribute('aria-busy','true');decoration.removeAttribute('aria-busy');
    };</script>'''
    serve(source,body)
    source._dom_timeout = 250
    with pytest.raises(UserResolutionError):
        source.resolve_user('Sample')


def test_unrelated_loading_cycle_does_not_block_absent_cursor(source):
    body = html('list.html').replace('</article>','<button id="more">더 불러오기</button></article>')
    body += '''<script>document.querySelector('#more').onclick=function(){
        const decoration=document.createElement('span');document.querySelector('article').append(decoration);
        decoration.setAttribute('aria-busy','true');decoration.removeAttribute('aria-busy');this.remove();
    };</script>'''
    serve(source,body)
    source._dom_timeout = 250
    assert len(source.collect(SearchCriteria(),None).candidates) == 3
