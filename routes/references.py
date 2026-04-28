from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
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


# ── Graph API ─────────────────────────────────────────────────────────────────

@router.get("/api/references-graph-data")
def references_graph_data():
    refs = db.get_all_references()
    nodes = []
    links = []

    for r in refs:
        nodes.append({
            "id": f"REF-{r['id']}",
            "db_id": r["id"],
            "name": r["title"],
            "authors": r["authors"] or "",
            "year": r["year"],
            "type": r["type"],
            "abstract": r["abstract"] or "",
            "tags": r["tags"] or "",
        })

    # Link based on shared tags
    tag_map = {}
    
    # Link based on shared authors
    author_map = {}
    
    for r in refs:
        ref_node_id = f"REF-{r['id']}"
        # Parse tags
        if r.get("tags"):
            tags = [t.strip().lower() for t in r["tags"].split() if t.strip().startswith("#")]
            for t in tags:
                tag_map.setdefault(t, []).append(ref_node_id)
        
        # Parse authors loosely (by comma)
        if r.get("authors"):
            authors = [a.strip().lower() for a in r["authors"].split(",")]
            for a in authors:
                if a: # avoid empty
                    author_map.setdefault(a, []).append(ref_node_id)

    seen = set()
    
    # Add tag links
    for tag, ids in tag_map.items():
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                key = tuple(sorted([ids[i], ids[j]]))
                if key not in seen:
                    seen.add(key)
                    links.append({"source": ids[i], "target": ids[j], "reason": f"Tag: {tag}"})
                    
    # Add author links
    for author, ids in author_map.items():
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                key = tuple(sorted([ids[i], ids[j]]))
                if key not in seen:
                    seen.add(key)
                    links.append({"source": ids[i], "target": ids[j], "reason": f"Author: {author}"})

    return JSONResponse({"nodes": nodes, "links": links})
