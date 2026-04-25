import sqlite3

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


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


@router.get("/decisiones", response_class=HTMLResponse)
def decisions_page(request: Request, project_id: str = ""):
    decisions = db.get_all_decisions(project_id or None)
    projects = db.get_all_projects()
    return templates.TemplateResponse(
        request,
        "decisions.html",
        {
            "decisions": decisions,
            "projects": projects,
            "active_page": "decisiones",
            "filter_project": project_id,
        },
    )


@router.get("/partials/decisions-list", response_class=HTMLResponse)
def partial_decisions_list(request: Request, project_id: str = ""):
    decisions = db.get_all_decisions(project_id or None)
    return templates.TemplateResponse(
        request,
        "partials/decisions_list.html",
        {"decisions": decisions},
    )


@router.post("/projects/{project_id}/decisions", response_class=HTMLResponse)
def create_decision(
    request: Request,
    project_id: str,
    decision: str = Form(...),
    context: str = Form(""),
    decided_by: str = Form(""),
):
    decision = decision.strip()
    if not decision:
        return _error_fragment("La decisión es obligatoria.")
    try:
        db.create_decision(project_id, {
            "decision": decision,
            "context": context.strip(),
            "decided_by": decided_by.strip(),
        })
    except sqlite3.IntegrityError:
        return _error_fragment("Proyecto inválido.")
    decisions = db.get_decisions(project_id)
    return templates.TemplateResponse(
        request,
        "partials/decisions_inline.html",
        {"decisions": decisions, "project_id": project_id},
    )


@router.put("/projects/{project_id}/decisions/{decision_id}", response_class=HTMLResponse)
def update_decision(
    request: Request,
    project_id: str,
    decision_id: int,
    decision: str = Form(...),
    context: str = Form(""),
    decided_by: str = Form(""),
):
    decision = decision.strip()
    if not decision:
        return _error_fragment("La decisión es obligatoria.")
    try:
        db.update_decision(
            project_id,
            decision_id,
            {
                "decision": decision,
                "context": context.strip(),
                "decided_by": decided_by.strip(),
            },
        )
    except db.DecisionNotFoundError:
        return _not_found_fragment("Decisión no encontrada")
    decisions = db.get_decisions(project_id)
    return templates.TemplateResponse(
        request,
        "partials/decisions_inline.html",
        {"decisions": decisions, "project_id": project_id},
    )


@router.delete("/projects/{project_id}/decisions/{decision_id}", response_class=HTMLResponse)
def delete_decision(request: Request, project_id: str, decision_id: int):
    try:
        db.delete_decision(project_id, decision_id)
    except db.DecisionNotFoundError:
        return _not_found_fragment("Decisión no encontrada")
    decisions = db.get_decisions(project_id)
    return templates.TemplateResponse(
        request,
        "partials/decisions_inline.html",
        {"decisions": decisions, "project_id": project_id},
    )
