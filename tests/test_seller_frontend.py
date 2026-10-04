"""Execute the seller page's actual event handlers with boundary doubles."""
import json
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest


class SellerMarkup(HTMLParser):
    """Keep real markup ancestry/attributes for visibility and live-region checks."""

    VOID_TAGS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
                 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self, html):
        super().__init__()
        self.nodes = []
        self.stack = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        index = len(self.nodes)
        self.nodes.append({'tag': tag, 'attrs': dict(attrs),
                           'parent': self.stack[-1] if self.stack else None})
        if tag not in self.VOID_TAGS:
            self.stack.append(index)

    def handle_endtag(self, tag):
        for offset in range(len(self.stack) - 1, -1, -1):
            if self.nodes[self.stack[offset]]['tag'] == tag:
                del self.stack[offset:]
                break

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID_TAGS:
            self.handle_endtag(tag)


def seller_check(check, initial_mode='ok'):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js is required')
    path = Path(__file__).resolve().parents[1] / 'app/static/index.html'
    harness = r'''
const assert = require('node:assert/strict'), vm = require('node:vm');
const html = require('node:fs').readFileSync(__PATH__, 'utf8');
class Element {
  constructor(attrs={}){this.value='';this.hidden='hidden' in attrs;this.dataset={};this.attributes=attrs;this.listeners={};this.children=[];this.textContent='';this.classList={toggle(){},add(){}};this.parentElement=null;
    for(const [k,v] of Object.entries(attrs))if(k.startsWith('data-'))this.dataset[k.slice(5)]=v;}
  addEventListener(name, fn){(this.listeners[name] ||= []).push(fn);}
  setAttribute(k,v){this.attributes[k]=v;} getAttribute(k){return this.attributes[k];}
  set src(v){this.setAttribute('src',v);} get src(){return this.getAttribute('src');}
  removeAttribute(k){delete this.attributes[k];} replaceChildren(...c){this.children=c;} append(...c){this.children.push(...c);} appendChild(c){this.append(c);}
  focus(){document.activeElement=this;focusCalls++;} scrollIntoView(){} querySelector(){return new Element();}
  async fire(name,event={}){for(const fn of this.listeners[name]||[]) await fn(event);}
}
const markup=__MARKUP__, nodes=markup.map(n=>new Element(n.attrs));
markup.forEach((n,i)=>{if(n.parent!==null){nodes[i].parentElement=nodes[n.parent];nodes[n.parent].append(nodes[i]);}});
const elements=new Map(nodes.filter(n=>n.attributes.id).map(n=>[n.attributes.id,n]));
const el=id=>elements.get(id);
const samples=nodes.filter(n=>'sample' in n.dataset), steps=nodes.filter(n=>(n.attributes.class||'').split(' ').includes('step'));
const visible=node=>!!node&&!node.hidden&&(!node.parentElement||visible(node.parentElement));
const timers=new Map();let nextTimer=0,focusCalls=0;
const document={activeElement:null,getElementById:el,querySelectorAll:s=>s==='.step'?steps:s==='[data-sample]'?samples:s==='.sample'?nodes.filter(n=>(n.attributes.class||'').split(' ').includes('sample')):[],createElement:()=>new Element(),documentElement:{}};
const requests=[];let fetchMode=__MODE__;
const fetcher=(url,options={})=>{
  const request={url,options};requests.push(request);
  // Deliberately permit late success after abort to exercise the real stale-result guard.
  if(fetchMode==='controlled-response')return new Promise(resolve=>{request.succeed=body=>resolve({ok:true,json:async()=>body});});
  if(fetchMode==='controlled-body')return Promise.resolve({ok:true,json:()=>new Promise(resolve=>{request.succeed=resolve;})});
  if(fetchMode==='pending')return new Promise((resolve,reject)=>{options.signal?.addEventListener('abort',()=>reject(Object.assign(new Error('aborted'),{name:'AbortError'})));});
  if(fetchMode==='body-pending')return Promise.resolve({ok:true,json:()=>new Promise((resolve,reject)=>options.signal?.addEventListener('abort',()=>reject(Object.assign(new Error('aborted'),{name:'AbortError'}))))});
  return Promise.resolve({ok:true,json:async()=>url==='/api/config'?{screenshot_enabled:true,finshield_enabled:true,offline_fixture:true,max_image_mb:3}:{text:'Read screenshot text'}});
};
const readers=[];let readerMode='immediate';
class Reader{
  readAsDataURL(file){this.file=file;readers.push(this);if(readerMode==='immediate')this.succeed();}
  succeed(){this.result='data:image/png;base64,AA==';this.onload();}
}
const revoked=[];let nextUrl=0;
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
vm.runInNewContext(script,{document,fetch:fetcher,AbortController,FileReader:Reader,window:{addEventListener(){}},
  URL:{createObjectURL:()=> `blob:local-test-${++nextUrl}`,revokeObjectURL:url=>revoked.push(url)},
  getComputedStyle:()=>({getPropertyValue:()=> '0'}),
  setTimeout:(fn,ms)=>{const id=++nextTimer;timers.set(id,{fn,ms});return id;},clearTimeout:id=>timers.delete(id)});
const tick=()=>new Promise(setImmediate);
const pick=(name='test.png')=>el('shot').fire('change',{target:{value:'x',files:[{type:'image/png',name,size:100}]}});
const guard=setTimeout(()=>{console.error('Handler did not settle');process.exit(1);},2000);
(async()=>{await tick(); __CHECK__ })().catch(e=>{console.error(e);process.exitCode=1;}).finally(()=>clearTimeout(guard));
'''
    script = (harness.replace('__PATH__', json.dumps(str(path)))
              .replace('__MARKUP__', json.dumps(SellerMarkup(path.read_text(encoding='utf-8')).nodes))
              .replace('__CHECK__', check).replace('__MODE__', json.dumps(initial_mode)))
    result = subprocess.run([node, '-e', script], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr


def test_analyst_navigation_does_not_clear_seller_input():
    seller_check("""
      el('msg').value='Unsaved seller conversation';
      await el('finshield-entry').fire('click');
      assert.equal(el('msg').value,'Unsaved seller conversation');
    """)


@pytest.mark.parametrize('mode', ['pending', 'body-pending'])
def test_screenshot_wait_is_bounded_and_preview_retained(mode):
    seller_check(f"""
      el('msg').value='Keep this timeout draft';
      fetchMode={json.dumps(mode)};const pending=pick();await tick();
      const upload=requests.find(r=>r.url==='/api/extract-text');
      assert.ok(upload.options.signal,'upload must be cancellable');
      assert.equal(el('shot-preview').hidden,false);
      for(const {{fn}} of [...timers.values()]) fn();
      await pending;
      assert.equal(el('shot-status').hidden,true);
      assert.equal(el('shot-error').hidden,false);
      assert.match(el('shot-error').textContent,/too long|timed out/i);
      assert.ok(upload.options.signal.aborted,'timeout aborts the actual request');
      assert.equal(el('msg').value,'Keep this timeout draft');
      assert.equal(el('shot-preview').hidden,false);
      assert.equal(timers.size,0);
    """)


@pytest.mark.parametrize('mode', ['pending', 'body-pending'])
def test_timeout_after_switching_to_text_stays_visible_without_changing_tab_or_focus(mode):
    seller_check(f"""
      fetchMode={json.dumps(mode)};await el('tab-shot').fire('click');
      const pending=pick();await tick();
      const previewUrl=el('shot-img').src;
      await el('tab-text').fire('click');el('msg').focus();
      el('msg').value='Draft edited while reading';await el('msg').fire('input');
      const focusBefore=focusCalls;
      for(const {{fn}} of [...timers.values()]) fn();await pending;
      assert.equal(el('panel-shot').hidden,true);
      assert.equal(el('tab-text').getAttribute('aria-selected'),'true');
      assert.equal(document.activeElement,el('msg'));assert.equal(focusCalls,focusBefore);
      assert.equal(el('msg').value,'Draft edited while reading');
      assert.ok(visible(el('shot-preview')));assert.equal(el('shot-img').src,previewUrl);
      assert.ok(!visible(el('shot-status')));
      assert.ok(visible(el('shot-error')),'timeout recovery must remain visible on Paste text');
      assert.equal(el('shot-error').getAttribute('role'),'alert');
      assert.match(el('shot-error').textContent,/too long|timed out/i);
      assert.ok(requests.find(r=>r.url==='/api/extract-text').options.signal.aborted);
      assert.equal(timers.size,0);
    """)


def test_screenshot_progress_is_visible_after_switching_to_text():
    seller_check("""
      fetchMode='pending';const pending=pick();await tick();
      await el('tab-text').fire('click');el('msg').focus();
      assert.ok(visible(el('shot-status')),'reading status must remain visible on Paste text');
      assert.equal(el('shot-status').getAttribute('role'),'status');
      await el('shot-remove').fire('click');await pending;
      assert.ok(!visible(el('shot-status')));assert.equal(timers.size,0);
    """)


@pytest.mark.parametrize('action', ['remove', 'replace'])
def test_late_file_reader_cannot_upload_or_overwrite_after_remove_or_replace(action):
    seller_check(f"""
      readerMode='controlled';const oldPick=pick('old.png');await tick();
      const oldPreview=el('shot-img').src, oldReader=readers[0];
      el('msg').value='Preserve draft';
      if({json.dumps(action)}==='remove'){{await el('shot-remove').fire('click');}}
      else {{const newPick=pick('replacement.png');await tick();readers[1].succeed();await newPick;}}
      assert.equal(el('msg').value,{json.dumps('Preserve draft' if action == 'remove' else 'Read screenshot text')});
      const draft=el('msg').value, previewUrl=el('shot-img').src;
      const focusBefore=focusCalls, selected=el('tab-text').getAttribute('aria-selected');
      oldReader.succeed();await oldPick;
      assert.equal(el('msg').value,draft);
      assert.equal(el('shot-img').src,previewUrl);
      assert.equal(el('tab-text').getAttribute('aria-selected'),selected);
      assert.equal(focusCalls,focusBefore);
      assert.ok(revoked.includes(oldPreview),'old local object URL must be released');
      const uploads=requests.filter(r=>r.url==='/api/extract-text');
      assert.equal(uploads.length,{0 if action == 'remove' else 1},'obsolete file read must not upload');
      assert.equal(visible(el('shot-preview')),{str(action == 'replace').lower()});
      assert.ok(!visible(el('shot-error')));assert.ok(!visible(el('shot-status')));
      assert.equal(timers.size,0);
    """)


@pytest.mark.parametrize('mode', ['controlled-response', 'controlled-body'])
@pytest.mark.parametrize('action', ['remove', 'replace'])
def test_late_success_cannot_overwrite_after_remove_or_replace(mode, action):
    seller_check(f"""
      fetchMode={json.dumps(mode)};const oldPick=pick('old.png');await tick();
      const oldUpload=requests.find(r=>r.url==='/api/extract-text');
      const oldPreview=el('shot-img').src;
      el('msg').value='Preserve current draft';
      if({json.dumps(action)}==='remove'){{await el('shot-remove').fire('click');}}
      else {{
        const newPick=pick('replacement.png');await tick();
        const newUpload=requests.filter(r=>r.url==='/api/extract-text')[1];
        assert.equal(newUpload.options.signal.aborted,false);
        newUpload.succeed({{text:'Replacement screenshot text'}});await newPick;
      }}
      assert.equal(el('msg').value,{json.dumps('Preserve current draft' if action == 'remove' else 'Replacement screenshot text')});
      assert.equal(requests.filter(r=>r.url==='/api/extract-text').length,{1 if action == 'remove' else 2});
      assert.ok(oldUpload.options.signal.aborted,'remove/replace must abort obsolete request');
      assert.ok(revoked.includes(oldPreview));
      await el('tab-text').fire('click');el('msg').focus();
      const draft=el('msg').value, previewUrl=el('shot-img').src, focusBefore=focusCalls;
      oldUpload.succeed({{text:'STALE screenshot text'}});await oldPick;
      assert.equal(el('msg').value,draft);
      assert.equal(el('shot-img').src,previewUrl);
      assert.equal(el('tab-text').getAttribute('aria-selected'),'true');
      assert.equal(focusCalls,focusBefore);
      assert.equal(visible(el('shot-preview')),{str(action == 'replace').lower()});
      assert.ok(!visible(el('shot-error')));assert.ok(!visible(el('shot-status')));
      assert.equal(timers.size,0);
    """)


def test_removing_screenshot_cancels_inflight_upload_and_ignores_result():
    seller_check("""
      fetchMode='pending';const pending=pick();await tick();
      const upload=requests.find(r=>r.url==='/api/extract-text');
      el('msg').value='Keep this draft';await el('shot-remove').fire('click');
      assert.ok(upload.options.signal?.aborted,'remove cancels obsolete upload');
      await pending;assert.equal(el('msg').value,'Keep this draft');
      assert.equal(el('shot-preview').hidden,true);assert.equal(el('shot-error').hidden,true);
      assert.equal(timers.size,0);
    """)


def test_config_timeout_shows_fallback_without_losing_prefilled_message():
    seller_check("""
      assert.ok(requests[0].options.signal,'config request must be bounded');
      for(const {fn} of [...timers.values()]) fn();await tick();
      assert.equal(el('config-notice').hidden,false);
      assert.match(el('config-notice').textContent,/still check pasted text/);
      assert.match(el('msg').value,/Carousell/);
      assert.equal(timers.size,0);
    """, initial_mode='pending')


def test_invalid_file_does_not_upload_or_destroy_existing_preview():
    seller_check("""
      await pick();const uploads=requests.filter(r=>r.url==='/api/extract-text').length;
      const draft=el('msg').value, focusBefore=focusCalls;
      for(const file of [{type:'text/html',name:'x.html',size:100},{type:'image/png',name:'large.png',size:4*1024*1024}]){
        await el('shot').fire('change',{target:{value:'x',files:[file]}});
        assert.equal(el('shot-error').hidden,false);
        assert.ok(visible(el('shot-error')));
        assert.equal(el('tab-text').getAttribute('aria-selected'),'true');
        assert.equal(focusCalls,focusBefore);
        assert.equal(el('shot-preview').hidden,false);
        assert.equal(el('msg').value,draft);
      }
      assert.equal(requests.filter(r=>r.url==='/api/extract-text').length,uploads);
    """)
