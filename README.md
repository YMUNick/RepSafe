# RepSafe × FIN-SHIELD

[English](README.md) | [繁體中文](README.zh-TW.md)

From a seller's suspicious conversation to a payment investigation, with traceable evidence and human review.

RepSafe retains the seller-facing entry point for pasted conversations, screenshot text extraction and reply drafts. FIN-SHIELD is its investigation module for e-commerce platforms with wallet or payment-collection capabilities. It brings together transactions, customer information, known relationships and demonstration policies. Risk analysts use it; risk and operations leads are prospective buyers; sellers are the people it aims to protect. Workflow demand, time savings and willingness to pay remain unverified.

## Current status

2026-10-04 usability update: sessions resume across reloads and tabs, requests have bounded waits and recovery guidance, and reviewer configuration failures are distinct from bad credentials. The analyst UI now brings the first action into the mobile viewport, uses a three-step workflow and readable SGD amounts with raw evidence retained. Screenshot upload keeps its local preview and draft on timeout; obsolete reads cannot overwrite a replacement. Bounded case storage reserves a final authorized decision after repeated hold actions. See [QA results and limits](docs/qa/bugs.md) and the [deployment record](docs/engineering/deploy.md) for publication evidence. This does **not** enable live AI or public reviewer access.

Initial deployment, 2026-10-02: the integrated synthetic workflow was deployed on Vercel (Python 3.12, Singapore `sin1`, existing Hobby plan). Open the [FIN-SHIELD analyst demo](https://repsafe-finshield.vercel.app/finshield) or [RepSafe seller assistant](https://repsafe-finshield.vercel.app/). The initial runtime was `2d9c92e` with 255 passing tests and 2 emulator-dependent skips. Hosted HTTP checks covered both cases, citations, isolation, CSRF and unauthorized review rejection. The deployment guide records newer revisions separately.

- Every case, KYC record, policy and payment is Synthetic / Simulated. There are no real transfers, bank-payment interception, account freezes or AML filings.
- Repository defaults keep FIN-SHIELD disabled. This public deployment explicitly enables the synthetic case workflow with real Firestore persistence and a model-call cap of 0. Private reviewer credentials are not yet provisioned; public visitors cannot approve or cancel payments.
- `offline_fixture` is a deterministic, evidence-linked workflow demonstration. It is not real Gemini, agentic AI or evidence of a G1 pass.
- Real Firestore passed a separate-process, 16-check durability probe. Real Gemini follow-up, human semantic evaluation, full security testing and G0–G3 acceptance are **not completed**; see the [QA plan](docs/qa/test-plan.md) and [roadmap](docs/roadmap.md). A deployed fixture is not a finished AI submission.
- The total project budget ceiling is USD 100. Actual spending, remaining funds and billing currency still need reconciliation; the ceiling is not the remaining balance. Time limits and scheduling are tracked in the [budget](docs/finance/budget.md) and roadmap.

## How it works

1. Conversation clues connect to a fixed synthetic case. Server-side, versioned rules check every simulated payment, whether or not someone viewed the warning.
2. A rule hit produces `HOLD_PENDING_REVIEW`; a complete check without a hit produces `SIMULATED_PASSED`; a failed payment check produces `CHECK_FAILED`.
3. An Investigator can read four authorized sources within the case: transactions, customer/KYC information, known relationships, and policy/history. It assembles findings, counter-evidence, missing information, policy basis and suggested next steps. Valid citations should open the source and the evidence returned by the tools.
4. An authorized reviewer makes an explicit decision with a reason; the case version and audit events preserve the action. AI, a VIP question, Dismiss alert and Escalate cannot release a hold.

Payment and investigation status are separate. Investigation can be `NOT_STARTED`, `RUNNING`, `READY` or `INCOMPLETE`; model or tool failures must show missing evidence and leave a held payment on hold. `SIMULATED_PASSED` means this simulated rule check passed, not that a payment is safe or lawful.

## Run locally

Use Python 3.11 from the repository root. These defaults run the existing RepSafe offline experience without a cloud account.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
# Copy only if no local .env exists; preserve existing local settings.
if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
$env:AGENT_MODE='offline_fixture'
$env:URL_REPUTATION_BACKEND='fixture'
$env:FINSHIELD_ENABLED='false'
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

On macOS/Linux use `.venv/bin/python` and `export` for environment variables. See [.env.example](.env.example) for configuration.

- [RepSafe homepage](http://127.0.0.1:8000/): conversation and screenshot entry, including upload and local preview; extracted text is confirmed before analysis. Screenshot extraction does not authenticate payment proof. The local default is 10 MB per image; Vercel uses a 3 MB raw-image limit. The UI should display the limit returned by `/api/config`.
- [Health](http://127.0.0.1:8000/health): the existing `status`, `mode` and `url_reputation` fields. This endpoint does not establish FIN-SHIELD model or storage readiness.
- [API documentation](http://127.0.0.1:8000/api/docs): FIN-SHIELD API paths start with `/api/finshield`.
- [FIN-SHIELD](http://127.0.0.1:8000/finshield): available after configuration and explicit enablement; a 404 is expected while the feature is disabled.

For the full synthetic case workflow, configure the origin, Firestore and reviewer authorization using the [deployment guide](docs/engineering/deploy.md). Online cases and review require Firestore even when the model uses offline fixtures. An explicitly injected local fake is for tests/development; missing credentials must produce an unavailable state, not a silent fallback to memory or SQLite on Vercel.

## Model and environment configuration

| Setting | Purpose and default |
|---|---|
| `FINSHIELD_ENABLED=false` | Keeps the module disabled until explicitly configured |
| `FINSHIELD_MODEL_MODE=offline_fixture` | Deterministic synthetic workflow; `gemini` selects the real-model mode |
| `FINSHIELD_LIVE_CALLS_ENABLED=false` | Disallows live model calls; selecting a mode alone does not enable paid calls |
| `FINSHIELD_MODEL_CALL_CAP=0` | Zero calls by default; set a finite allowance only for an authorized run |
| `FINSHIELD_BUDGET_ID` | Identifies an authorized run against durable call accounting, without automatic daily replenishment |
| `FINSHIELD_ALLOWED_ORIGIN` | Exact deployment HTTPS origin for cookie, CSRF and Origin enforcement |
| `AGENT_MODE` / `URL_REPUTATION_BACKEND` | Existing RepSafe conversation and URL-check settings; separate from FIN-SHIELD model mode |
| `MAX_IMAGE_MB` | Keep the local default of `10`; set `3` on Vercel because base64 JSON expands the upload within its 4.5 MB request-body limit. Upload and preview remain available; UI limits follow `/api/config` |
| `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION` / `GEMINI_MODEL` | Server-side real-model configuration; verify usable model and credentials in the deployment guide |

Reviewer secrets, Firestore configuration and cloud credentials stay server-side; use the integrated `.env.example` and deployment guide for their exact fields. Public visitors do not automatically become reviewers. Reviewer status still requires access to the specific case. Mutating API calls also enforce session, CSRF, Origin, case-version and idempotency requirements.

## Walk through two synthetic cases

Prerequisite: open `/finshield` and check its Synthetic / Simulated and model-mode labels. Without storage or authorization, show only a clearly labelled preview; do not present that preview as a persisted case or completed review. These are verification steps for a configured build, not claimed passing results.

1. High-risk case `risk-fee`: create a case, inspect the fake payment-verification conversation and payment sources, then submit the simulated payment. Check that rules produce `HOLD_PENDING_REVIEW`. Run the investigation and open the cited evidence, counter-evidence and gaps. Ask whether VIP status permits release; the hold must remain. Only an authorized reviewer can explicitly Approve held payment, Keep hold, Escalate or Cancel payment with a reason; inspect the audit event. Dismiss alert handles the warning without releasing payment.
2. Normal case `normal-invoice`: create a separate case, inspect the invoice and reasonable business explanation, then submit the simulated payment. A complete check without a rule hit should produce `SIMULATED_PASSED`. Inspect the investigation's counter-evidence; shared devices must not be treated as proof of collusion. Verify this case's own sources and states rather than carrying over the first case's citations or review actions.

Offline mode can rehearse this workflow. A real-AI demonstration requires an actual Gemini trace showing a follow-up chosen from the previous tool result; G1 also requires every other acceptance check. Thirty seconds is an editing/demo target, not a measured latency guarantee.

## Configure Vercel and verify deployment

Status: the public production demo is deployed. The [deployment guide](docs/engineering/deploy.md) records the exact revision, deployment IDs, checks and remaining limits. The following steps describe configuring another deployment, not unfinished authentication for the published site.

1. Authenticate Vercel and link the intended project (or import the GitHub repository). The current site was published by CLI; automatic Git deployments are not connected. Select the root containing `app/` and `requirements.txt`, using native FastAPI with Python 3.12 in `sin1`. Preserve `/` for the existing chat and `/finshield` for the new page.
2. Set server-side environment variables separately for Preview and Production. Start with `FINSHIELD_MODEL_MODE=offline_fixture`, `FINSHIELD_LIVE_CALLS_ENABLED=false` and `FINSHIELD_MODEL_CALL_CAP=0`; set `MAX_IMAGE_MB=3` on Vercel, retaining the local default of 10. The deployment owner confirms existing cloud resources and credentials; this does not require automatically upgrading to a paid plan.
3. Configure working Firestore access, the exact HTTPS origin and a reviewer secret before enabling full case operations. Do not substitute memory or SQLite on Vercel for durable online state, or put secrets in frontend files, GitHub or `.env.example`.
4. After deployment, verify `/`, `/health`, `/finshield` and its static assets, screenshot upload/preview and the `/api/config` size limit, then both cases, session isolation, unauthorized review rejection, CSRF/Origin rejection, retries and restart persistence. Missing credentials must show an explicit unavailable/unconfigured state.
5. Real Gemini testing separately requires valid credentials, an authorized call budget and recorded results. Add a public URL and completion claims only after the integration owner verifies the deployed revision and evidence.

## Verification and data

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts/run_eval.py --offline --edge
```

The first command runs local tests; the second checks the existing conversation workflow offline. Listing commands does not mean they ran or passed. Report the conversation baseline, new financial cases, Firestore durability and real-model results separately. Local fakes/fixtures do not prove cloud or agentic behavior. Consult the QA documents for actual results and gaps.

Public data uses synthetic cases and demonstration policies only; demonstration policies are not regulations. Interview transcripts, contacts, consent and workflow notes belong only in `data/private/`; existing consented and redacted seller cases belong in ignored `data/real_cases/`. Neither private directory may be deployed or published. See [outreach and data handling](docs/sales/seller-outreach.md).

## Documentation

| Document | Purpose |
|---|---|
| [PRD](docs/prd.md) · [Roadmap](docs/roadmap.md) | Personas, scope, state semantics and G0–G3 |
| [Architecture](docs/engineering/architecture.md) · [Deployment](docs/engineering/deploy.md) | APIs, storage, permissions, configuration and deployment evidence |
| [UI specification](docs/design/ui-spec.md) · [Storyboard](docs/design/storyboard.md) | English UI, evidence and simulation labels |
| [English pitch](docs/pitch/pitch-script.md) | Product narrative, demonstration script and FAQ |
| [Outreach templates](docs/sales/seller-outreach.md) · [Source register](docs/sales/data-sources.md) | Analyst/buyer/seller validation and claim boundaries |
| [Budget](docs/finance/budget.md) | USD 100 ceiling, costs and reconciliation gaps |
| [Test plan](docs/qa/test-plan.md) · [Bugs](docs/qa/bugs.md) | Coverage, actual results and open issues |
| [Integration meeting](docs/meetings/2026-10-02-FIN-SHIELD整合評估.md) · [Engineering plan](docs/superpowers/plans/2026-10-02-finshield-48h-core.md) | Design rationale and historical decisions; current execution follows updated specifications |

RepSafe and FIN-SHIELD are working names. Existing products also offer investigation summaries and agentic capabilities. Connecting conversation clues to case evidence is a differentiation hypothesis, not a claim of market novelty, measured impact or proven demand.
