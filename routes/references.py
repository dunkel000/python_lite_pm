from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ── Pages ─────────────────────────────────────────────────────────────────────

@router.get("/biblioteca", response_class=HTMLResponse)
def biblioteca_page(request: Request):
    refs = db.get_all_references()
    stats = db.get_reference_stats()
    return templates.TemplateResponse(
        request,
        "biblioteca.html",
        {"refs": refs, "stats": stats, "active_page": "biblioteca"},
    )


# ── Partials ──────────────────────────────────────────────────────────────────

@router.get("/partials/reference-grid", response_class=HTMLResponse)
def partial_reference_grid(
    request: Request,
    ref_type: str = "",
    search: str = "",
    tag: str = "",
):
    refs = db.get_all_references(
        ref_type=ref_type or None,
        search=search or None,
        tag=tag or None,
    )
    return templates.TemplateResponse(
        request,
        "partials/reference_grid.html",
        {"refs": refs},
    )


@router.get("/partials/reference-detail/{ref_id}", response_class=HTMLResponse)
def partial_reference_detail(request: Request, ref_id: int):
    ref = db.get_reference(ref_id)
    if not ref:
        return HTMLResponse("<p class='p-6 text-red-500'>Referencia no encontrada.</p>", status_code=404)
    return templates.TemplateResponse(
        request,
        "partials/reference_detail.html",
        {"ref": ref},
    )


@router.get("/partials/reference-form", response_class=HTMLResponse)
def partial_reference_form(request: Request, id: int = 0):
    ref = db.get_reference(id) if id else None
    return templates.TemplateResponse(
        request,
        "partials/reference_form.html",
        {"ref": ref},
    )


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.post("/references", response_class=HTMLResponse)
def create_reference(
    request: Request,
    title: str = Form(...),
    authors: str = Form(""),
    year: str = Form(""),
    ref_type: str = Form("paper"),
    abstract: str = Form(""),
    doi: str = Form(""),
    url: str = Form(""),
    tags: str = Form(""),
    journal: str = Form(""),
    publisher: str = Form(""),
):
    db.create_reference({
        "title": title.strip(),
        "authors": authors.strip(),
        "year": int(year) if year.strip().isdigit() else None,
        "type": ref_type,
        "abstract": abstract.strip(),
        "doi": doi.strip() or None,
        "url": url.strip() or None,
        "tags": tags.strip(),
        "journal": journal.strip() or None,
        "publisher": publisher.strip() or None,
    })
    refs = db.get_all_references()
    return templates.TemplateResponse(
        request,
        "partials/reference_grid.html",
        {"refs": refs},
    )


@router.put("/references/{ref_id}", response_class=HTMLResponse)
def update_reference(
    request: Request,
    ref_id: int,
    title: str = Form(...),
    authors: str = Form(""),
    year: str = Form(""),
    ref_type: str = Form("paper"),
    abstract: str = Form(""),
    doi: str = Form(""),
    url: str = Form(""),
    tags: str = Form(""),
    journal: str = Form(""),
    publisher: str = Form(""),
):
    db.update_reference(ref_id, {
        "title": title.strip(),
        "authors": authors.strip(),
        "year": int(year) if year.strip().isdigit() else None,
        "type": ref_type,
        "abstract": abstract.strip(),
        "doi": doi.strip() or None,
        "url": url.strip() or None,
        "tags": tags.strip(),
        "journal": journal.strip() or None,
        "publisher": publisher.strip() or None,
    })
    refs = db.get_all_references()
    return templates.TemplateResponse(
        request,
        "partials/reference_grid.html",
        {"refs": refs},
    )


@router.delete("/references/{ref_id}", response_class=HTMLResponse)
def delete_reference(request: Request, ref_id: int):
    db.delete_reference(ref_id)
    refs = db.get_all_references()
    return templates.TemplateResponse(
        request,
        "partials/reference_grid.html",
        {"refs": refs},
    )
