/* FIN-SHIELD: no dependencies, no remote assets; all case content is plain text. */
(function () {
  'use strict';
  const PAYMENT_LABELS = Object.freeze({
    PENDING_CHECK: 'Pending server check', HOLD_PENDING_REVIEW: 'Held for manual review',
    SIMULATED_PASSED: 'Simulated payment passed', CHECK_FAILED: 'Payment check failed',
    SIMULATED_CANCELLED: 'Simulated payment cancelled'
  });
  const INVESTIGATION_LABELS = Object.freeze({
    NOT_STARTED: 'Not started', RUNNING: 'Investigation running', READY: 'Report ready', INCOMPLETE: 'Investigation incomplete'
  });
  const TEMPLATES = Object.freeze({
    'risk-fee': {title: 'Verification fee', conversation: 'Pay a verification fee before receiving your sale proceeds.'},
    'normal-invoice': {title: 'Service invoice', conversation: 'Please pay invoice INV-N-1 for the service already delivered.'}
  });
  const CITATION_FIELDS = ['case_id', 'source_id', 'record_id', 'field', 'quote', 'dataset_version', 'policy_version', 'call_index'];
  const paymentLabel = (status) => Object.hasOwn(PAYMENT_LABELS, status) ? PAYMENT_LABELS[status] : 'Status unavailable';
  const modeLabel = (mode) => mode === 'offline_fixture'
    ? 'Offline fixture · Deterministic synthetic demonstration, not live Gemini or proof of agentic AI.'
    : mode === 'gemini' ? 'Gemini mode · Synthetic case data. A configured mode alone does not confirm a successful model call.'
      : 'Model mode unavailable. No live model execution has been verified.';
  function money(amount, currency) {
    if (!Number.isSafeInteger(amount) || amount < 0 || currency !== 'SGD') return 'Unavailable';
    const minor = BigInt(amount);
    return 'SGD ' + (minor / 100n).toLocaleString('en-SG') + '.' + String(minor % 100n).padStart(2, '0');
  }
  const safeCaseId = (value) => typeof value === 'string' && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(value);
  function fieldLabel(field) {
    const labels = {amount_minor: 'Amount', total_minor: 'Settled history total', history_total_minor: 'Settled history total',
      count: 'Eligible transactions', history_count: 'Eligible transactions',
      window_start: 'History window start', window_end: 'History window end (excluded)',
      conversation: 'Conversation', occurred_at: 'Transaction time', matched_rule_ids: 'Matched rules'};
    return Object.hasOwn(labels, field) ? labels[field] : field.replace(/_/g, ' ').replace(/^./, (letter) => letter.toUpperCase());
  }
  function fieldValue(field, value, currency) {
    return ['amount_minor', 'total_minor', 'history_total_minor'].includes(field) && Number.isSafeInteger(value) && currency === 'SGD'
      ? money(value, currency) : String(value);
  }
  class ApiError extends Error {
    constructor(code, status = 0) { super(code); this.code = code; this.status = status; }
  }
  class ApiClient {
    constructor(fetcher = (...args) => fetch(...args)) { this.fetcher = fetcher; this.csrf = ''; this.keys = new Map(); }
    async request(path, body, rememberKey = true) {
      const options = {method: body === undefined ? 'GET' : 'POST', credentials: 'same-origin', cache: 'no-store', headers: {Accept: 'application/json'}};
      if (body !== undefined) {
        options.headers['Content-Type'] = 'application/json';
        if (this.csrf) options.headers['X-CSRF-Token'] = this.csrf;
        options.body = JSON.stringify(body);
        if (rememberKey) {
          const identity = path + '\n' + options.body;
          if (!this.keys.has(identity)) this.keys.set(identity, crypto.randomUUID());
          options.headers['Idempotency-Key'] = this.keys.get(identity);
        }
      }
      const controller = new AbortController();
      options.signal = controller.signal;
      let timer;
      const deadline = new Promise((_, reject) => {
        timer = setTimeout(() => {
          reject(new ApiError('request_timeout'));
          controller.abort();
        }, path.endsWith('/investigation') ? 55000 : 45000);
      });
      const receive = async () => {
        let response;
        try { response = await this.fetcher('/api/finshield' + path, options); }
        catch (_) { throw new ApiError('network_unavailable'); }
        if (response.ok && response.status === 204) return null;
        let data;
        try { data = await response.json(); }
        catch (_) { throw new ApiError('invalid_response', response.status); }
        if (!response.ok) {
          const code = data?.error?.code;
          throw new ApiError(typeof code === 'string' && /^[a-z][a-z0-9_]{0,79}$/.test(code) ? code : 'request_failed', response.status);
        }
        return data;
      };
      // Bound the complete response, including a stalled body or fetch implementation.
      try { return await Promise.race([receive(), deadline]); }
      finally { clearTimeout(timer); }
    }
    post(path, body, rememberKey = true) { return this.request(path, body, rememberKey); }
    get(path) { return this.request(path); }
  }
  function resolveCitation(record, citation) {
    if (!record || !citation || citation.case_id !== record.case_id || !Number.isInteger(citation.call_index)) return null;
    const evidence = (record.result?.trace || []).flatMap((step) => step.tool_result?.evidence || [])
      .find((item) => CITATION_FIELDS.every((field) => item[field] !== undefined && item[field] === citation[field]));
    if (!evidence) return null;
    const source = (record.bundle?.sources || []).find((item) => item.source_id === evidence.source_id);
    if (source && (source.case_id !== record.case_id || source.record_id !== evidence.record_id ||
        source.dataset_version !== evidence.dataset_version || source.policy_version !== evidence.policy_version)) return null;
    if (source && Object.hasOwn(source.fields || {}, citation.field) && String(source.fields[citation.field]) !== citation.quote) return null;
    return evidence;
  }
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {ApiClient, ApiError, paymentLabel, money, modeLabel, resolveCitation};
    return;
  }

  const $ = (id) => document.getElementById(id);
  const client = new ApiClient();
  let templateId = 'risk-fee', record = null, busy = false, selectedCitation = null;
  let vipReply = '', reviewerAvailable = null, needsRefresh = false;
  const cases = new Map();
  function text(id, value) { $(id).textContent = value; }
  function element(tag, value, className) {
    const node = document.createElement(tag);
    if (value !== undefined) node.textContent = String(value);
    if (className) node.className = className;
    return node;
  }
  function path(action = '') { return '/cases/' + encodeURIComponent(record.case_id) + action; }
  function announce(value) { text('announcement', value); }
  function feedback(message) {
    text('feedback', message); $('feedback').hidden = !message;
    if (message) $('feedback').focus();
  }
  function controls() {
    document.querySelectorAll('button, input, textarea, select').forEach((node) => { node.disabled = busy; });
    document.querySelectorAll('[data-template]').forEach((node) => { node.disabled = busy || needsRefresh; });
    const hasCase = !!record;
    const knownSelectedCase = cases.has(templateId);
    $('open-case').hidden = hasCase || knownSelectedCase;
    $('open-case').disabled = busy || needsRefresh;
    $('check-payment').hidden = !hasCase;
    $('check-payment').disabled = busy || needsRefresh || record?.payment_status !== 'PENDING_CHECK';
    $('investigate').hidden = !hasCase;
    $('investigate').disabled = busy || needsRefresh || record?.investigation_status !== 'NOT_STARTED' ||
      !['HOLD_PENDING_REVIEW', 'SIMULATED_PASSED', 'SIMULATED_CANCELLED'].includes(record?.payment_status);
    $('refresh-case').hidden = !hasCase && !knownSelectedCase && !needsRefresh;
    $('download-report').disabled = busy || !hasCase;
    $('ask-vip').disabled = busy || needsRefresh || !hasCase || record?.investigation_status !== 'READY' || record?.vip_used === true || !!vipReply;
    const available = record?.permissions?.reviewer_available ?? reviewerAvailable;
    ['login-submit', 'reviewer-id', 'reviewer-secret'].forEach((id) => { $(id).disabled = busy || needsRefresh || !hasCase || available !== true; });
    const canReview = record?.permissions?.can_review === true;
    $('review-form').hidden = !canReview;
    $('review-login').hidden = canReview;
    $('review-submit').disabled = busy || needsRefresh || !canReview || record?.payment_status !== 'HOLD_PENDING_REVIEW';
    text('review-access', canReview ? 'Authorized for this case' : available === false ? 'Reviewer unavailable' : available === true ? 'Authorization required' : 'Access not checked');
    text('review-availability', canReview ? 'You are authorized for this case. Record a reason and explicitly confirm each decision for the displayed version.' : available === false
      ? 'Reviewer access is unavailable in this demo. Held simulated payments stay held; you can still inspect the evidence.'
      : available === true ? 'Choose reviewer A or B and enter the corresponding secret. Credentials are not saved by this page.'
        : 'Reviewer availability has not been checked. Open a case to check access.');
    const step = !hasCase || ['PENDING_CHECK', 'CHECK_FAILED'].includes(record.payment_status) ? 1
      : ['NOT_STARTED', 'RUNNING'].includes(record.investigation_status) ? 2 : 3;
    [1, 2, 3].forEach((number) => {
      const node = $('step-' + number);
      node.dataset.state = number < step ? 'complete' : number === step ? 'current' : 'upcoming';
      if (number === step) node.setAttribute('aria-current', 'step'); else node.removeAttribute('aria-current');
    });
    text('next-action', needsRefresh ? 'Outcome uncertain. Refresh the case before any further action.'
      : !hasCase ? knownSelectedCase ? 'Refresh the selected case to load its recorded state.' : 'Open this synthetic case to begin.'
        : record.payment_status === 'PENDING_CHECK' ? 'Check the simulated payment to start the evidence review.'
          : record.payment_status === 'CHECK_FAILED' ? 'The check failed. Refresh the case to confirm its recorded state.'
            : record.investigation_status === 'NOT_STARTED' ? 'Investigate the evidence. Payment status remains independently controlled.'
              : record.investigation_status === 'RUNNING' ? 'Refresh to retrieve the investigation outcome.'
                : 'Inspect the cited evidence, then use human review if access is available.');
    $('check-payment').classList.toggle('primary', step === 1);
    $('investigate').classList.toggle('primary', step === 2);
    $('workspace').setAttribute('aria-busy', String(busy));
    $('request-progress').hidden = !busy;
    document.querySelectorAll('[data-invalid-citation="true"]').forEach((node) => { node.disabled = true; });
  }
  function errorCopy(error) {
    const specific = {
      request_timeout: 'The request timed out; its outcome is uncertain. Refresh the case before any further mutation. The server may already have recorded the action.',
      session_capacity_reached: 'The lifetime demo session capacity has been reached and does not reset when sessions expire. Owner intervention is required to allow new sessions. Existing valid sessions can still resume.',
      review_login_locked: 'Reviewer access is locked for this session after failed attempts. Wait for the session to expire before trying again.',
      reviewer_unavailable: 'Reviewer access is unavailable for this reviewer. The payment stays in its last confirmed state. Refresh to check availability.',
      case_capacity_reached: 'This case has reached its capacity limit. Refresh to inspect the recorded state; additional nonterminal actions may be unavailable.',
      storage_unavailable: 'Case storage is unavailable. No state change is confirmed. Refresh when storage is restored.'
    };
    if (Object.hasOwn(specific, error.code)) return specific[error.code];
    if (error.status === 401) return 'Your session has expired. Reload this page to open a new synthetic case.';
    if (error.status === 403) return 'This request was not authorized. Check your reviewer access and refresh the case.';
    if (error.status === 404) return 'This case or module is unavailable. No successful payment check has been confirmed.';
    if (error.status === 409) return 'The case changed or an investigation is already running. Refresh the case, inspect its version, and confirm your decision again.';
    if (error.status === 422) return 'The request could not be validated. Check the form and try again.';
    if (error.status === 429) return 'The request limit has been reached. Wait before retrying.';
    if (error.status >= 500) return 'The case service is unavailable. No successful state change has been confirmed. Refresh the case when the service is restored.';
    if (error.code === 'network_unavailable') return 'Connection lost. The last displayed state may be out of date. Retry the same action or refresh to confirm the server state.';
    return 'The request could not be completed. Refresh the case to confirm its state.';
  }
  async function perform(work) {
    if (busy) return;
    busy = true; feedback(''); controls();
    try { await work(); }
    catch (error) {
      if (error.code === 'request_timeout') needsRefresh = true;
      feedback(errorCopy(error));
      if (record && [401, 403].includes(error.status)) {
        record.permissions = {...record.permissions, can_review: false};
        $('reviewer-secret').value = '';
      }
      if (record && error.status === 409) {
        try { accept(await client.get(path())); } catch (_) { /* Keep the last confirmed snapshot. */ }
      }
      $('review-confirm').checked = false;
      announce('Request incomplete. Check the error message and the last confirmed state.');
    } finally { busy = false; controls(); }
  }
  function accept(value) {
    if (!value || typeof value.case_id !== 'string' || !Number.isInteger(value.version) || !value.bundle ||
        (cases.has(templateId) && value.case_id !== cases.get(templateId)) ||
        (record && value.case_id !== record.case_id) || value.bundle.template_id !== templateId) throw new ApiError('invalid_response');
    // A replay can return a historical operation snapshot. Never regress a newer displayed version.
    if (record && value.version < record.version) return;
    record = value;
    cases.set(templateId, value.case_id);
    updateUrl(value.case_id);
    selectedCitation = null;
    $('review-confirm').checked = false;
    render();
  }
  function updateUrl(caseId) {
    const url = new URL(location.href);
    if (caseId) url.searchParams.set('case', caseId); else url.searchParams.delete('case');
    history.replaceState(null, '', url.pathname + url.search + url.hash);
  }
  async function session(resumeOnly) {
    let value;
    try { value = await client.post('/sessions', {resume_only: resumeOnly}, false); }
    catch (error) {
      if (resumeOnly && error.status === 401) {
        client.csrf = ''; cases.clear(); reviewerAvailable = null;
        return false;
      }
      throw error;
    }
    if (typeof value?.csrf_token !== 'string' || !value.csrf_token || !Array.isArray(value.cases) ||
        typeof value.reviewer_available !== 'boolean') throw new ApiError('invalid_response');
    client.csrf = value.csrf_token;
    reviewerAvailable = value.reviewer_available;
    cases.clear();
    value.cases.slice(0, 2).forEach((item) => {
      if (safeCaseId(item.case_id) && Object.hasOwn(TEMPLATES, item.template_id)) cases.set(item.template_id, item.case_id);
    });
    return true;
  }
  async function restore() {
    if (!await session(true)) { preview(templateId); return; }
    const selected = new URL(location.href).searchParams.get('case');
    const preferred = safeCaseId(selected) && [...cases].find(([, id]) => id === selected);
    const chosen = preferred?.[0] || (cases.has('risk-fee') ? 'risk-fee' : cases.keys().next().value) || 'risk-fee';
    preview(chosen);
    if (cases.has(chosen)) {
      updateUrl(cases.get(chosen));
      accept(await client.get('/cases/' + encodeURIComponent(cases.get(chosen))));
    }
  }
  function list(id, values, empty) {
    const node = $(id); node.replaceChildren();
    (values?.length ? values : [empty]).forEach((value) => node.append(element('li', value)));
  }
  function inspect(citation) {
    const evidence = resolveCitation(record, citation);
    if (!evidence) { feedback('This citation cannot be matched to evidence returned for the current case.'); return; }
    selectedCitation = Object.fromEntries(CITATION_FIELDS.map((field) => [field, citation[field]]));
    const node = $('source-inspector'); node.replaceChildren();
    node.append(element('p', 'CITED SOURCE · SYNTHETIC', 'eyebrow'));
    const source = (record.bundle.sources || []).find((item) => item.source_id === evidence.source_id);
    const exactValue = source?.fields?.[evidence.field] ?? evidence.fact_value;
    node.append(element('p', fieldLabel(evidence.field) + ': ' + fieldValue(evidence.field, exactValue ?? evidence.quote, source?.fields?.currency || record.bundle.current?.currency), 'evidence-value'));
    node.append(element('blockquote', evidence.quote));
    const details = element('dl');
    [['Source', evidence.source_id], ['Record / field', evidence.record_id + ' / ' + evidence.field],
      ['Dataset / policy', evidence.dataset_version + ' / ' + evidence.policy_version],
      ['Tool call', evidence.call_index]].forEach(([label, value]) => details.append(element('dt', label), element('dd', value)));
    if (evidence.derived_from?.length) details.append(element('dt', 'Derived from transactions'), element('dd', evidence.derived_from.join(', ')));
    node.append(details);
    text('review-evidence', 'This inspected citation will be attached to your review. Explain any additional manual checks in the reason.');
    node.scrollIntoView({block: 'center', behavior: 'auto'}); node.focus({preventScroll: true});
    announce('Source excerpt selected.');
  }
  function claims(id, values, empty) {
    const target = $(id); target.replaceChildren();
    if (!values?.length) { target.append(element('p', empty, 'empty')); return; }
    values.forEach((claim) => {
      const card = element('article', undefined, 'claim');
      const numericFields = {amount_minor: 'amount_minor', history_total_minor: 'total_minor', history_count: 'count'};
      const numericField = Object.hasOwn(numericFields, claim.fact_key) ? numericFields[claim.fact_key] : null;
      const verifiedNumber = numericField && Number.isSafeInteger(claim.fact_value) && claim.fact_value >= 0 &&
        (claim.citations || []).some((citation) => {
          const evidence = resolveCitation(record, citation);
          return evidence?.fact_key === claim.fact_key && evidence?.fact_value === claim.fact_value;
        });
      if (verifiedNumber) {
        card.append(element('p', fieldLabel(numericField) + ': ' + fieldValue(numericField, claim.fact_value, record.bundle.current?.currency)));
        const raw = element('details', undefined, 'raw-record');
        raw.append(element('summary', 'Exact reported claim & provenance'), element('p', claim.text), element('pre', JSON.stringify(claim, null, 2)));
        card.append(raw);
      } else card.append(element('p', claim.text));
      (claim.citations || []).forEach((citation, index) => {
        const valid = !!resolveCitation(record, citation);
        const button = element('button', valid ? 'Source ' + (index + 1) + ' · ' + fieldLabel(citation.field) : 'Citation unavailable', 'citation');
        button.type = 'button'; button.disabled = !valid; button.dataset.invalidCitation = String(!valid);
        button.setAttribute('aria-label', valid ? 'Inspect cited source: ' + fieldLabel(citation.field) + ', ' + citation.record_id : 'Citation unavailable');
        button.addEventListener('click', () => inspect(citation)); card.append(button);
      }); target.append(card);
    });
  }
  function renderSources() {
    const sources = (record.bundle.sources || []).filter((source) => source.case_id === record.case_id);
    text('source-count', sources.length + ' case records');
    $('source-list').replaceChildren();
    sources.forEach((source) => {
      const card = element('article', undefined, 'source-record');
      card.append(element('strong', source.record_id));
      Object.entries(source.fields || {}).forEach(([field, value]) => card.append(element('p', fieldLabel(field) + ': ' + fieldValue(field, value, source.fields.currency || record.bundle.current?.currency))));
      const raw = element('details', undefined, 'raw-record');
      raw.append(element('summary', 'Exact raw values & provenance'), element('pre', JSON.stringify(source, null, 2)));
      card.append(raw);
      card.append(element('p', 'Dataset ' + source.dataset_version + ' · Policy ' + source.policy_version, 'metadata'));
      $('source-list').append(card);
    });
    $('source-inspector').replaceChildren(element('p', 'Choose a report citation to inspect its exact source excerpt.', 'empty'));
    text('review-evidence', 'The currently inspected report citation will be attached, if available. Otherwise explain your manual checks.');
  }
  function render() {
    const bundle = record.bundle, rule = record.rule_result, result = record.result, report = result?.report;
    text('case-title', TEMPLATES[templateId].title);
    text('case-id', 'Case ' + record.case_id);
    text('case-version', 'Version ' + record.version);
    text('mode-note', modeLabel(record.mode));
    text('payment-status', paymentLabel(record.payment_status));
    text('payment-code', Object.hasOwn(PAYMENT_LABELS, record.payment_status) ? record.payment_status : 'Server status not recognized');
    $('payment-status').dataset.tone = record.payment_status === 'HOLD_PENDING_REVIEW' ? 'hold' : record.payment_status === 'CHECK_FAILED' ? 'error' : 'neutral';
    text('investigation-status', INVESTIGATION_LABELS[record.investigation_status] || 'Status unavailable');
    text('investigation-code', Object.hasOwn(INVESTIGATION_LABELS, record.investigation_status) ? record.investigation_status : 'Server status not recognized');
    text('payment-note', record.payment_status === 'HOLD_PENDING_REVIEW'
      ? 'This simulated payment stays held until an authorized reviewer explicitly approves or cancels it.'
      : record.payment_status === 'SIMULATED_PASSED'
        ? (record.events || []).some((event) => event.action === 'approve' && event.after === 'SIMULATED_PASSED')
          ? 'This simulated payment was approved by an authorized reviewer. The original rule findings remain in the decision trail. This is not a guarantee of safety.'
          : 'The simulated payment passed the demo policy. This is not a guarantee of safety.'
        : record.payment_status === 'CHECK_FAILED' ? 'The payment check failed. No simulated approval has been granted.'
          : 'Every simulated payment is checked by server rules. The investigation cannot change its payment status.');
    const conversationSource = (bundle.sources || []).find((source) => source.case_id === record.case_id && source.record_id === bundle.conversation_id)
      || (bundle.sources || []).find((source) => source.case_id === record.case_id && source.record_id === 'current' && typeof source.fields?.conversation === 'string');
    const conversation = conversationSource?.fields;
    text('conversation', conversation ? String(conversation.conversation ?? conversation.text ?? conversation.message ?? 'Conversation unavailable.') : 'Conversation source unavailable. Browse the case records for available context.');
    text('current-amount', money(bundle.current?.amount_minor, bundle.current?.currency));
    text('history-total', rule?.metrics ? money(rule.metrics.total_minor, bundle.current?.currency) : 'Not calculated');
    text('history-count', Number.isInteger(rule?.metrics?.count) ? rule.metrics.count : 'Not calculated');
    text('metric-window', rule?.metrics ? 'Settled history: ' + rule.metrics.window_start + ' to ' + rule.metrics.window_end + ' (end excluded). Current payment excluded.' : 'Historical totals exclude the current payment and future records.');
    text('rule-summary', rule ? 'Evaluated: ' + (rule.evaluated_rule_ids || []).join(', ') + ' · Matched: ' + ((rule.matched_rule_ids || []).join(', ') || 'none') + ' · Policy ' + rule.policy_id + ' v' + rule.policy_version : 'Rules have not run for this case.');
    text('report-state', INVESTIGATION_LABELS[record.investigation_status] || 'Unavailable');
    const incomplete = record.investigation_status === 'INCOMPLETE';
    $('report-details').open = record.investigation_status !== 'NOT_STARTED';
    $('source-details').open = sourcesAvailable();
    $('vip-panel').hidden = record.investigation_status !== 'READY';
    text('investigation-notice', incomplete ? 'Investigation incomplete. Manual review is required.'
      : record.investigation_status === 'RUNNING' ? 'Investigation is running. Refresh to retrieve its recorded outcome. Payment status is unchanged by investigation.'
        : record.investigation_status === 'READY' ? (record.mode === 'offline_fixture' ? 'Deterministic fixture report. This is an offline demonstration, not a verified live AI investigation.' : 'Review the cited evidence and counter-evidence before making a decision.')
          : 'Check the simulated payment, then investigate its evidence.');
    if (result?.reason_codes?.length) text('investigation-notice', $('investigation-notice').textContent + ' Reported reasons: ' + result.reason_codes.join(', ') + '.');
    claims('findings', report?.findings, 'No findings returned.');
    claims('counter-evidence', report?.counter_evidence, 'No counter-evidence returned. This does not establish wrongdoing.');
    claims('policy-basis', report?.policy_basis, 'No policy claims returned.');
    list('missing-information', report?.missing_information, report ? 'No missing items reported by this investigation.' : 'No completed evidence assessment is available.');
    list('next-steps', report?.suggested_next_steps, incomplete ? 'Request the missing records and use the separate review form.' : 'Review the case and its available evidence.');
    renderSources();
    text('vip-answer', record.vip_answer || vipReply || 'The answer cannot approve or release a payment. Use the separate review form for a decision.');
    $('audit-list').replaceChildren();
    (record.events || []).forEach((event) => {
      const item = element('li');
      item.append(element('strong', event.action + ' · ' + event.actor_id), element('p', event.reason),
        element('p', event.before + ' → ' + event.after + ' · ' + event.at, 'metadata'));
      $('audit-list').append(item);
    });
    if (!record.events?.length) $('audit-list').append(element('li', 'No recorded decisions for this case.', 'empty'));
    controls();
    announce(paymentLabel(record.payment_status) + '. ' + (INVESTIGATION_LABELS[record.investigation_status] || 'Investigation status unavailable') + '.');
  }
  function sourcesAvailable() { return !!record?.bundle?.sources?.length; }
  async function investigate() {
    text('investigation-status', 'Investigation running');
    text('investigation-notice', 'Reading case evidence. The server records the outcome of this request; payment status remains independently controlled.');
    try {
      // The endpoint returns RunResult. Fetch the public CaseRecord separately.
      await client.post(path('/investigation'), {});
      accept(await client.get(path()));
    } catch (error) {
      text('investigation-notice', 'Investigation incomplete. Manual review is required. Refresh the case to confirm the server outcome.');
      text('investigation-status', 'Outcome not confirmed');
      throw error;
    }
  }
  function preview(selectedTemplate) {
    templateId = selectedTemplate; record = null; selectedCitation = null; vipReply = '';
    updateUrl(cases.get(templateId) || null);
    $('report-details').open = false; $('source-details').open = false; $('vip-panel').hidden = true;
    $('reviewer-secret').value = ''; $('review-reason').value = ''; $('review-confirm').checked = false;
    $('review-action').value = 'keep_hold';
    text('confirm-copy', 'I confirm this review decision for the displayed case and version.');
    document.querySelectorAll('[data-template]').forEach((item) => { const chosen = item.dataset.template === templateId; item.classList.toggle('selected', chosen); item.setAttribute('aria-pressed', String(chosen)); });
    text('case-title', TEMPLATES[templateId].title); text('conversation', TEMPLATES[templateId].conversation);
    text('case-id', 'Synthetic template preview. Open the case to load server records.'); text('case-version', 'Template preview');
    text('payment-status', 'Not checked'); $('payment-status').dataset.tone = 'neutral'; text('payment-code', 'No payment has been submitted.');
    text('investigation-status', 'Not started'); text('investigation-code', 'Evidence appears after investigation.');
    text('mode-note', 'Model mode not checked. Open a case to check the service.');
    text('current-amount', 'SGD 500.00'); text('history-total', 'Not calculated'); text('history-count', 'Not calculated');
    text('metric-window', 'Historical totals exclude the current payment and future records.'); text('rule-summary', 'Rules have not run for this preview.');
    text('payment-note', 'Opening a case loads the selected template. Payment checks run on the server.');
    text('report-state', 'Awaiting case'); text('investigation-notice', 'Open this synthetic case and check the payment to begin.');
    ['findings', 'counter-evidence', 'policy-basis'].forEach((id) => $(id).replaceChildren(element('p', 'No report loaded for this template.', 'empty')));
    list('missing-information', [], 'Investigation has not started.'); list('next-steps', [], 'Open the synthetic case.');
    text('source-count', 'No sources'); $('source-inspector').replaceChildren(element('p', 'No cited source selected.', 'empty'));
    $('source-list').replaceChildren(element('p', 'Open this case to load records.', 'empty'));
    $('audit-list').replaceChildren(element('li', 'No recorded decisions loaded.', 'empty'));
    text('vip-answer', 'The answer cannot approve or release a payment. Use the separate review form for a decision.');
    feedback(''); controls();
  }
  document.querySelectorAll('[data-template]').forEach((button) => button.addEventListener('click', () => {
    if (busy || needsRefresh || button.dataset.template === templateId) return;
    return perform(async () => {
      preview(button.dataset.template);
      if (cases.has(templateId)) accept(await client.get('/cases/' + encodeURIComponent(cases.get(templateId))));
    });
  }));
  $('open-case').addEventListener('click', () => perform(async () => {
    if (needsRefresh) return;
    // Check the shared cookie again: another tab may have opened this template.
    await session(false);
    if (cases.has(templateId)) {
      accept(await client.get('/cases/' + encodeURIComponent(cases.get(templateId))));
      return;
    }
    accept(await client.post('/cases', {template_id: templateId}));
    // Creation replay is a historical response; refresh the latest state on each open.
    accept(await client.get(path()));
  }));
  $('check-payment').addEventListener('click', () => perform(async () => {
    if (needsRefresh || !record || record.payment_status !== 'PENDING_CHECK') return;
    accept(await client.post(path('/payment'), {}));
    if (record.payment_status !== 'CHECK_FAILED' && record.investigation_status === 'NOT_STARTED') await investigate();
  }));
  $('investigate').addEventListener('click', () => perform(async () => { if (!needsRefresh && record) await investigate(); }));
  $('refresh-case').addEventListener('click', () => perform(async () => {
    if (record) accept(await client.get(path()));
    else if (cases.has(templateId)) accept(await client.get('/cases/' + encodeURIComponent(cases.get(templateId))));
    else await restore();
    needsRefresh = false;
  }));
  $('ask-vip').addEventListener('click', () => perform(async () => {
    if (needsRefresh || !record) return;
    const result = await client.post(path('/vip'), {});
    vipReply = typeof result?.answer === 'string' ? result.answer : 'VIP answer unavailable. Use the separate review form.';
    text('vip-answer', vipReply);
    accept(await client.get(path()));
  }));
  $('review-login').addEventListener('submit', (event) => {
    event.preventDefault(); if (busy || needsRefresh || !record || record.permissions?.reviewer_available !== true) return;
    const login = {case_id: record.case_id, reviewer_id: $('reviewer-id').value.trim(), secret: $('reviewer-secret').value};
    $('reviewer-secret').value = '';
    perform(async () => { try { await client.post('/review-login', login, false); } finally { login.secret = ''; }
      accept(await client.get(path()));
      announce('Reviewer access checked for the current case.');
    });
  });
  $('review-action').addEventListener('change', () => {
    $('review-confirm').checked = false;
    const action = $('review-action').value;
    text('confirm-copy', action === 'approve' ? 'I explicitly approve this held simulated payment for the displayed case and version.'
      : action === 'cancel' ? 'I explicitly cancel this simulated payment for the displayed case and version.'
        : 'I confirm this decision. A held simulated payment will remain held.');
  });
  $('review-reason').addEventListener('input', () => { $('review-confirm').checked = false; });
  $('review-form').addEventListener('submit', (event) => {
    event.preventDefault();
    if (busy || needsRefresh || record?.permissions?.can_review !== true || record.payment_status !== 'HOLD_PENDING_REVIEW' || !$('review-confirm').checked) return;
    const reason = $('review-reason').value.trim();
    if (!reason) { feedback('Enter a non-empty reason describing your manual checks or missing evidence.'); $('review-reason').focus(); return; }
    const command = {action: $('review-action').value, reason, expected_version: record.version,
      evidence_refs: selectedCitation && resolveCitation(record, selectedCitation) ? [selectedCitation] : []};
    perform(async () => { accept(await client.post(path('/review'), command)); $('review-reason').value = ''; accept(await client.get(path())); });
  });
  $('download-report').addEventListener('click', () => perform(async () => {
    const report = await client.get(path('/report'));
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], {type: 'application/json'}));
    const anchor = element('a'); anchor.href = url;
    anchor.download = 'finshield-synthetic-report.json'; document.body.append(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    announce('Synthetic case report downloaded.');
  }));
  controls();
  perform(restore);
}());
