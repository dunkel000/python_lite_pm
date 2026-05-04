import urllib.parse
import logging

import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import db
from routes import decisions, projects, users
from security import (
    CSRF_COOKIE_NAME,
    SESSION_KEY,
    SETTINGS,
    check_login_credentials,
    is_authenticated,
    is_html_request,
    issue_csrf_token,
    should_require_auth,
    validate_csrf,
)

app = FastAPI(title="Project Tracker — Activos Privados")
templates = Jinja2Templates(directory="templates")

logger = logging.getLogger("security")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(projects.router)
app.include_router(decisions.router)
app.include_router(users.router)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    path = request.url.path
    method = request.method.upper()

    if should_require_auth(path, method) and not is_authenticated(request):
        if is_html_request(request):
            next_param = urllib.parse.quote(str(request.url.path))
            return RedirectResponse(url=f"/login?next={next_param}", status_code=303)
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    is_htmx_write = (
        method in {"POST", "PUT", "PATCH", "DELETE"}
        and request.headers.get("hx-request") == "true"
    )
    if SETTINGS.auth_enabled and is_htmx_write:
        submitted_token = request.headers.get("x-csrf-token", "")
        if not validate_csrf(request, submitted_token):
            has_csrf_cookie = bool(request.cookies.get(CSRF_COOKIE_NAME))
            has_csrf_header = bool(submitted_token)
            logger.warning(
                "CSRF validation failed for %s %s (pm_csrf cookie present=%s, x-csrf-token header present=%s)",
                method,
                path,
                has_csrf_cookie,
                has_csrf_header,
            )
            return HTMLResponse("<div class='p-4 text-sm text-red-600'>CSRF inválido.</div>", status_code=403)

    response = await call_next(request)

    if request.session.get(SESSION_KEY) and not request.cookies.get(CSRF_COOKIE_NAME):
        token = issue_csrf_token(request)
        response.set_cookie(
            CSRF_COOKIE_NAME,
            token,
            httponly=False,
            secure=SETTINGS.secure_cookies,
            samesite="strict",
        )

    return response


app.add_middleware(
    SessionMiddleware,
    secret_key=SETTINGS.secret_key,
    same_site="strict",
    https_only=SETTINGS.secure_cookies,
    session_cookie="pm_session",
)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = "/"):
    if not SETTINGS.auth_enabled:
        return RedirectResponse(url=next or "/", status_code=303)
    if is_authenticated(request):
        return RedirectResponse(url=next or "/", status_code=303)
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "next": next or "/",
            "deployment_mode": SETTINGS.deployment_mode,
        },
    )


@app.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, username: str = Form(...), password: str = Form(...), next: str = Form("/")):
    if not SETTINGS.auth_enabled:
        return RedirectResponse(url=next or "/", status_code=303)
    if not check_login_credentials(username, password):
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "next": next or "/",
                "error": "Credenciales inválidas.",
                "deployment_mode": SETTINGS.deployment_mode,
            },
            status_code=401,
        )

    request.session[SESSION_KEY] = True
    token = issue_csrf_token(request)
    response = RedirectResponse(url=next or "/", status_code=303)
    response.set_cookie(
        CSRF_COOKIE_NAME,
        token,
        httponly=False,
        secure=SETTINGS.secure_cookies,
        samesite="strict",
    )
    return response


@app.post("/logout")
def logout(request: Request):
    if not SETTINGS.auth_enabled:
        return RedirectResponse(url="/", status_code=303)
    request.session.clear()
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(CSRF_COOKIE_NAME)
    return response


@app.on_event("startup")
def startup():
    db.init_db()
    if SETTINGS.deployment_mode not in {"intranet", "internet"}:
        print(f"[security] PT_DEPLOYMENT_MODE='{SETTINGS.deployment_mode}' no reconocido; usar 'intranet' o 'internet'.")

    if SETTINGS.auth_enabled:
        print("[security] Auth enabled for /projects*, /users*, /projects/{project_id}/decisions* and mutating /partials/* endpoints.")
    else:
        print("[security] Auth disabled (PT_AUTH_ENABLED=false); app is open without login.")
    print("[security] Login user:", SETTINGS.auth_user)
    print("[security] Login password:", SETTINGS.auth_password)
    if SETTINGS.auth_token:
        print("[security] PT_AUTH_TOKEN is enabled for API clients.")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
