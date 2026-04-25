from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import db
from security import csrf_token

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _ctx(request: Request, **kwargs):
    return {"csrf_token": csrf_token(request), **kwargs}


@router.get("/decisiones", response_class=HTMLResponse)
def decisions_page(request: Request, project_id: str = ""):
    decisions = db.get_all_decisions(project_id or None)
    projects = db.get_all_projects()
    return templates.TemplateResponse(
        request,
        "decisions.html",
        _ctx(
            request,
            decisions=decisions,
            projects=projects,
            active_page="decisiones",
            filter_project=project_id,
        ),
    )


@router.get("/partials/decisions-list", response_class=HTMLResponse)
def partial_decisions_list(request: Request, project_id: str = ""):
    decisions = db.get_all_decisions(project_id or None)
    return templates.TemplateResponse(
        request,
        "partials/decisions_list.html",
        _ctx(request, decisions=decisions),
    )


@router.post("/projects/{project_id}/decisions", response_class=HTMLResponse)
def create_decision(
    request: Request,
    project_id: str,
    decision: str = Form(...),
    context: str = Form(""),
    decided_by: str = Form(""),
):
    db.create_decision(project_id, {
        "decision": decision.strip(),
        "context": context.strip(),
        "decided_by": decided_by.strip(),
    })
    decisions = db.get_decisions(project_id)
    return templates.TemplateResponse(
        request,
        "partials/decisions_inline.html",
        _ctx(request, decisions=decisions, project_id=project_id),
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
    db.update_decision(
        project_id,
        decision_id,
        {
            "decision": decision.strip(),
            "context": context.strip(),
            "decided_by": decided_by.strip(),
        },
    )
    decisions = db.get_decisions(project_id)
    return templates.TemplateResponse(
        request,
        "partials/decisions_inline.html",
        _ctx(request, decisions=decisions, project_id=project_id),
    )


@router.delete("/projects/{project_id}/decisions/{decision_id}", response_class=HTMLResponse)
def delete_decision(request: Request, project_id: str, decision_id: int):
    db.delete_decision(project_id, decision_id)
    decisions = db.get_decisions(project_id)
    return templates.TemplateResponse(
        request,
        "partials/decisions_inline.html",
        _ctx(request, decisions=decisions, project_id=project_id),
    )
