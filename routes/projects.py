from datetime import date, timedelta
import json

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

import db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _current_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _compute_gantt_weeks(n: int = 16):
    monday = _current_monday()
    weeks = []
    for i in range(n):
        ws = monday + timedelta(weeks=i)
        we = ws + timedelta(days=6)
        weeks.append((ws, we))
    return weeks


def _gantt_project_data(projects, weeks):
    result = []
    for p in projects:
        try:
            start = date.fromisoformat(p["start_date"]) if p.get("start_date") else None
            end = date.fromisoformat(p["end_date"]) if p.get("end_date") else None
        except ValueError:
            start = end = None

        col_start = None
        col_span = 0

        if start and end:
            for i, (ws, we) in enumerate(weeks):
                if start <= we and end >= ws:
                    if col_start is None:
                        col_start = i + 2  # +2: 1-indexed, first col is name
                    col_span += 1

        result.append({**p, "col_start": col_start, "col_span": col_span})
    return result


# ── Pages ─────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    projects = db.get_all_projects()
    stats = db.get_stats()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"projects": projects, "stats": stats, "active_page": "dashboard"},
    )


@router.get("/gantt", response_class=HTMLResponse)
def gantt_page(request: Request, status: str = "", priority: str = ""):
    projects = db.get_all_projects(status or None, priority or None)
    weeks = _compute_gantt_weeks()
    gantt_data = _gantt_project_data(projects, weeks)
    return templates.TemplateResponse(
        request,
        "gantt.html",
        {
            "gantt_data": gantt_data,
            "weeks": weeks,
            "active_page": "gantt",
            "filter_status": status,
            "filter_priority": priority,
        },
    )


# ── Partials ──────────────────────────────────────────────────────────────────

@router.get("/partials/project-table", response_class=HTMLResponse)
def partial_project_table(request: Request, status: str = "", priority: str = ""):
    projects = db.get_all_projects(status or None, priority or None)
    return templates.TemplateResponse(
        request,
        "partials/project_table.html",
        {"projects": projects},
    )


@router.get("/partials/stats", response_class=HTMLResponse)
def partial_stats(request: Request):
    stats = db.get_stats()
    return templates.TemplateResponse(
        request,
        "partials/stats_cards.html",
        {"stats": stats},
    )


@router.get("/partials/project-form", response_class=HTMLResponse)
def partial_project_form(request: Request, id: str = ""):
    project = db.get_project(id) if id else None
    next_id = db.next_project_id()
    return templates.TemplateResponse(
        request,
        "partials/project_form.html",
        {"project": project, "next_id": next_id},
    )


@router.get("/partials/gantt-chart", response_class=HTMLResponse)
def partial_gantt_chart(request: Request, status: str = "", priority: str = ""):
    projects = db.get_all_projects(status or None, priority or None)
    weeks = _compute_gantt_weeks()
    gantt_data = _gantt_project_data(projects, weeks)
    return templates.TemplateResponse(
        request,
        "partials/gantt_chart.html",
        {"gantt_data": gantt_data, "weeks": weeks},
    )


# ── Project detail ────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail(request: Request, project_id: str):
    project = db.get_project(project_id)
    if not project:
        return HTMLResponse("<p class='p-6 text-red-500'>Proyecto no encontrado.</p>", status_code=404)
    decisions = db.get_decisions(project_id)
    status_log = db.get_status_log(project_id)
    return templates.TemplateResponse(
        request,
        "partials/project_detail.html",
        {"project": project, "decisions": decisions, "status_log": status_log},
    )


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.post("/projects", response_class=HTMLResponse)
def create_project(
    request: Request,
    id: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    priority: str = Form("Media"),
    status: str = Form("Backlog"),
    owner: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    percent_complete: int = Form(0),
):
    db.create_project(
        {
            "id": id.strip(),
            "name": name.strip(),
            "description": description.strip(),
            "priority": priority,
            "status": status,
            "owner": owner.strip(),
            "start_date": start_date or None,
            "end_date": end_date or None,
            "percent_complete": percent_complete,
        }
    )
    projects = db.get_all_projects()
    return templates.TemplateResponse(
        request,
        "partials/project_table.html",
        {"projects": projects},
    )


@router.put("/projects/{project_id}", response_class=HTMLResponse)
def update_project(
    request: Request,
    project_id: str,
    name: str = Form(...),
    description: str = Form(""),
    priority: str = Form("Media"),
    status: str = Form("Backlog"),
    owner: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    percent_complete: int = Form(0),
):
    db.update_project(
        project_id,
        {
            "name": name.strip(),
            "description": description.strip(),
            "priority": priority,
            "status": status,
            "owner": owner.strip(),
            "start_date": start_date or None,
            "end_date": end_date or None,
            "percent_complete": percent_complete,
        },
    )
    projects = db.get_all_projects()
    return templates.TemplateResponse(
        request,
        "partials/project_table.html",
        {"projects": projects},
    )


@router.delete("/projects/{project_id}", response_class=HTMLResponse)
def delete_project(request: Request, project_id: str):
    db.delete_project(project_id)
    projects = db.get_all_projects()
    return templates.TemplateResponse(
        request,
        "partials/project_table.html",
        {"projects": projects},
    )


@router.patch("/projects/{project_id}/status", response_class=HTMLResponse)
def update_status(request: Request, project_id: str, status: str = Form(...)):
    db.update_project_status(project_id, status)
    stats = db.get_stats()
    return templates.TemplateResponse(
        request,
        "partials/stats_cards.html",
        {"stats": stats},
    )


# ── Graph API ──────────────────────────────────────────────────────────────────────────

@router.get("/api/graph-data")
def graph_data():
    projects = db.get_all_projects()
    nodes = []
    links = []

    for p in projects:
        nodes.append({
            "id": p["id"],
            "name": p["name"],
            "status": p["status"],
            "priority": p["priority"],
            "owner": p["owner"] or "",
            "percent": p["percent_complete"],
        })

    # Build owner-based edges: projects sharing same owner get a link
    owner_map: dict = {}
    for p in projects:
        o = p["owner"] or ""
        if o:
            owner_map.setdefault(o, []).append(p["id"])

    seen = set()
    for owner, ids in owner_map.items():
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                key = tuple(sorted([ids[i], ids[j]]))
                if key not in seen:
                    seen.add(key)
                    links.append({"source": ids[i], "target": ids[j], "owner": owner})

    return JSONResponse({"nodes": nodes, "links": links})


@router.get("/explorer", response_class=HTMLResponse)
def explorer_page(request: Request):
    return templates.TemplateResponse(
        request,
        "explorer.html",
        {"active_page": "explorer"},
    )
