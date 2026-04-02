from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


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
    db.create_decision(project_id, {
        "decision": decision.strip(),
        "context": context.strip(),
        "decided_by": decided_by.strip(),
    })
    decisions = db.get_decisions(project_id)
    return templates.TemplateResponse(
        request,
        "partials/decisions_inline.html",
        {"decisions": decisions, "project_id": project_id},
    )
