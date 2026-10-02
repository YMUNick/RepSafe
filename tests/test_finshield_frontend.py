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
    run = subprocess.run([node, "-e", script], cwd=ROOT, capture_output=True, text=True)
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
    this.attributes={}; this.disabled=false; this.hidden=false; this.value=''; this.checked=false;
    this.classList={toggle(){}}; nodes.push(this);
  }
  set textContent(value) { this.content=String(value); this.children=[]; }
  get textContent() { return (this.content || '') + this.children.map(n=>n.textContent).join(' '); }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.content=''; this.children=items; }
  setAttribute(key,value) { this.attributes[key]=value; }
  addEventListener(event,fn) { this.listeners[event]=fn; }
  scrollIntoView() { this.scrolled=true; }
  focus() { document.activeElement=this; }
  remove() {}
}
const markup=nodefs.readFileSync(__HTML_PATH__, 'utf8');
for(const match of markup.matchAll(/<([a-z][a-z0-9]*)\b([^>]*\bid="([^"]+)"[^>]*)>/g)) {
  const node=new Element(match[1]); elements.set(match[3],node);
  const template=match[2].match(/data-template="([^"]+)"/);
  if(template) node.dataset.template=template[1];
}
const document={getElementById:id=>elements.get(id), createElement:tag=>new Element(tag), body:new Element('body'),
  querySelectorAll:selector=>nodes.filter(n=>selector==='[data-template]' ? !!n.dataset.template :
    selector==='[data-invalid-citation="true"]' ? n.dataset.invalidCitation==='true' :
    ['BUTTON','INPUT','TEXTAREA','SELECT'].includes(n.tagName))};
const citation={case_id:'case-one',source_id:'case-one:s1',record_id:'current',field:'conversation',
  quote:'<img src=x onerror=alert(1)> https://untrusted.example',dataset_version:'fs-demo-v1',policy_version:'1',call_index:1};
const fixture={case_id:'case-one',version:0,mode:'offline_fixture',payment_status:'PENDING_CHECK',
  investigation_status:'NOT_STARTED',permissions:{can_review:false},events:[],result:null,rule_result:null,
  bundle:{template_id:'risk-fee',conversation_id:'case-one:risk-conv',current:{amount_minor:50000,currency:'SGD'},
    sources:[{...citation,fields:{conversation:citation.quote}}]}};
const clone=value=>JSON.parse(JSON.stringify(value));
let failInvestigation=false, paymentAtInvestigation='', conflict=false;
function reply(value,status=200) { return {ok:status<400,status,json:async()=>clone(value)}; }
const fetcher=async(url,options)=>{
  const body=options.body ? JSON.parse(options.body) : null;
  calls.push({url,body,...options});
  if(url.endsWith('/sessions')) return reply({csrf_token:'csrf-fixture'});
  if(url.endsWith('/review-login')) {fixture.permissions.can_review=true;return reply(null,204);}
  if(url.endsWith('/cases')) return reply(fixture);
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
  return reply(fixture);
};
vm.runInNewContext(nodefs.readFileSync(__JS_PATH__,'utf8'),{document,fetch:fetcher,crypto,console,setTimeout,URL,Blob});
const el=id=>elements.get(id);
async function fire(id,event='click') {
  const fn=el(id).listeners[event]; assert.ok(fn,'Missing handler: '+id);
  await fn({preventDefault(){}}); await new Promise(setImmediate);
}
"""


def ui_check(code):
    harness = DOM_HARNESS.replace("__HTML_PATH__", json.dumps(str(STATIC / "finshield.html")))
    harness = harness.replace("__JS_PATH__", json.dumps(str(STATIC / "finshield.js")))
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
