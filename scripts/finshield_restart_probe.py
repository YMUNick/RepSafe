"""Two-process Firestore restart probe. Never substitutes a memory store."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.finshield_smoke import fingerprint, write_evidence


def validate_target(backend, allow_live, project, database, collection, emulator_host):
    if not all((project, database, collection)) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", collection):
        raise ValueError("explicit_target_required")
    if backend == "firestore":
        if not allow_live:
            raise ValueError("live_authorization_required")
        if emulator_host:
            raise ValueError("emulator_environment_conflicts_with_cloud")
    elif backend == "emulator":
        parsed = urlsplit("//" + emulator_host)
        if parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or not parsed.port:
            raise ValueError("loopback_emulator_required")
    else:
        raise ValueError("invalid_backend")


def validate_manifest(manifest, run_id, backend, project, database, collection, pid):
    if manifest.get("write_process_id") == pid or not manifest.get("write_process_id"):
        raise ValueError("separate_process_required")
    expected = dict(run_id=run_id, backend=backend, project=project, database=database, collection=collection)
    if any(manifest.get(k) != v for k, v in expected.items()):
        raise ValueError("target_mismatch")


def make_store(args):
    # Called only after target and consent checks. No IAM or database creation.
    from google.cloud import firestore
    from app.finshield.store import FirestoreStore
    kwargs = dict(project=args.project, database=args.database)
    if args.backend == "emulator":
        from google.auth.credentials import AnonymousCredentials
        kwargs["credentials"] = AnonymousCredentials()
    client = firestore.Client(**kwargs)
    return FirestoreStore(client, args.collection)


def write_phase(args, store):
    from app.finshield.auth import SessionAuth
    from app.finshield.models import ReviewCommand
    from app.finshield.service import CaseService
    now = lambda: datetime.now(timezone.utc)
    secret = secrets.token_urlsafe(32)
    auth = SessionAuth(store, {"reviewer-a": hashlib.sha256(secret.encode()).hexdigest()}, clock=now)
    service = CaseService(store, clock=now)
    record = {"stage": "AC-10", "status": "written", "backend": args.backend,
              "run_id": args.run_id, "project": args.project, "database": args.database,
              "collection": args.collection, "write_process_id": os.getpid(), "cases": {}}
    for variant in ("held", "approved", "interrupted"):
        token, _, session = auth.new_session()
        case = service.create(session.session_id, "risk-fee", args.run_id + "-create-" + variant)
        scope = auth.resolve(token, case.case_id)
        payment_key = args.run_id + "-payment-" + variant
        held = service.check(scope, payment_key)
        if held.payment_status != "HOLD_PENDING_REVIEW":
            raise ValueError("write_hold_failed")
        details = {"case_id": case.case_id, "payment_key": payment_key,
                   "payment_response_hash": fingerprint(held.model_dump(mode="json")),
                   "bundle_hash": fingerprint(held.bundle.model_dump(mode="json"))}
        if variant == "approved":
            auth.grant(token, case.case_id, "reviewer-a", secret)
            scope = auth.resolve(token, case.case_id)
            command = ReviewCommand(action="approve", reason="Manually checked synthetic restart probe records.",
                                    expected_version=held.version, evidence_refs=())
            key = args.run_id + "-review"
            case = service.review(scope, command, key)
            details.update(review_key=key, review_command=command.model_dump(mode="json"),
                           review_response_hash=fingerprint(case.model_dump(mode="json")))
        elif variant == "interrupted":
            lease = service.claim_run(scope, args.run_id + "-investigation")
            case = service.get(scope)
            details["lease_until"] = lease.lease_until.isoformat()
        else:
            case = held
        details.update(expected_payment_status=case.payment_status,
                       expected_audit_count=len(case.events),
                       audit_hash=fingerprint([e.model_dump(mode="json") for e in case.events]))
        record["cases"][variant] = details
    # Raw cookie, csrf, reviewer secret, token hashes and session IDs are excluded.
    return record


def read_phase(args, store, manifest):
    from app.finshield.models import CaseRecord, Scope, ReviewCommand
    from app.finshield.service import CaseService
    service = CaseService(store, clock=lambda: datetime.now(timezone.utc))
    checks = {}
    for variant, expected in manifest["cases"].items():
        raw = store.read("case-" + expected["case_id"])
        if raw is None:
            raise ValueError("persisted_case_missing")
        case = CaseRecord.model_validate(raw)
        payment_actor = next(e.actor_id for e in case.events if e.action == "payment_check")
        scope = Scope(case.session_id, case.case_id, payment_actor, False)
        current = service.get(scope)
        checks[variant + "_state"] = current.payment_status == expected["expected_payment_status"]
        checks[variant + "_bundle"] = fingerprint(current.bundle.model_dump(mode="json")) == expected["bundle_hash"]
        checks[variant + "_audit"] = (len(current.events) == expected["expected_audit_count"] and
            fingerprint([e.model_dump(mode="json") for e in current.events]) == expected["audit_hash"])
        replay = service.check(scope, expected["payment_key"])
        checks[variant + "_payment_replay"] = fingerprint(replay.model_dump(mode="json")) == expected["payment_response_hash"]
        if variant == "approved":
            review_scope = Scope(case.session_id, case.case_id, "reviewer-a", True)
            replay = service.review(review_scope, ReviewCommand.model_validate(expected["review_command"]), expected["review_key"])
            checks["review_replay"] = fingerprint(replay.model_dump(mode="json")) == expected["review_response_hash"]
            checks["review_replay_no_duplicate_audit"] = len(service.get(scope).events) == expected["expected_audit_count"]
        if variant == "interrupted":
            if datetime.fromisoformat(expected["lease_until"]) > datetime.now(timezone.utc):
                raise ValueError("lease_not_expired_rerun_read_later")
            recovered = service.recover_expired(scope)
            checks["interrupted_incomplete"] = recovered.investigation_status == "INCOMPLETE"
            checks["interrupted_keeps_hold"] = recovered.payment_status == "HOLD_PENDING_REVIEW"
    return {"stage": "AC-10", "status": "pass" if all(checks.values()) else "fail",
            "backend": args.backend, "run_id": args.run_id,
            "write_process_id": manifest["write_process_id"], "read_process_id": os.getpid(),
            "checks": checks, "case_ids": [c["case_id"] for c in manifest["cases"].values()],
            "cost_usd": None, "cost_status": "unverified"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("emulator", "firestore"), required=True)
    parser.add_argument("--phase", choices=("write", "read"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--project", default=os.environ.get("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--database", default=os.environ.get("FINSHIELD_FIRESTORE_DATABASE"))
    parser.add_argument("--collection", default=os.environ.get("FINSHIELD_FIRESTORE_COLLECTION"))
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        if not re.fullmatch(r"[A-Za-z0-9-]{1,32}", args.run_id):
            raise ValueError("invalid_run_id")
        validate_target(args.backend, args.allow_live, args.project, args.database, args.collection,
                        os.environ.get("FIRESTORE_EMULATOR_HOST", ""))
        path = args.manifest or Path(tempfile.gettempdir()) / ("finshield-restart-" + args.run_id + ".json")
        if args.phase == "write" and path.exists():
            raise ValueError("manifest_exists_use_new_run_id")
        manifest = None
        if args.phase == "read":
            manifest = json.loads(path.read_text(encoding="utf-8"))
            validate_manifest(manifest, args.run_id, args.backend, args.project, args.database,
                              args.collection, os.getpid())
        store = make_store(args)
        result = write_phase(args, store) if args.phase == "write" else read_phase(args, store, manifest)
        write_evidence(path if args.phase == "write" else args.out or path.with_suffix(".read.json"), result)
        print(json.dumps({"status": result["status"], "backend": args.backend, "run_id": args.run_id}))
        return 1 if result["status"] == "fail" else 0
    except Exception as exc:
        # Cloud/client exceptions may contain credential paths; never echo them.
        code = str(exc) if type(exc) is ValueError else "probe_unavailable"
        from app.finshield.models import ServiceError
        if isinstance(exc, ServiceError) and re.fullmatch(r"[a-z][a-z0-9_]{0,79}", exc.code):
            code = exc.code
        print(json.dumps({"status": "blocked", "phase": args.phase, "error": code}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
