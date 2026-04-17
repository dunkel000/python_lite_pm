import re
import sqlite3

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import db

router = APIRouter()
templates = Jinja2Templates(directory="templates")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _error_fragment(message: str) -> HTMLResponse:
    html = (
        '<div class="p-4 text-sm text-destructive bg-destructive/10 '
        'border border-destructive/30 rounded-md">'
        f"{message}"
        "</div>"
    )
    return HTMLResponse(html, status_code=400)


def _not_found_fragment(message: str) -> HTMLResponse:
    html = (
        '<div class="p-4 text-sm text-destructive bg-destructive/10 '
        'border border-destructive/30 rounded-md">'
        f"{message}"
        "</div>"
    )
    return HTMLResponse(html, status_code=404)


def _validate(name: str, email: str):
    name = (name or "").strip()
    email = (email or "").strip().lower()
    if not name:
        return None, None, "El nombre es obligatorio."
    if not EMAIL_RE.match(email):
        return None, None, "El email corporativo no es válido."
    return name, email, None


@router.get("/users", response_class=HTMLResponse)
def users_page(request: Request):
    users = db.list_users()
    return templates.TemplateResponse(
        request,
        "users.html",
        {"users": users, "active_page": "users"},
    )


@router.get("/partials/user-table", response_class=HTMLResponse)
def partial_user_table(request: Request):
    users = db.list_users()
    return templates.TemplateResponse(
        request,
        "partials/user_table.html",
        {"users": users},
    )


@router.get("/partials/user-form", response_class=HTMLResponse)
def partial_user_form(request: Request, id: int = 0):
    user = db.get_user(id) if id else None
    return templates.TemplateResponse(
        request,
        "partials/user_form.html",
        {"user": user},
    )


@router.post("/users", response_class=HTMLResponse)
def create_user(request: Request, name: str = Form(...), email: str = Form(...)):
    name, email, err = _validate(name, email)
    if err:
        return _error_fragment(err)
    try:
        db.create_user(name, email)
    except sqlite3.IntegrityError:
        return _error_fragment("Ya existe un usuario con ese email.")
    users = db.list_users()
    return templates.TemplateResponse(
        request,
        "partials/user_table.html",
        {"users": users},
    )


@router.put("/users/{user_id}", response_class=HTMLResponse)
def update_user(
    request: Request,
    user_id: int,
    name: str = Form(...),
    email: str = Form(...),
):
    name, email, err = _validate(name, email)
    if err:
        return _error_fragment(err)
    try:
        db.update_user(user_id, name, email)
    except sqlite3.IntegrityError:
        return _error_fragment("Ya existe un usuario con ese email.")
    except db.UserNotFoundError:
        return _not_found_fragment("Usuario no encontrado.")
    users = db.list_users()
    return templates.TemplateResponse(
        request,
        "partials/user_table.html",
        {"users": users},
    )


@router.delete("/users/{user_id}", response_class=HTMLResponse)
def delete_user(request: Request, user_id: int):
    try:
        db.delete_user(user_id)
    except db.UserNotFoundError:
        return _not_found_fragment("Usuario no encontrado.")
    users = db.list_users()
    return templates.TemplateResponse(
        request,
        "partials/user_table.html",
        {"users": users},
    )
