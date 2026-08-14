from __future__ import annotations

import json
import ipaddress
import logging
import secrets
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import MutableHeaders
from starlette.middleware.trustedhost import TrustedHostMiddleware

from roi_web.errors import AppError
from roi_web.schemas import (
    DeleteRoiFileRequest,
    ExportRequest,
    ExcludeIntensityRequest,
    FillRequest,
    ImportMaskRequest,
    KeepComponentRequest,
    InteractiveTaskRequest,
    LabelColorRequest,
    LabelCreateRequest,
    LabelLockRequest,
    LoadCaseRequest,
    LoadEditableRoiRequest,
    RoiSelectionRequest,
    PolygonRequest,
    PromptRequest,
    ProposalMergeRequest,
    RootRequest,
    SaveRequest,
    StrokeRequest,
    TrimRoiRequest,
)
from roi_web.workbench.service import WorkbenchService


LOGGER = logging.getLogger("roi_web")
if not LOGGER.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    LOGGER.addHandler(handler)
LOGGER.setLevel(logging.INFO)


def create_app(project_root: Path | None = None) -> FastAPI:
    root = (project_root or Path(__file__).resolve().parents[1]).resolve()
    static_dir = Path(__file__).resolve().parent / "static"
    service = WorkbenchService(root)
    app = FastAPI(title="ROI Web Workbench", version="0.2.1", docs_url="/api/docs", redoc_url=None)
    app.state.service = service
    app.state.browser_launch_token = secrets.token_urlsafe(32)

    # This middleware remains strict in production.  The outer request-context
    # shim below maps Starlette TestClient's synthetic `testserver` host to the
    # loopback address only when the ASGI peer itself is the TestClient sentinel.
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "[::1]"],
    )

    def loopback_host_port(value: str, scheme: str) -> tuple[str, int] | None:
        try:
            parsed = urlsplit(f"//{value}")
            hostname = (parsed.hostname or "").lower()
            if hostname == "localhost":
                allowed = True
            else:
                allowed = ipaddress.ip_address(hostname).is_loopback
            if not allowed or parsed.username is not None or parsed.password is not None:
                return None
            port = parsed.port
        except (ValueError, TypeError):
            return None
        return hostname, int(port if port is not None else (443 if scheme == "https" else 80))

    def valid_loopback_origin(origin: str, request_scheme: str, request_port: int) -> bool:
        try:
            parsed = urlsplit(origin)
            if parsed.scheme not in {"http", "https"} or parsed.scheme != request_scheme:
                return False
            if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
                return False
            if parsed.username is not None or parsed.password is not None:
                return False
            hostname = (parsed.hostname or "").lower()
            if hostname != "localhost" and not ipaddress.ip_address(hostname).is_loopback:
                return False
            port = parsed.port
        except (ValueError, TypeError):
            return False
        effective_port = int(port if port is not None else (443 if parsed.scheme == "https" else 80))
        return effective_port == request_port

    def require_active_case(
        x_roi_case_id: str = Header(alias="X-ROI-Case-ID", min_length=1, max_length=1024),
        x_roi_session_id: str = Header(alias="X-ROI-Session-ID", min_length=16, max_length=128),
    ) -> tuple[str, str]:
        service.require_loaded(x_roi_case_id, x_roi_session_id)
        return x_roi_case_id, x_roi_session_id

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id
        start = time.perf_counter()
        raw_host = request.headers.get("host", "")
        peer_host = request.client.host if request.client is not None else ""
        if raw_host.lower() == "testserver" and peer_host == "testclient":
            MutableHeaders(scope=request.scope)["host"] = "127.0.0.1"
            raw_host = "127.0.0.1"
        request_endpoint = loopback_host_port(raw_host, request.url.scheme)
        if request_endpoint is None:
            return JSONResponse(
                status_code=400,
                content={"title": "HOST_REJECTED", "status": 400, "detail": "仅允许本机 loopback Host", "request_id": request_id},
                headers={"X-Request-ID": request_id},
            )
        _request_hostname, request_port = request_endpoint
        origin = request.headers.get("origin", "").rstrip("/")
        fetch_site = request.headers.get("sec-fetch-site", "").lower()
        browser_like = bool(
            origin
            or fetch_site
            or request.headers.get("sec-fetch-mode")
            or request.headers.get("user-agent", "").lower().startswith("mozilla/")
        )
        if origin and not valid_loopback_origin(origin, request.url.scheme, request_port):
            return JSONResponse(
                status_code=403,
                content={"title": "ORIGIN_REJECTED", "status": 403, "detail": "仅允许同端口 loopback Origin", "request_id": request_id},
                headers={"X-Request-ID": request_id},
            )
        if fetch_site == "cross-site":
            return JSONResponse(
                status_code=403,
                content={"title": "ORIGIN_REJECTED", "status": 403, "detail": "已阻止跨站请求", "request_id": request_id},
                headers={"X-Request-ID": request_id},
            )
        if request.url.path.startswith("/api/") and browser_like:
            launch_cookie = request.cookies.get("roi_web_launch", "")
            if not launch_cookie or not secrets.compare_digest(
                launch_cookie,
                app.state.browser_launch_token,
            ):
                return JSONResponse(
                    status_code=403,
                    content={"title": "BROWSER_TOKEN_REQUIRED", "status": 403, "detail": "浏览器启动令牌缺失或已失效，请从工作台首页重新进入", "request_id": request_id},
                    headers={"X-Request-ID": request_id},
                )
            if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not origin:
                return JSONResponse(
                    status_code=403,
                    content={"title": "ORIGIN_REQUIRED", "status": 403, "detail": "浏览器写请求必须携带同源 Origin", "request_id": request_id},
                    headers={"X-Request-ID": request_id},
                )
        try:
            response = await call_next(request)
        except Exception:
            LOGGER.exception(json.dumps({"level": "error", "event": "request_failed", "request_id": request_id}))
            raise
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' blob:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
        )
        response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "no-cache"
        LOGGER.info(json.dumps({
            "level": "info", "event": "request", "request_id": request_id,
            "method": request.method, "route": request.url.path,
            "status": response.status_code, "duration_ms": round((time.perf_counter() - start) * 1000, 2),
        }, ensure_ascii=False))
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        content = {
            "title": exc.code,
            "status": exc.status_code,
            "detail": exc.message,
            "request_id": getattr(request.state, "request_id", ""),
        }
        if exc.details:
            content["meta"] = exc.details
        return JSONResponse(
            status_code=exc.status_code,
            content=content,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        messages = [f"{'.'.join(str(value) for value in item['loc'])}: {item['msg']}" for item in exc.errors()]
        return JSONResponse(
            status_code=422,
            content={"title": "VALIDATION_ERROR", "status": 422, "detail": "；".join(messages), "request_id": getattr(request.state, "request_id", "")},
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"title": "INTERNAL_ERROR", "status": 500, "detail": "服务器处理失败，请查看启动窗口日志", "request_id": getattr(request.state, "request_id", "")},
        )

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "roi-web", "version": "0.2.1"}

    @app.get("/ready")
    def ready():
        return {"status": "ready", "models": len(service.models)}

    @app.post("/api/root")
    def set_root(payload: RootRequest):
        return service.set_root(Path(payload.path), payload.discard_dirty)

    @app.get("/api/root")
    def get_root():
        return service.root_info()

    @app.get("/api/cases")
    def cases():
        return {"items": service.list_cases()}

    @app.post("/api/cases/load")
    def load_case(payload: LoadCaseRequest):
        return service.load_case(
            payload.case_id,
            payload.discard_dirty,
            payload.roi_relative_path,
            payload.expected_roi_sha256,
        )

    @app.post("/api/roi/import")
    def import_mask(payload: ImportMaskRequest, _binding: tuple[str, str] = Depends(require_active_case)):
        return service.import_mask(payload.relative_path, *_binding)

    @app.post("/api/roi/load-interactive-reference")
    def load_interactive_reference(payload: ImportMaskRequest, _binding: tuple[str, str] = Depends(require_active_case)):
        return service.load_interactive_reference(payload.relative_path, *_binding)

    @app.post("/api/roi/load-editable")
    def load_editable_roi(payload: LoadEditableRoiRequest, _binding: tuple[str, str] = Depends(require_active_case)):
        return service.load_editable_roi(payload.relative_path, payload.discard_dirty, *_binding)

    @app.post("/api/roi/selection")
    def select_roi_files(payload: RoiSelectionRequest, _binding: tuple[str, str] = Depends(require_active_case)):
        return service.select_roi_files(payload.relative_paths, payload.discard_dirty, *_binding, payload.request_id)

    @app.post("/api/roi/delete")
    def delete_roi_file(payload: DeleteRoiFileRequest, _binding: tuple[str, str] = Depends(require_active_case)):
        return service.delete_patient_roi(payload.relative_path, payload.confirm, *_binding, payload.request_id)

    @app.get("/api/session")
    def session(_binding: tuple[str, str] = Depends(require_active_case)):
        return service.session_info(*_binding)

    @app.get("/api/slice")
    def slice_image(
        orientation: str = Query(pattern="^(axial|coronal|sagittal)$"),
        index: int = Query(ge=0),
        level: float = 40.0,
        width: float = Query(default=400.0, gt=0.0),
        opacity: float = Query(default=0.49, ge=0.0, le=1.0),
        mode: str = Query(default="fill", pattern="^(fill|boundary)$"),
        boundary_width: int = Query(default=1, ge=1, le=10),
        baseline: bool = True,
        proposal: bool = True,
        hidden_labels: str = Query(default="", max_length=4096),
        hidden_layers: str = Query(default="", max_length=32768),
        layer_opacities: str = Query(default="", max_length=32768),
        _binding: tuple[str, str] = Depends(require_active_case),
    ):
        return Response(
            service.slice_png(
                orientation, index, level, width, opacity, mode, boundary_width,
                baseline, proposal, *_binding, hidden_labels, hidden_layers, layer_opacities,
            ),
            media_type="image/png",
            headers={"Cache-Control": "no-store"},
        )

    @app.post("/api/edit/stroke")
    def stroke(payload: StrokeRequest, _binding: tuple[str, str] = Depends(require_active_case)):
        return service.stroke(payload.orientation, payload.index, payload.label_id, payload.tool, payload.radius, [(point.x, point.y) for point in payload.points], *_binding, payload.layer_key)

    @app.post("/api/edit/polygon")
    def polygon(payload: PolygonRequest, _binding: tuple[str, str] = Depends(require_active_case)):
        return service.polygon(payload.orientation, payload.index, payload.label_id, [(point.x, point.y) for point in payload.points], *_binding, payload.layer_key)

    @app.post("/api/edit/fill")
    def fill(payload: FillRequest, _binding: tuple[str, str] = Depends(require_active_case)):
        return service.fill(payload.orientation, payload.index, payload.label_id, (payload.point.x, payload.point.y), *_binding, payload.layer_key)

    @app.post("/api/edit/trim")
    def trim_roi(payload: TrimRoiRequest, _binding: tuple[str, str] = Depends(require_active_case)):
        return service.trim_roi(payload.orientation, payload.index, payload.label_id, payload.direction, *_binding, payload.layer_key)

    @app.post("/api/edit/keep-component")
    def keep_component(payload: KeepComponentRequest, _binding: tuple[str, str] = Depends(require_active_case)):
        return service.keep_component(payload.orientation, payload.index, payload.label_id, (payload.point.x, payload.point.y), *_binding, payload.layer_key)

    @app.post("/api/edit/exclude-intensity")
    def exclude_intensity(payload: ExcludeIntensityRequest, _binding: tuple[str, str] = Depends(require_active_case)):
        return service.exclude_intensity(
            payload.orientation, payload.index, payload.label_id, payload.scope,
            payload.minimum, payload.maximum, *_binding, payload.layer_key,
        )

    @app.post("/api/edit/undo")
    def undo(_binding: tuple[str, str] = Depends(require_active_case)):
        return service.undo(*_binding)

    @app.post("/api/edit/redo")
    def redo(_binding: tuple[str, str] = Depends(require_active_case)):
        return service.redo(*_binding)

    @app.post("/api/labels")
    def create_label(payload: LabelCreateRequest, _binding: tuple[str, str] = Depends(require_active_case)):
        return service.create_label(payload.name, payload.display_name, payload.color, payload.hotkey, payload.priority, *_binding)

    @app.post("/api/labels/lock")
    def lock_label(payload: LabelLockRequest, _binding: tuple[str, str] = Depends(require_active_case)):
        return service.lock_label(payload.label_id, payload.locked, *_binding, payload.layer_key)

    @app.post("/api/labels/color")
    def set_label_color(payload: LabelColorRequest, _binding: tuple[str, str] = Depends(require_active_case)):
        return service.set_label_color(payload.label_id, payload.color, *_binding, payload.layer_key)

    @app.post("/api/prompts")
    def add_prompt(payload: PromptRequest, _binding: tuple[str, str] = Depends(require_active_case)):
        return service.add_prompt(
            payload.orientation, payload.index, payload.kind,
            [(point.x, point.y) for point in payload.points], payload.radius, *_binding,
        )

    @app.post("/api/prompts/undo")
    def undo_prompt(_binding: tuple[str, str] = Depends(require_active_case)):
        return service.undo_prompt(*_binding)

    @app.post("/api/prompts/reset")
    def reset_prompts(_binding: tuple[str, str] = Depends(require_active_case)):
        return service.reset_prompts(*_binding)

    @app.post("/api/tasks/interactive")
    def start_interactive(payload: InteractiveTaskRequest, _binding: tuple[str, str] = Depends(require_active_case)):
        return service.start_interactive(payload.label_id, *_binding, payload.layer_key)

    @app.get("/api/tasks/{task_id}")
    def task(task_id: str, _binding: tuple[str, str] = Depends(require_active_case)):
        return service.task(task_id, *_binding)

    @app.post("/api/tasks/{task_id}/cancel")
    def cancel_task(task_id: str, _binding: tuple[str, str] = Depends(require_active_case)):
        return service.cancel_task(task_id, *_binding)

    @app.post("/api/proposals/merge")
    def merge_proposal(payload: ProposalMergeRequest, _binding: tuple[str, str] = Depends(require_active_case)):
        return service.merge_proposal(payload.label_id, payload.operation, *_binding, payload.layer_key)

    @app.get("/api/roi-slices")
    def roi_slices(
        orientation: str = Query(pattern="^(axial|coronal|sagittal)$"),
        label_id: int = Query(ge=1, le=65535),
        layer_key: str = Query(default="", max_length=8192),
        _binding: tuple[str, str] = Depends(require_active_case),
    ):
        return {"indices": service.roi_slices(orientation, label_id, *_binding, layer_key)}

    @app.get("/api/roi-mesh")
    def roi_mesh(
        label_id: int = Query(ge=1, le=65535),
        layer_key: str = Query(default="", max_length=8192),
        _binding: tuple[str, str] = Depends(require_active_case),
    ):
        return service.roi_mesh(label_id, *_binding, layer_key)

    @app.post("/api/save")
    def save(payload: SaveRequest, _binding: tuple[str, str] = Depends(require_active_case)):
        return service.save(payload.reviewed, *_binding)

    @app.post("/api/export")
    def export(payload: ExportRequest, _binding: tuple[str, str] = Depends(require_active_case)):
        return service.export_single_nifti(payload.roi_name, payload.reviewed, *_binding)

    @app.get("/")
    def index():
        response = FileResponse(static_dir / "index.html", headers={"Cache-Control": "no-store"})
        response.set_cookie(
            "roi_web_launch",
            app.state.browser_launch_token,
            httponly=True,
            samesite="strict",
            secure=False,
            path="/",
        )
        return response

    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    return app


app = create_app()
