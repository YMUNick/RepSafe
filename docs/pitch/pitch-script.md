# RepSafe × FIN-SHIELD — English pitch and demonstration script

Updated 2026-10-02 · Sandy · [English README](../../README.md) · [繁體中文 README](../../README.zh-TW.md)

This is a ready-to-rehearse script for the synthetic investigation prototype. Implementation and deployment are being integrated; live verification is pending. Use the offline version until real Gemini and the displayed workflow have evidence for the recorded revision. The video storyboard belongs to Dana: [storyboard](../design/storyboard.md). This document supplies the business narrative and presenter wording, not a claim that the video has been recorded.

## 1. Three sentences

> RepSafe connects a seller's suspicious conversation to FIN-SHIELD, an evidence copilot for risk analysts at e-commerce platforms with wallets or payment collection.
>
> In our synthetic workflow, code checks each simulated payment while the investigator organizes case evidence, counter-evidence and gaps for a human reviewer.
>
> Our question is whether that evidence trail can make verification and handoffs easier without losing the explanations that keep legitimate payments moving.

中文對照：RepSafe 將賣家可疑對話接到 FIN-SHIELD，協助具有錢包／代收付能力的平台風控分析師查證。合成流程由程式檢查每筆模擬付款，調查助手整理證據、反證與缺失，交由人工覆核。待驗證的價值是減少查證與交接負擔，同時保留正常交易的合理解釋。

## 2. Three-minute script

Timing is a rehearsal target. The spoken paragraphs below are the offline-ready script; show its mode label throughout. Only narrate actions that the configured build actually demonstrates. If storage is unavailable, state that this is a preview and do not narrate a persisted decision. Waiting time may be edited only with a visible disclosure and separately reported elapsed time.

### 0:00–0:25 — The analyst's question

A seller receives a message asking for a payment-verification fee. In our synthetic example, the analyst has a practical question: what evidence supports a hold, and what might explain the payment? The conversation, transaction history, customer profile and policy each provide part of the answer. We want to make those pieces easier to review together.

### 0:25–0:45 — The product

This is RepSafe with FIN-SHIELD. RepSafe keeps the seller's conversation entry point. FIN-SHIELD is an evidence copilot for platform risk analysts. Everything here is synthetic, every payment is simulated, and this run uses deterministic offline fixtures. It demonstrates the workflow; it does not demonstrate live AI.

### 0:45–1:20 — High-risk case

We open the verification-fee case and submit a simulated payment. Server rules check the payment before it can pass, even if nobody opened the warning. This case is held for review.

The investigation view separates supporting evidence, counter-evidence and missing information. We open a citation to inspect its source and version. The report is a draft for the reviewer. A relationship is a clue to examine, not proof that people committed a crime.

### 1:20–1:50 — Human control

Now we ask: does VIP status allow release? The question does not change the hold. Dismissing an alert or escalating a case does not release payment either.

Only an authorized reviewer with access to this case can make an explicit decision and give a reason. When we demonstrate that action, we inspect the resulting audit event. No money moves in this prototype.

### 1:50–2:20 — The normal case

Next, we open a separate invoice case with a reasonable business explanation. The completed rule check allows this simulated payment to pass. We inspect the evidence that supports that outcome, including the counter-evidence.

The point is not to hold every payment. If the model or a tool fails, the investigation must show that it is incomplete. Missing evidence must not become a fabricated finding.

### 2:20–3:00 — What still needs evidence

Our next validation asks analysts to compare the same cases with their current workflow: time to a supported decision, requests for more information and citation correctness. We also need to test whether risk and operations leads would sponsor a pilot.

Existing investigation products already offer AI assistance. Our hypothesis is the connection from seller conversation to reviewable case evidence. Time savings, pricing and customer demand remain unverified.

RepSafe with FIN-SHIELD: trace the evidence, preserve the uncertainty, keep the decision with the reviewer.

### Optional real-Gemini replacement

Use only after recording an actual successful run. Replace the final two sentences of the 0:25–0:45 paragraph with:

> Everything here is synthetic, and every payment is simulated. In this recorded run, Gemini reads a tool result, chooses a follow-up within this case, and receives additional evidence. Its tools are read-only; it cannot release a payment.

At 0:45–1:20 show the actual sequence, returned source IDs and follow-up result. Record model, revision, mode, elapsed time and call usage. A prewritten order, fixture output or four tools always run in sequence does not establish agentic behavior. A successful model call alone does not establish G1; all acceptance checks still apply.

## 3. Operator notes for the two cases

| Case/action | Expected display after configuration | Evidence to show |
|---|---|---|
| `risk-fee`: submit simulated payment | `HOLD_PENDING_REVIEW` | Versioned rule result and this payment's sources |
| Investigate | `READY` or truthful `INCOMPLETE`, independent of payment state | Source-linked findings, counter-evidence, gaps; real tool trace only when actually recorded |
| VIP question / Dismiss alert / Escalate | Held payment remains held | Policy basis and unchanged payment state |
| Authorized Approve held payment | `SIMULATED_PASSED` | Explicit reason, authorized actor and audit event |
| Authorized Keep hold / Cancel payment | Hold retained / `SIMULATED_CANCELLED` | Reason and audit event; cancellation does not delete the case |
| `normal-invoice`: submit simulated payment | `SIMULATED_PASSED` after a complete rule check without a hit | Reasonable business explanation and valid counter-evidence |
| Payment-rule/input failure | `CHECK_FAILED` | Missing input or failure; no simulated pass |
| Model/tool failure | `INCOMPLETE`; existing hold remains | Failure disclosure and handoff to an authorized person |

A public visitor may see a labelled preview. Public access does not grant reviewer rights. If a cloud credential, case store or permission is unavailable, demonstrate that limitation honestly rather than substituting a successful-looking static decision.

## 4. Reviewer and buyer FAQ

| Question | Evidence-bounded answer |
|---|---|
| Who uses it and who pays? | Risk analysts at platforms with wallet/payment-collection capabilities are the intended users. Risk or operations leads are prospective buyers. We have no validated willingness-to-pay result yet. Sellers remain beneficiaries and a separate research group. |
| Is it an AML system? | This prototype investigates synthetic e-commerce scam scenarios. It does not monitor real bank payments, freeze accounts, file AML reports or decide whether a crime occurred. |
| Why AI? | The intended real-model role is to interpret context, choose a limited follow-up and draft findings with sources. Code computes amounts and applies payment rules; an authorized person makes a review decision. Offline fixtures demonstrate only the workflow. |
| How is it different from InvestigateAI? | NICE Actimize already describes agentic investigation and analyst assistance. We are testing a narrower conversation-to-case workflow, not claiming that AI investigation or report generation is new. See source FS-S3 in the [source register](../sales/data-sources.md). |
| What happens when evidence is missing? | The investigation must disclose the gap or become incomplete. A held payment stays held. A complete normal rule check is not retroactively labelled criminal because the model failed. |
| Is it accurate or faster? | Financial-case quality, false holds, citation accuracy and elapsed time need their own measured results. The old conversation test set and offline fixtures cannot establish those results. We have no validated time-saving percentage to quote. |
| What is the price or ROI? | Both are unvalidated. We need observed case volumes, comparable analyst time, operating cost, integration effort and a buyer's pilot conditions. A proposed licence or usage model is a hypothesis, not an offer or sale. |
| Is the Vercel app live? | Live verification is pending. A public URL belongs in the README only after the integration owner has verified the deployed revision and its actual mode. A screenshot or old Cloud Run URL does not establish that. |
| Where is private data stored? | The public prototype uses synthetic data. Interviews and consent stay in private research storage; they are not uploaded into the demo. Online synthetic case and review records require Firestore, with secrets confined to the server. |

## 5. Claim ledger and rehearsal handoff

| Claim | Current status | Evidence needed before changing it |
|---|---|---|
| Analyst workflow pain / value of conversation-to-case evidence | Interview hypothesis | Workflow accounts from two analysts; record dissent and existing alternatives |
| Procurement and paid pilot | Unverified | One risk/operations buyer interview, budget ownership and explicit pilot conditions |
| Time savings / ROI / latency | Unmeasured | Comparable baseline, case set, method, actual outcomes and costs; include inconclusive cases |
| Real Gemini follow-up | Live verification pending | Actual prior-result-dependent follow-up trace and valid source citations |
| G1/G2/G3 completion | Not established by this script | Revision-specific acceptance and independent-case results, plus completed submission assets |
| Vercel availability / restart durability | Live verification pending | Deployed route checks and durable two-process/restart evidence |
| Seller quote or testimonial | None supplied | Verbatim original, approved translation and explicit publication permission |

Public context and competitor facts are sourced in the [register](../sales/data-sources.md), with the meeting's provenance. No public scam statistic is treated as platform demand, seller-specific losses or avoidable losses. No fabricated testimonials, calibrated-looking scores, automation percentage or guaranteed prevention claim belongs in the script.

Before recording: confirm mode and dataset labels, use both cases, check source targets and permissions, record the actual build, keep empty/failed states visible, and time the spoken script. Dana owns video edits; Quinn and the controller supply actual verification results. Interview drafts and seller consent materials remain in [outreach](../sales/seller-outreach.md); no outreach has been sent as part of this writing task.
