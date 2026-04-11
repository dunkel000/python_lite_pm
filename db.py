import sqlite3
import os
from datetime import datetime

DB_PATH = os.getenv("SQLITE_DB_PATH", os.path.join(os.path.dirname(__file__), "data", "tracker.db"))


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                priority TEXT CHECK(priority IN ('Alta','Media','Baja')),
                status TEXT CHECK(status IN ('Backlog','Pendiente','En Progreso','Bloqueado','Completado')),
                owner TEXT,
                start_date TEXT,
                end_date TEXT,
                percent_complete INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
                decision TEXT NOT NULL,
                context TEXT,
                decided_by TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS status_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
                old_status TEXT,
                new_status TEXT,
                changed_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS "references" (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT NOT NULL,
                authors    TEXT,
                year       INTEGER,
                type       TEXT CHECK(type IN ('paper','book','chapter')),
                abstract   TEXT,
                doi        TEXT,
                url        TEXT,
                tags       TEXT,
                journal    TEXT,
                publisher  TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
    _seed_if_empty(conn)
    _seed_references_if_empty(conn)
    conn.close()


def _seed_if_empty(conn):
    count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    if count > 0:
        return
    seed_projects = [
        {
            "id": "DEV-001",
            "name": "Automatización REDEC",
            "description": "Automatizar el proceso de carga y validación de datos REDEC para reducir errores manuales y tiempo de procesamiento.",
            "priority": "Alta",
            "status": "En Progreso",
            "owner": "Diego",
            "start_date": "2026-01-15",
            "end_date": "2026-04-30",
            "percent_complete": 45,
        },
        {
            "id": "DEV-002",
            "name": "Reporte de Cartera",
            "description": "Generar reportes automáticos de cartera para clientes de Activos Privados con datos en tiempo real.",
            "priority": "Alta",
            "status": "Pendiente",
            "owner": "Diego",
            "start_date": "2026-03-01",
            "end_date": "2026-06-15",
            "percent_complete": 10,
        },
        {
            "id": "DEV-003",
            "name": "Alertas de Vencimiento",
            "description": "Sistema de alertas automáticas para vencimientos de instrumentos en cartera.",
            "priority": "Media",
            "status": "Backlog",
            "owner": "Equipo",
            "start_date": "2026-05-01",
            "end_date": "2026-07-31",
            "percent_complete": 0,
        },
        {
            "id": "DEV-004",
            "name": "Conciliación Custodia",
            "description": "Reconciliación automática de posiciones con custodios externos para detectar discrepancias.",
            "priority": "Alta",
            "status": "Bloqueado",
            "owner": "Diego",
            "start_date": "2026-02-01",
            "end_date": "2026-05-15",
            "percent_complete": 30,
        },
        {
            "id": "DEV-005",
            "name": "Template Informes CMF",
            "description": "Estandarizar los templates de informes regulatorios para la CMF con validación automática.",
            "priority": "Baja",
            "status": "Completado",
            "owner": "Equipo",
            "start_date": "2025-11-01",
            "end_date": "2026-02-28",
            "percent_complete": 100,
        },
    ]
    for p in seed_projects:
        conn.execute(
            """INSERT INTO projects (id, name, description, priority, status, owner,
               start_date, end_date, percent_complete)
               VALUES (:id, :name, :description, :priority, :status, :owner,
               :start_date, :end_date, :percent_complete)""",
            p,
        )
    conn.commit()


def _seed_references_if_empty(conn):
    count = conn.execute("SELECT COUNT(*) FROM \"references\"").fetchone()[0]
    if count > 0:
        return
    seed_refs = [
        {
            "title": "Asset Pricing",
            "authors": "John H. Cochrane",
            "year": 2005,
            "type": "book",
            "abstract": "A comprehensive treatment of modern asset pricing theory. Covers consumption-based models, factor pricing, option pricing, and the equity premium puzzle from a unified stochastic discount factor perspective.",
            "doi": None,
            "url": "https://press.uchicago.edu/ucp/books/book/chicago/A/bo3772499.html",
            "tags": "#finance #assetpricing #sdf author:Cochrane",
            "journal": None,
            "publisher": "University of Chicago Press",
        },
        {
            "title": "The Cross-Section of Expected Stock Returns",
            "authors": "Eugene F. Fama, Kenneth R. French",
            "year": 1992,
            "type": "paper",
            "abstract": "Two easily measured variables, size and book-to-market equity, combine to capture the cross-sectional variation in average stock returns associated with market beta, size, leverage, book-to-market equity, and earnings-price ratios.",
            "doi": "10.1111/j.1540-6261.1992.tb04398.x",
            "url": "https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1992.tb04398.x",
            "tags": "#finance #factormodels #crosssection author:Fama author:French",
            "journal": "The Journal of Finance",
            "publisher": None,
        },
        {
            "title": "An Introduction to Markov Chain Monte Carlo Methods",
            "authors": "Matthew Richey",
            "year": 2010,
            "type": "paper",
            "abstract": "A gentle introduction to Markov chain Monte Carlo methods, with applications to Bayesian inference and computational statistics. Covers the Metropolis-Hastings algorithm, Gibbs sampling, and convergence diagnostics.",
            "doi": "10.1080/00029890.2010.10390634",
            "url": None,
            "tags": "#markovprocess #mcmc #bayesian #statistics author:Richey",
            "journal": "The American Mathematical Monthly",
            "publisher": None,
        },
        {
            "title": "Portfolio Selection",
            "authors": "Harry M. Markowitz",
            "year": 1952,
            "type": "paper",
            "abstract": "The paper introduces the mean-variance framework for portfolio selection. It establishes the concept of the efficient frontier and demonstrates how diversification reduces portfolio risk without sacrificing expected return.",
            "doi": "10.2307/2975974",
            "url": "https://www.jstor.org/stable/2975974",
            "tags": "#finance #portfolio #optimization #meanvariance author:Markowitz",
            "journal": "The Journal of Finance",
            "publisher": None,
        },
    ]
    for r in seed_refs:
        conn.execute(
            """INSERT INTO \"references\" (title, authors, year, type, abstract, doi, url, tags, journal, publisher)
               VALUES (:title, :authors, :year, :type, :abstract, :doi, :url, :tags, :journal, :publisher)""",
            r,
        )
    conn.commit()


# ── Projects ──────────────────────────────────────────────────────────────────

def get_all_projects(status: str = None, priority: str = None):
    conn = get_conn()
    query = "SELECT * FROM projects WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_project(project_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_project(data: dict):
    conn = get_conn()
    with conn:
        conn.execute(
            """INSERT INTO projects (id, name, description, priority, status, owner,
               start_date, end_date, percent_complete)
               VALUES (:id, :name, :description, :priority, :status, :owner,
               :start_date, :end_date, :percent_complete)""",
            data,
        )
        conn.execute(
            "INSERT INTO status_log (project_id, old_status, new_status) VALUES (?, ?, ?)",
            (data["id"], None, data.get("status")),
        )
    conn.close()


def update_project(project_id: str, data: dict):
    current = get_project(project_id)
    conn = get_conn()
    with conn:
        conn.execute(
            """UPDATE projects SET name=:name, description=:description, priority=:priority,
               status=:status, owner=:owner, start_date=:start_date, end_date=:end_date,
               percent_complete=:percent_complete, updated_at=datetime('now')
               WHERE id=:id""",
            {**data, "id": project_id},
        )
        if current and current.get("status") != data.get("status"):
            conn.execute(
                "INSERT INTO status_log (project_id, old_status, new_status) VALUES (?, ?, ?)",
                (project_id, current["status"], data["status"]),
            )
    conn.close()


def update_project_status(project_id: str, new_status: str):
    current = get_project(project_id)
    if not current:
        return
    conn = get_conn()
    with conn:
        conn.execute(
            "UPDATE projects SET status=?, updated_at=datetime('now') WHERE id=?",
            (new_status, project_id),
        )
        if current["status"] != new_status:
            conn.execute(
                "INSERT INTO status_log (project_id, old_status, new_status) VALUES (?, ?, ?)",
                (project_id, current["status"], new_status),
            )
    conn.close()


def delete_project(project_id: str):
    conn = get_conn()
    with conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.close()


def next_project_id():
    conn = get_conn()
    rows = conn.execute("SELECT id FROM projects WHERE id LIKE 'DEV-%'").fetchall()
    conn.close()
    nums = []
    for r in rows:
        try:
            nums.append(int(r["id"].split("-")[1]))
        except (IndexError, ValueError):
            pass
    return f"DEV-{(max(nums) + 1 if nums else 1):03d}"


# ── Decisions ─────────────────────────────────────────────────────────────────

def get_decisions(project_id: str):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM decisions WHERE project_id = ? ORDER BY created_at DESC",
        (project_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_decisions(project_id: str = None):
    conn = get_conn()
    if project_id:
        rows = conn.execute(
            """SELECT d.*, p.name as project_name FROM decisions d
               JOIN projects p ON d.project_id = p.id
               WHERE d.project_id = ? ORDER BY d.created_at DESC""",
            (project_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT d.*, p.name as project_name FROM decisions d
               JOIN projects p ON d.project_id = p.id
               ORDER BY d.created_at DESC"""
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_decision(project_id: str, data: dict):
    conn = get_conn()
    with conn:
        conn.execute(
            """INSERT INTO decisions (project_id, decision, context, decided_by)
               VALUES (?, ?, ?, ?)""",
            (project_id, data.get("decision"), data.get("context"), data.get("decided_by")),
        )
    conn.close()


# ── Status Log ────────────────────────────────────────────────────────────────

def get_status_log(project_id: str):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM status_log WHERE project_id = ? ORDER BY changed_at DESC",
        (project_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Stats ─────────────────────────────────────────────────────────────────────

def get_stats():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    en_progreso = conn.execute(
        "SELECT COUNT(*) FROM projects WHERE status = 'En Progreso'"
    ).fetchone()[0]
    bloqueados = conn.execute(
        "SELECT COUNT(*) FROM projects WHERE status = 'Bloqueado'"
    ).fetchone()[0]
    completados_mes = conn.execute(
        """SELECT COUNT(*) FROM projects
           WHERE status = 'Completado'
           AND strftime('%Y-%m', updated_at) = strftime('%Y-%m', 'now')"""
    ).fetchone()[0]
    conn.close()
    return {
        "total": total,
        "en_progreso": en_progreso,
        "bloqueados": bloqueados,
        "completados_mes": completados_mes,
    }


# ── References ─────────────────────────────────────────────────────────────────────────────────

def get_all_references(ref_type: str = None, search: str = None, tag: str = None):
    conn = get_conn()
    query = 'SELECT * FROM "references" WHERE 1=1'
    params = []
    if ref_type:
        query += " AND type = ?"
        params.append(ref_type)
    if search:
        query += " AND (title LIKE ? OR authors LIKE ? OR abstract LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    if tag:
        query += " AND tags LIKE ?"
        params.append(f"%{tag}%")
    query += " ORDER BY year DESC, created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_reference(ref_id: int):
    conn = get_conn()
    row = conn.execute('SELECT * FROM "references" WHERE id = ?', (ref_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_reference(data: dict):
    conn = get_conn()
    with conn:
        cursor = conn.execute(
            """INSERT INTO \"references\" (title, authors, year, type, abstract, doi, url, tags, journal, publisher)
               VALUES (:title, :authors, :year, :type, :abstract, :doi, :url, :tags, :journal, :publisher)""",
            data,
        )
    ref_id = cursor.lastrowid
    conn.close()
    return ref_id


def update_reference(ref_id: int, data: dict):
    conn = get_conn()
    with conn:
        conn.execute(
            """UPDATE \"references\" SET title=:title, authors=:authors, year=:year,
               type=:type, abstract=:abstract, doi=:doi, url=:url,
               tags=:tags, journal=:journal, publisher=:publisher
               WHERE id=:id""",
            {**data, "id": ref_id},
        )
    conn.close()


def delete_reference(ref_id: int):
    conn = get_conn()
    with conn:
        conn.execute('DELETE FROM "references" WHERE id = ?', (ref_id,))
    conn.close()


def get_reference_stats():
    conn = get_conn()
    total = conn.execute('SELECT COUNT(*) FROM "references"').fetchone()[0]
    papers = conn.execute('SELECT COUNT(*) FROM "references" WHERE type = \'paper\'').fetchone()[0]
    books = conn.execute('SELECT COUNT(*) FROM "references" WHERE type = \'book\'').fetchone()[0]
    chapters = conn.execute('SELECT COUNT(*) FROM "references" WHERE type = \'chapter\'').fetchone()[0]
    newest = conn.execute('SELECT MAX(year) FROM "references"').fetchone()[0]
    conn.close()
    return {
        "total": total,
        "papers": papers,
        "books": books,
        "chapters": chapters,
        "newest_year": newest,
    }
