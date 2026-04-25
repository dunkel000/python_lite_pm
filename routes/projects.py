from datetime import date, timedelta
import json
import sqlite3

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

import db
from security import csrf_token

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

def _error_fragment(message: str) -> HTMLResponse:
    html = (
        '<div class="p-4 text-sm text-destructive bg-destructive/10 '
        'border border-destructive/30 rounded-md">'
        f"{message}"
        "</div>"
    )
    return HTMLResponse(html, status_code=400)

def _parse_int(value: str):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _ctx(request: Request, **kwargs):
    return {"csrf_token": csrf_token(request), **kwargs}


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    projects = db.get_all_projects()
    stats = db.get_stats()
    users_list = db.list_users()
    tags_list = db.list_tags()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        _ctx(
            request,
            projects=projects,
            stats=stats,
            users=users_list,
            tags=tags_list,
            active_page="dashboard",
        ),
    )


@router.get("/gantt", response_class=HTMLResponse)
def gantt_page(
    request: Request,
    status: str = "",
    priority: str = "",
    assigned_user_id: str = "",
    tag_id: str = "",
):
    projects = db.get_all_projects(
        status or None,
        priority or None,
        _parse_int(assigned_user_id),
        _parse_int(tag_id),
    )
    weeks = _compute_gantt_weeks()
    gantt_data = _gantt_project_data(projects, weeks)
    return templates.TemplateResponse(
        request,
        "gantt.html",
        _ctx(
            request,
            gantt_data=gantt_data,
            weeks=weeks,
            active_page="gantt",
            filter_status=status,
            filter_priority=priority,
            filter_user=assigned_user_id,
            filter_tag=tag_id,
            users=db.list_users(),
            tags=db.list_tags(),
        ),
    )


# ── Partials ──────────────────────────────────────────────────────────────────

@router.get("/partials/project-table", response_class=HTMLResponse)
def partial_project_table(
    request: Request,
    status: str = "",
    priority: str = "",
    assigned_user_id: str = "",
    tag_id: str = "",
):
    projects = db.get_all_projects(
        status or None,
        priority or None,
        _parse_int(assigned_user_id),
        _parse_int(tag_id),
    )
    return templates.TemplateResponse(
        request,
        "partials/project_table.html",
        _ctx(request, projects=projects),
    )


@router.get("/partials/stats", response_class=HTMLResponse)
def partial_stats(request: Request):
    stats = db.get_stats()
    return templates.TemplateResponse(
        request,
        "partials/stats_cards.html",
        _ctx(request, stats=stats),
    )


@router.get("/partials/project-form", response_class=HTMLResponse)
def partial_project_form(request: Request, id: str = ""):
    project = db.get_project(id) if id else None
    next_id = db.next_project_id()
    current_tags = (
        ", ".join(t["name"] for t in project["tags"]) if project else ""
    )
    return templates.TemplateResponse(
        request,
        "partials/project_form.html",
        _ctx(
            request,
            project=project,
            next_id=next_id,
            users=db.list_users(),
            current_tags=current_tags,
        ),
    )


@router.get("/partials/gantt-chart", response_class=HTMLResponse)
def partial_gantt_chart(
    request: Request,
    status: str = "",
    priority: str = "",
    assigned_user_id: str = "",
    tag_id: str = "",
):
    projects = db.get_all_projects(
        status or None,
        priority or None,
        _parse_int(assigned_user_id),
        _parse_int(tag_id),
    )
    weeks = _compute_gantt_weeks()
    gantt_data = _gantt_project_data(projects, weeks)
    return templates.TemplateResponse(
        request,
        "partials/gantt_chart.html",
        _ctx(request, gantt_data=gantt_data, weeks=weeks),
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
        _ctx(request, project=project, decisions=decisions, status_log=status_log),
    )


# ── CRUD ──────────────────────────────────────────────────────────────────────

def _parse_tags(raw: str):
    return [t.strip() for t in (raw or "").split(",") if t.strip()]


@router.post("/projects", response_class=HTMLResponse)
def create_project(
    request: Request,
    id: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    create_description_md: str = Form(""),
    priority: str = Form("Media"),
    status: str = Form("Backlog"),
    assigned_user_id: str = Form(""),
    tags: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    percent_complete: int = Form(0),
):
    parsed_assigned_user_id = _parse_int(assigned_user_id)
    if parsed_assigned_user_id is not None and not db.get_user(parsed_assigned_user_id):
        return _error_fragment("El usuario asignado no es válido o ya no existe.")

    project_data = {
        "id": id.strip(),
        "name": name.strip(),
        "description": description.strip(),
        "priority": priority,
        "status": status,
        "assigned_user_id": parsed_assigned_user_id,
        "start_date": start_date or None,
        "end_date": end_date or None,
        "percent_complete": percent_complete,
        "tag_names": _parse_tags(tags),
    }
    try:
        db.create_project(project_data)
    except sqlite3.IntegrityError:
        return _error_fragment("El usuario asignado no es válido o ya no existe.")

    if create_description_md:
        md_path = db.create_project_description_note(project_data)
        if not project_data["description"]:
            db.update_project(
                project_data["id"],
                {**project_data, "description": f"Nota Obsidian: {md_path}"},
            )
    projects = db.get_all_projects()
    return templates.TemplateResponse(
        request,
        "partials/project_table.html",
        _ctx(request, projects=projects),
    )


@router.put("/projects/{project_id}", response_class=HTMLResponse)
def update_project(
    request: Request,
    project_id: str,
    name: str = Form(...),
    description: str = Form(""),
    priority: str = Form("Media"),
    status: str = Form("Backlog"),
    assigned_user_id: str = Form(""),
    tags: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    percent_complete: int = Form(0),
):
    parsed_assigned_user_id = _parse_int(assigned_user_id)
    if parsed_assigned_user_id is not None and not db.get_user(parsed_assigned_user_id):
        return _error_fragment("El usuario asignado no es válido o ya no existe.")

    try:
        db.update_project(
            project_id,
            {
                "name": name.strip(),
                "description": description.strip(),
                "priority": priority,
                "status": status,
                "assigned_user_id": parsed_assigned_user_id,
                "start_date": start_date or None,
                "end_date": end_date or None,
                "percent_complete": percent_complete,
                "tag_names": _parse_tags(tags),
            },
        )
    except sqlite3.IntegrityError:
        return _error_fragment("El usuario asignado no es válido o ya no existe.")
    projects = db.get_all_projects()
    return templates.TemplateResponse(
        request,
        "partials/project_table.html",
        _ctx(request, projects=projects),
    )


@router.delete("/projects/{project_id}", response_class=HTMLResponse)
def delete_project(request: Request, project_id: str):
    db.delete_project(project_id)
    projects = db.get_all_projects()
    return templates.TemplateResponse(
        request,
        "partials/project_table.html",
        _ctx(request, projects=projects),
    )


@router.patch("/projects/{project_id}/status", response_class=HTMLResponse)
def update_status(request: Request, project_id: str, status: str = Form(...)):
    db.update_project_status(project_id, status)
    stats = db.get_stats()
    return templates.TemplateResponse(
        request,
        "partials/stats_cards.html",
        _ctx(request, stats=stats),
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
            "assigned_user_id": p.get("assigned_user_id"),
            "assigned_user_name": p.get("assigned_user_name") or "",
            "assigned_user_email": p.get("assigned_user_email") or "",
            "percent": p["percent_complete"],
        })

    user_map: dict = {}
    user_name_by_id: dict = {}
    for p in projects:
        uid = p.get("assigned_user_id")
        if uid:
            user_map.setdefault(uid, []).append(p["id"])
            user_name_by_id[uid] = p.get("assigned_user_name") or ""

    seen = set()
    for uid, ids in user_map.items():
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                key = tuple(sorted([ids[i], ids[j]]))
                if key not in seen:
                    seen.add(key)
                    links.append({
                        "source": ids[i],
                        "target": ids[j],
                        "user_id": uid,
                        "user_name": user_name_by_id.get(uid, ""),
                    })

    return JSONResponse({"nodes": nodes, "links": links})


@router.get("/explorer", response_class=HTMLResponse)
def explorer_page(request: Request):
    return templates.TemplateResponse(
        request,
        "explorer.html",
        _ctx(request, active_page="explorer"),
    )
