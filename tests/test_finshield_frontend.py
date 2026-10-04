"""Frontend contract/security checks. Node checks need no npm dependencies."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"


def node_check(code):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for executable frontend checks")
    script = "const assert = require('node:assert/strict');\n"
    script += f"const fs = require({json.dumps(str(STATIC / 'finshield.js'))});\n"
    script += "(async () => {\n" + code + "\n})().catch(e => { console.error(e); process.exit(1); });"
    run = subprocess.run([node, "-"], input=script, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=20)
    assert run.returncode == 0, run.stdout + run.stderr


def test_accessible_shell_and_existing_screenshot_preserved():
    html = (STATIC / "finshield.html").read_text(encoding="utf-8")
    for copy in ("Synthetic data", "Simulated payments", "Payment status", "Investigation status",
                 "Counter-evidence", "Missing information", "Policy basis", "Approve held payment",
                 "Dismiss alert", 'id="review-reason"', 'id="review-confirm"', 'role="alert"'):
        assert copy in html
    assert 'lang="en"' in html
    home = (STATIC / "index.html").read_text(encoding="utf-8")
    assert 'id="shot-preview"' in home
    assert 'id="finshield-entry"' in home
    assert 'cfg.finshield_enabled === true' in home


def test_untrusted_content_has_no_html_or_storage_sink():
    script = (STATIC / "finshield.js").read_text(encoding="utf-8")
    for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "localStorage", "sessionStorage", "eval("):
        assert sink not in script
    assert "textContent" in script
    assert "expected_version" in script
    assert "permissions?.can_review === true" in script


def test_status_labels_and_money_are_truthful():
    node_check("""
      assert.equal(fs.paymentLabel('HOLD_PENDING_REVIEW'), 'Held for manual review');
      assert.equal(fs.paymentLabel('SIMULATED_PASSED'), 'Simulated payment passed');
      assert.equal(fs.paymentLabel('unknown'), 'Status unavailable');
      assert.equal(fs.money(50000, 'SGD'), 'SGD 500.00');
      assert.equal(fs.money(1.5, 'SGD'), 'Unavailable');
      assert.equal(fs.money(null, 'SGD'), 'Unavailable');
      assert.match(fs.modeLabel('offline_fixture'), /not live Gemini/);
      assert.match(fs.modeLabel('unexpected'), /unavailable/i);
    """)


def test_network_retry_reuses_key_and_preserves_security_headers():
    node_check("""
      const calls = []; let fail = true;
      const client = new fs.ApiClient(async (path, options) => {
        calls.push({path, ...options});
        if (fail) { fail = false; throw new Error('network'); }
        return {ok:true, status:200, json:async()=>({ok:true})};
      });
      client.csrf = 'test-csrf';
      await assert.rejects(client.post('/cases/case-one/payment', {}));
      await client.post('/cases/case-one/payment', {});
      assert.equal(calls[0].headers['Idempotency-Key'], calls[1].headers['Idempotency-Key']);
      assert.equal(calls[1].headers['X-CSRF-Token'], 'test-csrf');
      assert.equal(calls[1].credentials, 'same-origin');
      assert.equal(calls[1].path, '/api/finshield/cases/case-one/payment');
      await client.post('/cases/case-one/review', {action:'keep_hold', expected_version:1});
      await client.post('/cases/case-one/review', {action:'approve', expected_version:2});
      assert.notEqual(calls[2].headers['Idempotency-Key'], calls[3].headers['Idempotency-Key']);
    """)


def test_login_204_does_not_keep_secret_in_retry_cache():
    node_check("""
      const client = new fs.ApiClient(async()=>({ok:true, status:204}));
      assert.equal(await client.post('/review-login', {secret:'fixture-secret'}, false), null);
      assert.equal(client.keys.size, 0);
    """)


def test_http_errors_do_not_display_raw_server_messages():
    node_check("""
      const client = new fs.ApiClient(async()=>({ok:false, status:503,
        json:async()=>({error:{code:'<script>private details</script>'}})}));
      await assert.rejects(client.get('/cases/a'), e=>e.code === 'request_failed' && e.status === 503);
    """)


def test_citation_requires_same_case_full_provenance_and_exact_quote():
    node_check("""
      const citation = {case_id:'a', source_id:'a:s1', record_id:'a:r1', field:'text',
        quote:'<img src=x onerror=alert(1)>', dataset_version:'v1', policy_version:'1', call_index:1};
      const record = {case_id:'a', bundle:{sources:[{...citation, fields:{text:citation.quote}}]},
        result:{trace:[{tool_result:{evidence:[{...citation, fact_key:'message', fact_value:citation.quote}]}}]}};
      assert.equal(fs.resolveCitation(record, citation).quote, citation.quote);
      for (const change of [{case_id:'b'}, {quote:'invented'}, {call_index:2}, {record_id:'other'},
          {dataset_version:'v2'}, {policy_version:'2'}, {field:'other'}]) {
        assert.equal(fs.resolveCitation(record, {...citation, ...change}), null);
      }
      assert.equal(fs.resolveCitation({...record, result:null}, citation), null);
    """)


def test_reduced_motion_and_small_screen_layout():
    css = (STATIC / "finshield.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in css
    assert ":focus-visible" in css
    assert "overflow-wrap: anywhere" in css
    assert "@media" in css


# A tiny dependency-free DOM adapter executes the real application and its event
# handlers. It is not a browser/layout substitute; browser QA is reported separately.
DOM_HARNESS = r"""
const vm = require('node:vm');
const nodefs = require('node:fs');
const elements = new Map(); const nodes = []; const calls = [];
class Element {
  constructor(tag='div') {
    this.tagName=tag.toUpperCase(); this.children=[]; this.listeners={}; this.dataset={};
    this.attributes={}; this.disabled=false; this.hidden=false; this.open=false; this.value=''; this.checked=false;
    this.classList={toggle(){}}; nodes.push(this);
  }
  set textContent(value) { this.content=String(value); this.children=[]; }
  get textContent() { return (this.content || '') + this.children.map(n=>n.textContent).join(' '); }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.content=''; this.children=items; }
  setAttribute(key,value) { this.attributes[key]=value; }
  removeAttribute(key) { delete this.attributes[key]; }
  addEventListener(event,fn) { this.listeners[event]=fn; }
  scrollIntoView() { this.scrolled=true; }
  focus() { document.activeElement=this; }
  remove() {}
}
const markup=nodefs.readFileSync(__HTML_PATH__, 'utf8');
for(const match of markup.matchAll(/<([a-z][a-z0-9]*)\b([^>]*\bid="([^"]+)"[^>]*)>/g)) {
  const node=new Element(match[1]); elements.set(match[3],node);
  node.hidden=/\bhidden\b/.test(match[2]);
  const template=match[2].match(/data-template="([^"]+)"/);
  if(template) node.dataset.template=template[1];
}
const document={getElementById:id=>elements.get(id), createElement:tag=>new Element(tag), body:new Element('body'),
  querySelectorAll:selector=>nodes.filter(n=>selector==='[data-template]' ? !!n.dataset.template :
    selector==='[data-invalid-citation="true"]' ? n.dataset.invalidCitation==='true' :
    ['BUTTON','INPUT','TEXTAREA','SELECT'].includes(n.tagName))};
const caseId='11111111-1111-5111-8111-111111111111';
const otherId='22222222-2222-5222-8222-222222222222';
const citation={case_id:caseId,source_id:'case-one:s1',record_id:'current',field:'conversation',
  quote:'<img src=x onerror=alert(1)> https://untrusted.example',dataset_version:'fs-demo-v1',policy_version:'1',call_index:1};
const fixture={case_id:caseId,version:0,mode:'offline_fixture',payment_status:'PENDING_CHECK',
  investigation_status:'NOT_STARTED',permissions:{can_review:false,reviewer_available:true},events:[],result:null,rule_result:null,
  bundle:{template_id:'risk-fee',conversation_id:'case-one:risk-conv',current:{amount_minor:50000,currency:'SGD'},
    sources:[{...citation,fields:{conversation:citation.quote}}]}};
const clone=value=>JSON.parse(JSON.stringify(value));
const caseResponses=new Map();
let failInvestigation=false, paymentAtInvestigation='', conflict=false;
let resumed=false, knownCases=[], apiFailure=null, timeoutPath='';
let schedule=setTimeout, cancel=clearTimeout;
const location={href:'http://localhost/finshield'};
const history={replaceState(_state,_title,url){location.href=new URL(url,location.href).href;}};
function reply(value,status=200) { return {ok:status<400,status,json:async()=>clone(value)}; }
const fetcher=async(url,options)=>{
  const body=options.body ? JSON.parse(options.body) : null;
  calls.push({url,...options,body});
  if(timeoutPath && url.endsWith(timeoutPath)) return new Promise(()=>{});
  if(apiFailure && url.endsWith(apiFailure.path)) return reply({error:{code:apiFailure.code}},apiFailure.status);
  if(url.endsWith('/sessions')) {
    if(body.resume_only && !resumed) return reply({error:{code:'unauthorized'}},401);
    resumed=true;return reply({csrf_token:'csrf-fixture',cases:knownCases,reviewer_available:fixture.permissions.reviewer_available});
  }
  if(url.endsWith('/review-login')) {fixture.permissions.can_review=true;return reply(null,204);}
  if(url.endsWith('/cases')) {
    knownCases=[{case_id:caseId,template_id:'risk-fee'}];return reply(fixture);
  }
  if(url.endsWith('/payment')) {fixture.payment_status='HOLD_PENDING_REVIEW';fixture.version++;
    fixture.rule_result={evaluated_rule_ids:['H1','H2'],matched_rule_ids:['H1','H2'],policy_id:'DEMO-PAYMENT',policy_version:'1',
      metrics:{count:3,total_minor:270000,window_start:'03:40Z',window_end:'04:00Z'}};return reply(fixture);}
  if(url.endsWith('/investigation')) {
    paymentAtInvestigation=elements.get('payment-status').textContent;
    if(failInvestigation) {failInvestigation=false;throw Error('lost');}
    fixture.investigation_status='READY'; fixture.version++;
    fixture.result={status:'READY',trace:[{tool_result:{evidence:[{...citation}]}}],
      report:{findings:[{text:'Synthetic fixture finding',citations:[citation,{...citation,quote:'wrong'}]}],
        counter_evidence:[{text:'A reasonable alternative exists',citations:[citation]}],
        policy_basis:[],missing_information:['Manual confirmation'],suggested_next_steps:['Review the cited evidence']}};
    return reply(fixture.result);
  }
  if(url.endsWith('/vip')) {fixture.vip_used=true;fixture.vip_answer='VIP does not release the payment.';fixture.version++;return reply({answer:fixture.vip_answer});}
  if(url.endsWith('/review')) {
    if(conflict) {conflict=false;fixture.version++;return reply({error:{code:'version_conflict'}},409);}
    assert.equal(body.expected_version,fixture.version);
    fixture.events.push({action:body.action,actor_id:'reviewer',reason:body.reason,before:fixture.payment_status,
      after:body.action==='approve'?'SIMULATED_PASSED':fixture.payment_status,at:'2026-10-02T04:01:00Z'});
    fixture.payment_status=fixture.events.at(-1).after;fixture.version++;return reply(fixture);
  }
  return reply(caseResponses.get(url.split('/').at(-1)) || fixture);
};
__SETUP__
vm.runInNewContext(nodefs.readFileSync(__JS_PATH__,'utf8'),{document,fetch:fetcher,crypto,console,setTimeout:(...args)=>schedule(...args),clearTimeout:(...args)=>cancel(...args),AbortController,URL,Blob,location,history});
const el=id=>elements.get(id);
await new Promise(setImmediate);
async function fire(id,event='click') {
  const fn=el(id).listeners[event]; assert.ok(fn,'Missing handler: '+id);
  await fn({preventDefault(){}}); await new Promise(setImmediate);
}
"""


def ui_check(code, setup=""):
    harness = DOM_HARNESS.replace("__HTML_PATH__", json.dumps(str(STATIC / "finshield.html")))
    harness = harness.replace("__JS_PATH__", json.dumps(str(STATIC / "finshield.js")))
    harness = harness.replace("__SETUP__", setup)
    node_check(harness + code)


def test_real_ui_payment_before_investigation_citations_vip_and_review():
    ui_check(r"""
      await fire('open-case');
      assert.equal(el('review-form').hidden,true);
      assert.equal(el('conversation').textContent,citation.quote);
      await fire('check-payment');
      assert.equal(paymentAtInvestigation,'Held for manual review');
      assert.equal(el('history-total').textContent,'SGD 2,700.00');
      assert.match(el('mode-note').textContent,/not live Gemini/);
      const valid=nodes.find(n=>n.dataset.invalidCitation==='false');
      const invalid=nodes.find(n=>n.dataset.invalidCitation==='true');
      assert.equal(valid.disabled,false);assert.equal(invalid.disabled,true);
      valid.listeners.click();
      assert.equal(document.activeElement,el('source-inspector'));
      assert.match(el('source-inspector').textContent,/<img src=x/);
      assert.equal(el('source-inspector').children.some(n=>n.tagName==='A'),false);
      const reviewCount=calls.filter(c=>c.url.endsWith('/review')).length;
      await fire('ask-vip');
      assert.equal(calls.filter(c=>c.url.endsWith('/review')).length,reviewCount);
      assert.equal(el('payment-status').textContent,'Held for manual review');
      el('reviewer-id').value='demo-reviewer';el('reviewer-secret').value='test-only-secret';
      await fire('review-login','submit');
      assert.equal(el('reviewer-secret').value,'');assert.equal(el('review-form').hidden,false);
      assert.match(el('review-availability').textContent,/authorized.*this case/i);
      assert.doesNotMatch(el('review-availability').textContent,/choose reviewer/i);
      el('review-action').value='dismiss';el('review-reason').value='Manual checks documented';el('review-confirm').checked=true;
      await fire('review-form','submit');assert.equal(el('payment-status').textContent,'Held for manual review');
      el('review-action').value='approve';el('review-reason').value='Records reviewed';el('review-confirm').checked=true;
      await fire('review-form','submit');assert.equal(el('payment-status').textContent,'Simulated payment passed');
      assert.match(el('audit-list').textContent,/Records reviewed/);
      assert.match(el('payment-note').textContent,/approved by an authorized reviewer/);
      assert.doesNotMatch(el('payment-note').textContent,/passed the demo policy/);
    """)


def test_real_ui_investigation_failure_retains_hold_and_retry_key():
    ui_check(r"""
      await fire('open-case');failInvestigation=true;await fire('check-payment');
      assert.equal(el('payment-status').textContent,'Held for manual review');
      assert.match(el('investigation-notice').textContent,/Manual review is required/);
      assert.equal(el('investigation-status').textContent,'Outcome not confirmed');
      assert.equal(el('investigate').disabled,false);
      await fire('investigate');
      const attempts=calls.filter(c=>c.url.endsWith('/investigation'));
      assert.equal(attempts.length,2);
      assert.equal(attempts[0].headers['Idempotency-Key'],attempts[1].headers['Idempotency-Key']);
      assert.equal(el('payment-status').textContent,'Held for manual review');
    """)


def test_real_ui_review_conflict_requires_new_confirmation_and_clears_template():
    ui_check(r"""
      await fire('open-case');await fire('check-payment');
      el('reviewer-id').value='demo';el('reviewer-secret').value='test-only';await fire('review-login','submit');
      el('review-action').value='approve';el('review-reason').value='Manual checks';el('review-confirm').checked=true;
      conflict=true;await fire('review-form','submit');
      assert.equal(el('review-confirm').checked,false);
      assert.match(el('feedback').textContent,/case changed/);
      assert.equal(el('payment-status').textContent,'Held for manual review');
      const count=calls.filter(c=>c.url.endsWith('/review')).length;
      await fire('review-form','submit');assert.equal(calls.filter(c=>c.url.endsWith('/review')).length,count);
      await fire('template-normal');
      assert.equal(el('review-form').hidden,true);
      assert.equal(el('source-count').textContent,'No sources');
      assert.equal(el('payment-status').textContent,'Not checked');
      assert.match(el('conversation').textContent,/INV-N-1/);
    """)


@pytest.mark.parametrize("phase,path,budget", [
    ("fetch", "/cases/a/payment", 45000),
    ("parse", "/cases/a/investigation", 55000),
])
def test_request_deadline_covers_fetch_and_body_retains_retry_identity(phase, path, budget):
    # A response whose headers arrive but body stalls must not leave controls busy forever.
    node_check("""
      const timers=new Map();let next=0;const cleared=[];
      global.setTimeout=(fn,ms)=>{const id=++next;timers.set(id,{fn,ms});return id;};
      global.clearTimeout=id=>{cleared.push(id);timers.delete(id);};
      const requests=[];let stall=true;
      const client=new fs.ApiClient(async(url,options)=>{
        requests.push(options);
        if(stall && PHASE==='fetch') return new Promise(()=>{});
        return {ok:true,status:200,json:()=>stall ? new Promise(()=>{}) : Promise.resolve({ok:true})};
      });
      const pending=client.post(PATH,{});
      await new Promise(setImmediate);
      assert.equal(timers.size,1,'A bounded deadline must be active');
      const [id,timer]=[...timers][0];assert.equal(timer.ms,BUDGET);
      const rejected=assert.rejects(pending,e=>e.code==='request_timeout');
      timer.fn();await rejected;
      assert.equal(requests[0].signal.aborted,true);
      assert.equal(timers.size,0);assert.ok(cleared.includes(id));
      stall=false;await client.post(PATH,{});
      assert.equal(requests[0].headers['Idempotency-Key'],requests[1].headers['Idempotency-Key']);
      assert.equal(timers.size,0,'Successful parsing must clear its deadline');
    """.replace("PHASE", json.dumps(phase)).replace("PATH", json.dumps(path)).replace("BUDGET", str(budget)))


def test_startup_without_session_does_not_allocate_and_remains_a_preview():
    ui_check(r"""
      assert.equal(calls.length,1);
      assert.deepEqual(calls[0].body,{resume_only:true});
      assert.equal(el('feedback').hidden,true,'First visit is not an expired-session error');
      assert.equal(el('open-case').hidden,false);
      assert.equal(el('report-details').open,false);
      assert.equal(el('source-details').open,false);
      assert.match(el('mode-note').textContent,/not checked/i);
      assert.match(el('next-action').textContent,/open/i);
    """)


@pytest.mark.parametrize("query", ["selected", "unsafe", "foreign", "absent"])
def test_startup_resumes_owned_case_from_safe_query_or_available_default(query):
    setup = """
      resumed=true;knownCases=[{case_id:caseId,template_id:'risk-fee'},{case_id:otherId,template_id:'normal-invoice'}];
    """
    if query == "selected":
        setup += "location.href+='?case='+otherId;fixture.case_id=otherId;fixture.bundle.template_id='normal-invoice';"
    elif query == "unsafe":
        setup += "location.href+='?case=../../review-login';"
    elif query == "foreign":
        setup += "location.href+='?case=33333333-3333-5333-8333-333333333333';"
    ui_check(r"""
      assert.equal(calls.length,2,'Resume and GET only; no creation');
      assert.deepEqual(calls[0].body,{resume_only:true});
      assert.equal(calls[1].url,'/api/finshield/cases/'+fixture.case_id);
      assert.equal(calls[1].method,'GET');
      assert.equal(el('open-case').hidden,true);
      assert.equal(el('check-payment').disabled,false);
      assert.equal(new URL(location.href).searchParams.get('case'),fixture.case_id);
      await fire('check-payment');
      assert.equal(calls.find(c=>c.url.endsWith('/payment')).headers['X-CSRF-Token'],'csrf-fixture');
    """, setup)


def test_template_reopen_uses_get_and_keeps_url_in_sync():
    ui_check(r"""
      await fire('open-case');
      assert.equal(new URL(location.href).searchParams.get('case'),caseId);
      await fire('template-normal');
      assert.equal(new URL(location.href).searchParams.has('case'),false);
      await fire('template-risk');
      assert.equal(el('payment-status').textContent,'Pending server check');
      assert.equal(new URL(location.href).searchParams.get('case'),caseId);
      assert.equal(calls.filter(c=>c.url.endsWith('/cases')).length,1);
    """)


@pytest.mark.parametrize("failure", ["503", "timeout"])
def test_existing_normal_switch_failure_preserves_identity_and_refreshes_same_case(failure):
    ui_check(r"""
      assert.equal(new URL(location.href).searchParams.get('case'),caseId);
      const selectedPath='/api/finshield/cases/'+otherId;
      const beforeSwitch=calls.length;
      const timers=new Map();let next=0;
      schedule=(fn,ms)=>{timers.set(++next,{fn,ms});return next;};cancel=id=>timers.delete(id);
      if(FAILURE==='timeout') timeoutPath=otherId;
      else apiFailure={path:otherId,code:'storage_unavailable',status:503};
      const switching=fire('template-normal');
      await new Promise(setImmediate);
      if(FAILURE==='timeout') {
        assert.equal(timers.size,1);
        [...timers.values()][0].fn();
      }
      await switching;
      assert.equal(calls[beforeSwitch].url,selectedPath);
      assert.equal(new URL(location.href).searchParams.get('case'),otherId,'A failed selected-case GET must retain the owned case ID');
      assert.equal(el('case-title').textContent,'Service invoice');
      assert.equal(el('refresh-case').hidden,false);
      assert.equal(el('refresh-case').disabled,false);
      assert.equal(el('open-case').hidden,true,'An existing selected case needs recovery, not creation');
      assert.equal(el('check-payment').disabled,true);
      assert.match(el('next-action').textContent,/refresh/i);
      if(FAILURE==='timeout') {
        assert.match(el('feedback').textContent,/outcome.*uncertain/i);
        assert.equal(el('template-risk').disabled,true);
      } else assert.match(el('feedback').textContent,/storage.*unavailable/i);

      // A second failure cannot default to the risk case or release uncertainty.
      timeoutPath='';apiFailure={path:otherId,code:'storage_unavailable',status:503};
      await fire('refresh-case');
      assert.equal(new URL(location.href).searchParams.get('case'),otherId);
      assert.equal(el('refresh-case').hidden,false);
      assert.equal(el('check-payment').disabled,true);
      if(FAILURE==='timeout') assert.equal(el('template-risk').disabled,true);

      // Even a successful response must match the selected owned case identity.
      apiFailure=null;caseResponses.set(otherId,{...normalCase,case_id:caseId});
      await fire('refresh-case');
      assert.equal(new URL(location.href).searchParams.get('case'),otherId);
      assert.equal(el('check-payment').disabled,true);
      if(FAILURE==='timeout') assert.equal(el('template-risk').disabled,true);

      caseResponses.set(otherId,normalCase);
      await fire('refresh-case');
      assert.equal(new URL(location.href).searchParams.get('case'),otherId);
      assert.equal(el('case-title').textContent,'Service invoice');
      assert.match(el('case-id').textContent,new RegExp(otherId));
      assert.equal(el('check-payment').disabled,false);
      assert.equal(el('template-risk').disabled,false);
      assert.equal(el('feedback').hidden,true);
      assert.ok(calls.slice(beforeSwitch).every(call=>call.url===selectedPath && call.method==='GET'),
        'Recovery must only GET the selected Service invoice, never resume/default or create another case');
      assert.equal(timers.size,0);
    """.replace("FAILURE", json.dumps(failure)), """
      resumed=true;knownCases=[{case_id:caseId,template_id:'risk-fee'},{case_id:otherId,template_id:'normal-invoice'}];
      const normalCase=clone(fixture);normalCase.case_id=otherId;normalCase.bundle.template_id='normal-invoice';
      normalCase.bundle.sources=[{...citation,case_id:otherId,source_id:otherId+':s1',
        fields:{conversation:'Please pay invoice INV-N-1 for the service already delivered.'}}];
      caseResponses.set(otherId,normalCase);
    """)


def test_reviewer_unavailable_blocks_credentials_and_preserves_hold():
    ui_check(r"""
      assert.equal(el('login-submit').disabled,true);
      assert.equal(el('reviewer-secret').disabled,true);
      assert.equal(el('reviewer-id').disabled,true);
      assert.match(el('review-access').textContent,/unavailable/i);
      el('reviewer-id').value='reviewer-a';el('reviewer-secret').value='test-only';
      await fire('review-login','submit');
      assert.equal(calls.some(c=>c.url.endsWith('/review-login')),false);
      assert.equal(el('payment-status').textContent,'Held for manual review');
    """, "resumed=true;knownCases=[{case_id:caseId,template_id:'risk-fee'}];fixture.permissions.reviewer_available=false;fixture.payment_status='HOLD_PENDING_REVIEW';")


@pytest.mark.parametrize("code,status,words", [
    ("session_capacity_reached", 429, "session.*capacity"),
    ("review_login_locked", 429, "reviewer.*locked"),
    ("reviewer_unavailable", 503, "reviewer.*unavailable"),
    ("case_capacity_reached", 409, "case.*capacity"),
    ("unauthorized", 401, "session.*expired"),
    ("storage_unavailable", 503, "storage.*unavailable"),
])
def test_specific_recovery_copy(code, status, words):
    ui_check("""
      await fire('open-case');
      apiFailure={path:'/payment',code:CODE,status:STATUS};
      await fire('check-payment');
      assert.match(el('feedback').textContent,new RegExp(WORDS,'i'));
    """.replace("CODE", json.dumps(code)).replace("STATUS", str(status)).replace("WORDS", json.dumps(words)))


def test_lifetime_session_capacity_requires_owner_intervention_not_waiting():
    ui_check(r"""
      apiFailure={path:'/sessions',code:'session_capacity_reached',status:429};
      await fire('open-case');
      assert.match(el('feedback').textContent,/owner intervention.*required/i);
      assert.doesNotMatch(el('feedback').textContent,/wait|retry|try again/i);
      assert.equal(calls.some(c=>c.url.endsWith('/cases')),false);
    """)


def test_evidence_formats_money_without_losing_raw_values_or_provenance():
    ui_check(r"""
      await fire('open-case');
      assert.match(el('source-list').textContent,/Amount.*SGD 500\.01/);
      assert.match(el('source-list').textContent,/amount_minor.*50001/);
      assert.match(el('source-list').textContent,/fs-demo-v1/);
      assert.match(el('source-list').textContent,/case-one:s1/);
      assert.match(el('source-list').textContent,/currency.*SGD/);
    """, "fixture.bundle.sources[0].fields={conversation:citation.quote,amount_minor:50001,currency:'SGD'};")


def test_report_formats_verified_numeric_facts_and_keeps_exact_claim():
    ui_check(r"""
      assert.match(el('findings').textContent,/Settled history total: SGD 2,700\.01/);
      assert.match(el('findings').textContent,/Settled history total \(SGD minor units\): 270001/);
      assert.match(el('findings').textContent,/history_total_minor/);
      assert.equal(el('report-details').open,true);
      assert.equal(el('step-3').attributes['aria-current'],'step');
    """, """
      resumed=true;knownCases=[{case_id:caseId,template_id:'risk-fee'}];fixture.investigation_status='READY';fixture.payment_status='HOLD_PENDING_REVIEW';
      citation.field='total_minor';citation.quote='270001';citation.fact_value=270001;citation.fact_key='history_total_minor';
      fixture.bundle.sources=[{...citation,fields:{total_minor:270001,currency:'SGD'}}];
      fixture.result={trace:[{tool_result:{evidence:[citation]}}],report:{findings:[{
        text:'Settled history total (SGD minor units): 270001',fact_key:'history_total_minor',fact_value:270001,citations:[citation]}]}};
    """)


def test_timeout_blocks_mutations_until_successful_refresh_and_reuses_key():
    ui_check(r"""
      await fire('open-case');
      const timers=new Map();let next=0;
      schedule=(fn,ms)=>{timers.set(++next,{fn,ms});return next;};cancel=id=>timers.delete(id);
      timeoutPath='/payment';
      const operation=fire('check-payment');await new Promise(setImmediate);
      assert.equal(el('check-payment').disabled,true);
      [...timers.values()][0].fn();await operation;
      assert.match(el('feedback').textContent,/outcome.*uncertain/i);
      assert.match(el('feedback').textContent,/Refresh.*before/i);
      assert.equal(el('workspace').attributes['aria-busy'],'false');
      assert.equal(el('check-payment').disabled,true);
      assert.equal(el('refresh-case').disabled,false);
      assert.equal(el('template-normal').disabled,true,'A timeout must not leave an apparently usable but inert template selector');
      await fire('check-payment');
      assert.equal(calls.filter(c=>c.url.endsWith('/payment')).length,1);
      timeoutPath='';apiFailure={path:caseId,code:'storage_unavailable',status:503};
      await fire('refresh-case');assert.equal(el('check-payment').disabled,true);
      apiFailure=null;await fire('refresh-case');assert.equal(el('check-payment').disabled,false);
      await fire('check-payment');
      const payments=calls.filter(c=>c.url.endsWith('/payment'));
      assert.equal(payments[0].headers['Idempotency-Key'],payments[1].headers['Idempotency-Key']);
      assert.equal(timers.size,0);
    """)


def test_exact_large_money_has_no_float_rounding():
    node_check("assert.equal(fs.money(Number.MAX_SAFE_INTEGER,'SGD'),'SGD 90,071,992,547,409.91');")


def test_actual_offline_report_uses_readable_money_and_preserves_provenance():
    from tests.test_finshield_api import bootstrap, client_for

    client, _, _ = client_for()
    case = bootstrap(client)
    path = "/api/finshield/cases/" + case["case_id"]
    assert client.post(path + "/payment", json={}, headers={"Idempotency-Key": "readable-payment"}).status_code == 200
    assert client.post(path + "/investigation", json={}, headers={"Idempotency-Key": "readable-investigation"}).status_code == 200
    actual = client.get(path).json()
    ui_check(r"""
      assert.match(el('findings').textContent,/Settled history total: SGD 2,700\.00/);
      assert.match(el('findings').textContent,/Amount: SGD 500\.00/);
      assert.match(el('findings').textContent,/Settled history total \(SGD minor units\): 270000/);
      assert.match(el('findings').textContent,/Amount_minor: 50000/);
      const details=el('findings').children.flatMap(n=>n.children).filter(n=>n.tagName==='DETAILS');
      assert.ok(details.length>=2);
      assert.ok(details.every(n=>!n.open),'Exact claims remain available without overwhelming the readable summary');
      assert.match(details.map(n=>n.textContent).join(' '),/dataset_version/);
      assert.match(details.map(n=>n.textContent).join(' '),/call_index/);
      const totalCitation=nodes.find(n=>n.dataset.invalidCitation==='false' && /Source 1 · Settled history total/.test(n.textContent));
      assert.ok(totalCitation,'Derived history citation needs the same readable label as the claim');
      totalCitation.listeners.click();
      assert.match(el('source-inspector').textContent,/Settled history total: SGD 2,700\.00/);
      assert.match(el('source-inspector').textContent,/270000/);
    """, "resumed=true;Object.assign(fixture," + json.dumps(actual) + ");knownCases=[{case_id:fixture.case_id,template_id:'risk-fee'}];")


def test_unknown_fact_key_remains_plain_text_instead_of_becoming_a_numeric_field():
    ui_check(r"""
      assert.match(el('findings').textContent,/Unknown fact kept verbatim/);
      assert.equal(el('feedback').hidden,true);
    """, """
      resumed=true;knownCases=[{case_id:caseId,template_id:'risk-fee'}];
      citation.fact_key='constructor';citation.fact_value=123;
      fixture.result={trace:[{tool_result:{evidence:[citation]}}],report:{findings:[{
        text:'Unknown fact kept verbatim',fact_key:'constructor',fact_value:123,citations:[citation]}]}};
    """)


def test_failed_payment_does_not_show_the_check_step_as_complete():
    ui_check(r"""
      assert.equal(el('step-1').attributes['aria-current'],'step');
      assert.equal(el('investigate').disabled,true);
      assert.match(el('next-action').textContent,/check failed/i);
    """, "resumed=true;knownCases=[{case_id:caseId,template_id:'risk-fee'}];fixture.payment_status='CHECK_FAILED';")
