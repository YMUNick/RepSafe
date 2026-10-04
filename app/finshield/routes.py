from dataclasses import replace
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.routing import APIRoute
from pydantic import Field, StrictBool

from .auth import SessionAuth, session_csrf
from .investigator import answer_offline_vip, answer_vip, make_model_step, make_offline_step, run_investigation
from .models import Model, ReviewCommand, RunResult, ServiceError
from .service import CaseService, template_case_id, validate_key
from .store import FirestoreStore


class SafeRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()
        async def safe(request):
            try:
                if request.method == 'POST' and len(await request.body()) > 65536:
                    raise ServiceError('request_too_large', 413)
                result = await handler(request)
            except ServiceError as exc:
                result = JSONResponse({'error': {'code': exc.code}}, status_code=exc.status_code)
            except RequestValidationError:
                result = JSONResponse({'error': {'code': 'invalid_request'}}, status_code=422)
            result.headers['Cache-Control'] = 'no-store'
            result.headers['X-Content-Type-Options'] = 'nosniff'
            result.headers['Referrer-Policy'] = 'no-referrer'
            return result
        return safe


class EmptyRequest(Model):
    pass


class SessionRequest(Model):
    resume_only: StrictBool = False


class CreateRequest(Model):
    template_id: Literal['risk-fee', 'normal-invoice']


class LoginRequest(Model):
    case_id: str = Field(min_length=1, max_length=64)
    reviewer_id: Literal['reviewer-a', 'reviewer-b']
    secret: str = Field(min_length=1, max_length=200)


def public_case(case, scope, mode, reviewer_available):
    public = case.model_dump(mode='json', include={'case_id', 'bundle', 'version', 'payment_status', 'investigation_status',
                                                  'rule_result', 'result', 'events', 'vip_used', 'vip_answer'})
    # Preserve exact actors privately for audit/replay; never expose session IDs.
    for event in public['events']:
        if event['actor_id'].startswith('visitor:'):
            event['actor_id'] = 'visitor'
    return {**public, 'permissions': {'can_review': scope.can_review,
                                    'reviewer_available': reviewer_available}, 'mode': mode}


def build_router(service, auth, model_step_factory, vip_answerer, config):
    router = APIRouter(prefix='/api/finshield', route_class=SafeRoute)
    if not config.enabled:
        return router

    def token(request):
        return request.cookies.get('fs_session', '')

    def guard(request: Request):
        config.validate()
        if request.method == 'POST':
            if request.headers.get('origin') != config.allowed_origin:
                raise ServiceError('origin_forbidden', 403)
            if request.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
                raise ServiceError('json_required', 415)
            if request.url.path != '/api/finshield/sessions':
                auth.check_csrf(token(request), request.headers.get('x-csrf-token', ''))

    def operation_key(request):
        key = request.headers.get('idempotency-key', '')
        validate_key(key)
        return key

    def current_scope(request, case_id):
        return auth.resolve(token(request), case_id)

    def reserve(scope):
        if config.model_mode == 'offline_fixture':
            return lambda: None
        if not config.live_calls_enabled:
            def disabled():
                raise ServiceError('live_calls_disabled', 409)
            return disabled
        return lambda: service.reserve_model_call(scope, config.budget_id, config.model_call_cap)

    @router.post('/sessions', dependencies=[Depends(guard)])
    def sessions(body: SessionRequest, request: Request, response: Response):
        cookie = token(request)
        try:
            session = auth.session(cookie)
        except ServiceError as exc:
            if exc.status_code != 401 or body.resume_only:
                raise
            cookie, csrf, session = auth.new_session()
            response.set_cookie('fs_session', cookie, httponly=True, secure=config.allowed_origin.startswith('https://'),
                                samesite='strict', path='/', max_age=24 * 60 * 60)
        else:
            csrf = session_csrf(cookie)
        cases = [{'case_id': case_id, 'template_id': template}
                 for template in ('risk-fee', 'normal-invoice')
                 if (case_id := template_case_id(session.session_id, template)) in session.case_ids]
        return {'csrf_token': csrf, 'cases': cases, 'reviewer_available': bool(auth.reviewer_hashes)}

    @router.post('/cases', dependencies=[Depends(guard)])
    def create(body: CreateRequest, request: Request):
        session = auth.session(token(request))
        case = service.create(session.session_id, body.template_id, operation_key(request))
        return public_case(case, current_scope(request, case.case_id), config.model_mode, bool(auth.reviewer_hashes))

    @router.get('/cases/{case_id}', dependencies=[Depends(guard)])
    def get_case(case_id: str, request: Request):
        scope = current_scope(request, case_id)
        return public_case(service.get(scope), scope, config.model_mode, bool(auth.reviewer_hashes))

    @router.post('/cases/{case_id}/payment', dependencies=[Depends(guard)])
    def payment(case_id: str, body: EmptyRequest, request: Request):
        scope = current_scope(request, case_id)
        return public_case(service.check(scope, operation_key(request)), scope, config.model_mode, bool(auth.reviewer_hashes))

    @router.post('/cases/{case_id}/investigation', dependencies=[Depends(guard)])
    def investigate(case_id: str, body: EmptyRequest, request: Request):
        scope = current_scope(request, case_id)
        lease = service.claim_run(scope, operation_key(request))
        if not lease.acquired:
            current = service.get(scope)
            if current.investigation_status == 'RUNNING':
                raise ServiceError('investigation_running', 409)
            return current.result.model_dump(mode='json')
        case = service.get(scope)
        if config.model_mode == 'gemini' and not config.live_calls_enabled:
            result = RunResult(status='INCOMPLETE', reason_codes=('live_calls_disabled',))
        else:
            result = run_investigation(scope, case.bundle, model_step_factory(case.bundle), reserve(scope))
        service.finish_run(scope, lease.run_id, result)
        return result.model_dump(mode='json')

    @router.post('/review-login', status_code=204, dependencies=[Depends(guard)])
    def review_login(body: LoginRequest, request: Request):
        auth.grant(token(request), body.case_id, body.reviewer_id, body.secret)
        return Response(status_code=204)

    @router.post('/cases/{case_id}/review', dependencies=[Depends(guard)])
    def review(case_id: str, body: ReviewCommand, request: Request):
        scope = current_scope(request, case_id)
        case = service.review(scope, body, operation_key(request))
        return public_case(case, current_scope(request, case_id), config.model_mode, bool(auth.reviewer_hashes))

    @router.post('/cases/{case_id}/vip', dependencies=[Depends(guard)])
    def vip(case_id: str, body: EmptyRequest, request: Request):
        scope = current_scope(request, case_id)
        if service.claim_vip(scope, operation_key(request)):
            case = service.get(scope)
            answer = 'Unavailable. Manual review is required.'
            if case.result and case.result.report and (config.model_mode == 'offline_fixture' or config.live_calls_enabled):
                evidence = tuple(e for step in case.result.trace if step.tool_result for e in step.tool_result.evidence)
                try:
                    answer = vip_answerer(scope, case.result.report, evidence, reserve(scope))
                except Exception:
                    pass  # Durable unavailable claim remains final; no automatic retry.
            service.save_vip(scope, answer)
        return {'answer': service.get(scope).vip_answer}

    @router.get('/cases/{case_id}/report', dependencies=[Depends(guard)])
    def report(case_id: str, request: Request):
        scope = current_scope(request, case_id)
        return public_case(service.get(scope), scope, config.model_mode, bool(auth.reviewer_hashes))

    return router


def install(app, settings, config):
    """Wire lazily: missing cloud configuration produces a request-time 503."""
    if not config.enabled:
        return
    def client_factory():
        project = config.firestore_project or settings.gcp_project
        if not project or project == 'your-gcp-project-id':
            raise ServiceError('storage_unavailable', 503)
        from google.cloud import firestore
        from app.cloud_identity import cloud_credentials
        return firestore.Client(project=project, database=config.firestore_database, credentials=cloud_credentials())
    store = FirestoreStore(collection=config.firestore_collection, client_factory=client_factory)
    service = CaseService(store)
    auth = SessionAuth(store, config.reviewer_hashes, session_cap=config.session_cap)
    if config.model_mode == 'offline_fixture':
        factory, vip = make_offline_step, answer_offline_vip
    else:
        factory = lambda bundle: make_model_step(replace(settings, agent_mode='gemini'), bundle)
        vip = lambda scope, report, evidence, before: answer_vip(scope, report, evidence, settings, before)
    app.include_router(build_router(service, auth, factory, vip, config))
    static = Path(__file__).resolve().parents[1] / 'static'
    def page():
        return FileResponse(static / 'finshield.html', media_type='text/html')
    def script():
        return FileResponse(static / 'finshield.js', media_type='application/javascript')
    def style():
        return FileResponse(static / 'finshield.css', media_type='text/css')
    app.add_api_route('/finshield', page, methods=['GET'], include_in_schema=False)
    app.add_api_route('/finshield.js', script, methods=['GET'], include_in_schema=False)
    app.add_api_route('/finshield.css', style, methods=['GET'], include_in_schema=False)
