"""个人手机网页入口与认证；不挂载旧版未鉴权业务接口。"""

from pathlib import Path
import sqlite3

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .auth import AuthError, AuthStore, COOKIE_NAME, SESSION_SECONDS
from .settings import MobileSettings
from .shipments import router as shipments_router
from .todos import router as todos_router
from .home import router as home_router

LANDING_PAGE = Path(__file__).resolve().parents[1] / "frontend" / "index.html"


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=48)
    password: str = Field(min_length=1, max_length=256, repr=False)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=256, repr=False)
    new_password: str = Field(min_length=12, max_length=256, repr=False)


def create_app(settings: MobileSettings) -> FastAPI:
    if settings.auth_database_path.resolve() in (settings.database_path.resolve(), settings.config_path.resolve()):
        raise ValueError("认证数据不能写入业务数据库或配置文件")
    app = FastAPI(title="Youzi Mobile", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    store = AuthStore(settings.auth_database_path)
    app.state.auth_store = store
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    @app.exception_handler(AuthError)
    async def auth_error(request: Request, exc: AuthError):
        headers = {"Retry-After": "900"} if exc.status == 429 else {}
        return JSONResponse({"detail": str(exc)}, status_code=exc.status, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request: Request, exc):
        # 不使用默认验证输出，避免将 password 等原始输入回显给客户端。
        return JSONResponse({"detail": "输入格式不正确，请检查填写内容或分页参数"}, status_code=422)

    @app.exception_handler(sqlite3.Error)
    async def database_error(request: Request, exc):
        return JSONResponse({"detail": "本地数据库暂不可用，请稍后重试"}, status_code=503, headers={"Cache-Control": "no-store"})

    @app.exception_handler(FileNotFoundError)
    async def database_missing(request: Request, exc):
        return JSONResponse({"detail": "本地数据文件暂不可用，请检查电脑端配置"}, status_code=503, headers={"Cache-Control": "no-store"})

    @app.middleware("http")
    async def protect(request: Request, call_next):
        if (settings.lan_ip or settings.tls_cert) and request.url.scheme != "https":
            return JSONResponse({"detail": "此入口仅允许 HTTPS"}, status_code=426)
        public = {"/api/mobile/health", "/api/mobile/auth/status", "/api/mobile/auth/setup", "/api/mobile/auth/login"}
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            expected = str(request.base_url).rstrip("/")
            if request.headers.get("x-youzi-mobile") != "1" or (origin is not None and origin != expected):
                return JSONResponse({"detail": "请求来源验证失败"}, status_code=403)
            try:
                if "content-length" not in request.headers:
                    return JSONResponse({"detail": "请求须包含内容长度"}, status_code=411)
                length = int(request.headers["content-length"])
            except ValueError:
                return JSONResponse({"detail": "无效请求长度"}, status_code=400)
            if length < 0 or length > 8192:
                return JSONResponse({"detail": "请求内容过大"}, status_code=413)
        if request.url.path.startswith("/api/mobile/") and request.url.path not in public:
            user = await run_in_threadpool(store.session_user, request.cookies.get(COOKIE_NAME))
            if not user:
                return JSONResponse({"detail": "请先登录"}, status_code=401)
            request.state.username = user
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        return response

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(LANDING_PAGE, media_type="text/html", headers={"Cache-Control": "no-store"})

    @app.get("/api/mobile/health")
    def health():
        return {"ok": True, "service": "youzi-mobile", "stage": "todos", "https": bool(settings.tls_cert)}

    @app.get("/assets/auth.js", include_in_schema=False)
    def javascript():
        return FileResponse(LANDING_PAGE.parent / "assets" / "auth.js", media_type="application/javascript")

    @app.get("/assets/mobile.css", include_in_schema=False)
    def stylesheet():
        return FileResponse(LANDING_PAGE.parent / "assets" / "mobile.css", media_type="text/css")

    @app.get("/assets/shipments.js", include_in_schema=False)
    def shipments_javascript():
        return FileResponse(LANDING_PAGE.parent / "assets" / "shipments.js", media_type="application/javascript")

    @app.get("/assets/todos.js", include_in_schema=False)
    def todos_javascript():
        return FileResponse(LANDING_PAGE.parent / "assets" / "todos.js", media_type="application/javascript")

    @app.get("/assets/home.js", include_in_schema=False)
    def home_javascript():
        return FileResponse(LANDING_PAGE.parent / "assets" / "home.js", media_type="application/javascript")

    @app.get("/api/mobile/auth/status")
    def status(request: Request):
        user = store.session_user(request.cookies.get(COOKIE_NAME))
        return {"initialized": store.initialized(), "authenticated": user is not None, "username": user}

    @app.post("/api/mobile/auth/setup", status_code=201)
    def setup(body: Credentials, request: Request):
        if not request.client or request.client.host not in {"127.0.0.1", "::1"}:
            raise AuthError(403, "首次初始化只能在本机完成")
        store.setup(body.username, body.password)
        return {"ok": True}

    @app.post("/api/mobile/auth/login")
    def login(body: Credentials, request: Request):
        username, token = store.login(body.username, body.password)
        response = JSONResponse({"ok": True, "username": username})
        response.set_cookie(COOKIE_NAME, token, max_age=SESSION_SECONDS, httponly=True, samesite="strict", secure=request.url.scheme == "https", path="/")
        return response

    @app.get("/api/mobile/me")
    def me(request: Request):
        return {"username": request.state.username}

    @app.post("/api/mobile/auth/logout")
    def logout(request: Request):
        store.logout(request.cookies[COOKIE_NAME])
        response = JSONResponse({"ok": True})
        response.delete_cookie(COOKIE_NAME, httponly=True, samesite="strict", secure=request.url.scheme == "https", path="/")
        return response

    @app.post("/api/mobile/auth/password")
    def change_password(body: PasswordChange, request: Request):
        store.change_password(request.cookies[COOKIE_NAME], body.current_password, body.new_password)
        response = JSONResponse({"ok": True})
        response.delete_cookie(COOKIE_NAME, path="/")
        return response

    app.include_router(shipments_router)
    app.include_router(todos_router)
    app.include_router(home_router)
    return app
