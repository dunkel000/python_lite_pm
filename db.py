import re
import sqlite3
import os
import unicodedata
from datetime import datetime
from pathlib import Path


def load_local_env(env_path: str = ".env") -> None:
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')

            if key and key not in os.environ:
                os.environ[key] = value


load_local_env()

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "tracker.db")
OBSIDIAN_DIRNAME = ".obsidian"
OBSIDIAN_NOTES_DIRNAME = "project_descriptions"


class UserNotFoundError(Exception):
    pass


def get_db_path() -> str:
    configured_path = os.getenv("SQLITE_DB_PATH", DEFAULT_DB_PATH)
    return os.path.abspath(os.path.expanduser(configured_path))


def get_db_dir() -> str:
    return os.path.dirname(get_db_path())


def get_conn():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    db_dir = get_db_dir()
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
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

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT
            );

            CREATE TABLE IF NOT EXISTS project_tags (
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                PRIMARY KEY (project_id, tag_id)
            );

            CREATE INDEX IF NOT EXISTS idx_project_tags_tag_id ON project_tags(tag_id);
        """)
        _migrate_users_and_tags(conn)
    _seed_if_empty(conn)
    conn.close()


def _slugify_email_local(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", ".", ascii_only).strip(".").lower()
    return slug or "user"


def _migrate_users_and_tags(conn):
    cols = [row["name"] for row in conn.execute("PRAGMA table_info('projects')").fetchall()]
    if "assigned_user_id" not in cols:
        conn.execute(
            "ALTER TABLE projects ADD COLUMN assigned_user_id INTEGER "
            "REFERENCES users(id) ON DELETE SET NULL"
        )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_projects_assigned_user_id ON projects(assigned_user_id)"
    )

    owners = conn.execute(
        "SELECT DISTINCT owner FROM projects WHERE owner IS NOT NULL AND owner <> ''"
    ).fetchall()
    for row in owners:
        name = row["owner"].strip()
        if not name:
            continue
        email = f"{_slugify_email_local(name)}@placeholder.local"
        conn.execute(
            "INSERT OR IGNORE INTO users (name, email) VALUES (?, ?)",
            (name, email),
        )

    conn.execute(
        """UPDATE projects
           SET assigned_user_id = (
               SELECT id FROM users WHERE users.name = projects.owner
           )
           WHERE assigned_user_id IS NULL
             AND owner IS NOT NULL
             AND owner <> ''"""
    )


def ensure_obsidian_vault() -> Path:
    """
    Prepara una estructura mínima para que el directorio de la DB funcione como vault de Obsidian.
    """
    vault_dir = Path(get_db_dir())
    vault_dir.mkdir(parents=True, exist_ok=True)

    obsidian_dir = vault_dir / OBSIDIAN_DIRNAME
    obsidian_dir.mkdir(exist_ok=True)

    app_json = obsidian_dir / "app.json"
    if not app_json.exists():
        app_json.write_text('{\n  "legacyEditor": false\n}\n', encoding="utf-8")

    core_plugins_json = obsidian_dir / "core-plugins.json"
    if not core_plugins_json.exists():
        core_plugins_json.write_text("[]\n", encoding="utf-8")

    (vault_dir / OBSIDIAN_NOTES_DIRNAME).mkdir(exist_ok=True)
    return vault_dir


def _description_note_template(project: dict) -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return f"""---
project_id: {project['id']}
name: {project['name']}
status: {project.get('status') or ''}
priority: {project.get('priority') or ''}
owner: {project.get('owner') or ''}
created_at: {now}
---

# {project['name']}

## Resumen
> Describe el objetivo general del proyecto.

## Alcance
- Entregable 1
- Entregable 2

## Hitos
- [ ] Hito inicial
- [ ] Hito intermedio
- [ ] Hito final

## Riesgos / Bloqueos
- Ninguno por ahora.

## Enlaces
- Proyecto en tracker: `{project['id']}`
"""


def create_project_description_note(project: dict) -> str:
    """
    Crea un archivo markdown para la descripción del proyecto dentro del directorio
    donde vive la DB (vault Obsidian).
    Devuelve la ruta absoluta del archivo.
    """
    vault_dir = ensure_obsidian_vault()
    notes_dir = vault_dir / OBSIDIAN_NOTES_DIRNAME
    note_path = notes_dir / f"{project['id']}.md"

    if not note_path.exists():
        note_path.write_text(_description_note_template(project), encoding="utf-8")

    return str(note_path.resolve())


def _seed_if_empty(conn):
    count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    if count > 0:
        return
    seed_users = [
        ("Diego", "diego@placeholder.local"),
        ("Equipo", "equipo@placeholder.local"),
    ]
    for name, email in seed_users:
        conn.execute(
            "INSERT OR IGNORE INTO users (name, email) VALUES (?, ?)",
            (name, email),
        )
    user_id_by_name = {
        row["name"]: row["id"]
        for row in conn.execute("SELECT id, name FROM users").fetchall()
    }

    seed_projects = [
        {
            "id": "DEV-001",
            "name": "Automatización REDEC",
            "description": "Automatizar el proceso de carga y validación de datos REDEC para reducir errores manuales y tiempo de procesamiento.",
            "priority": "Alta",
            "status": "En Progreso",
            "assigned_user_id": user_id_by_name.get("Diego"),
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
            "assigned_user_id": user_id_by_name.get("Diego"),
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
            "assigned_user_id": user_id_by_name.get("Equipo"),
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
            "assigned_user_id": user_id_by_name.get("Diego"),
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
            "assigned_user_id": user_id_by_name.get("Equipo"),
            "start_date": "2025-11-01",
            "end_date": "2026-02-28",
            "percent_complete": 100,
        },
    ]
    for p in seed_projects:
        conn.execute(
            """INSERT INTO projects (id, name, description, priority, status,
               assigned_user_id, start_date, end_date, percent_complete)
               VALUES (:id, :name, :description, :priority, :status,
               :assigned_user_id, :start_date, :end_date, :percent_complete)""",
            p,
        )
    conn.commit()



# ── Projects ──────────────────────────────────────────────────────────────────

_PROJECT_SELECT = """
    SELECT p.*, u.name AS assigned_user_name, u.email AS assigned_user_email
    FROM projects p
    LEFT JOIN users u ON u.id = p.assigned_user_id
"""


def _attach_tags(conn, project: dict) -> dict:
    project["tags"] = [
        dict(r)
        for r in conn.execute(
            """SELECT t.id, t.name, t.color
               FROM project_tags pt JOIN tags t ON t.id = pt.tag_id
               WHERE pt.project_id = ?
               ORDER BY t.name""",
            (project["id"],),
        ).fetchall()
    ]
    return project


def get_all_projects(
    status: str = None,
    priority: str = None,
    assigned_user_id: int = None,
    tag_id: int = None,
):
    conn = get_conn()
    query = _PROJECT_SELECT + " WHERE 1=1"
    params = []
    if status:
        query += " AND p.status = ?"
        params.append(status)
    if priority:
        query += " AND p.priority = ?"
        params.append(priority)
    if assigned_user_id is not None:
        query += " AND p.assigned_user_id = ?"
        params.append(assigned_user_id)
    if tag_id is not None:
        query += (
            " AND EXISTS (SELECT 1 FROM project_tags pt "
            "WHERE pt.project_id = p.id AND pt.tag_id = ?)"
        )
        params.append(tag_id)
    query += " ORDER BY p.created_at DESC"
    rows = conn.execute(query, params).fetchall()
    projects = [_attach_tags(conn, dict(r)) for r in rows]
    conn.close()
    return projects


def get_project(project_id: str):
    conn = get_conn()
    row = conn.execute(
        _PROJECT_SELECT + " WHERE p.id = ?", (project_id,)
    ).fetchone()
    project = _attach_tags(conn, dict(row)) if row else None
    conn.close()
    return project


def create_project(data: dict):
    tag_names = data.get("tag_names") or []
    conn = get_conn()
    with conn:
        conn.execute(
            """INSERT INTO projects (id, name, description, priority, status,
               assigned_user_id, start_date, end_date, percent_complete)
               VALUES (:id, :name, :description, :priority, :status,
               :assigned_user_id, :start_date, :end_date, :percent_complete)""",
            data,
        )
        conn.execute(
            "INSERT INTO status_log (project_id, old_status, new_status) VALUES (?, ?, ?)",
            (data["id"], None, data.get("status")),
        )
        _set_project_tags_tx(conn, data["id"], tag_names)
    conn.close()


def update_project(project_id: str, data: dict):
    current = get_project(project_id)
    tag_names = data.get("tag_names")
    conn = get_conn()
    with conn:
        conn.execute(
            """UPDATE projects SET name=:name, description=:description, priority=:priority,
               status=:status, assigned_user_id=:assigned_user_id,
               start_date=:start_date, end_date=:end_date,
               percent_complete=:percent_complete, updated_at=datetime('now')
               WHERE id=:id""",
            {**data, "id": project_id},
        )
        if current and current.get("status") != data.get("status"):
            conn.execute(
                "INSERT INTO status_log (project_id, old_status, new_status) VALUES (?, ?, ?)",
                (project_id, current["status"], data["status"]),
            )
        if tag_names is not None:
            _set_project_tags_tx(conn, project_id, tag_names)
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


def update_decision(project_id: str, decision_id: int, data: dict):
    conn = get_conn()
    with conn:
        conn.execute(
            """UPDATE decisions
               SET decision = ?, context = ?, decided_by = ?
               WHERE id = ? AND project_id = ?""",
            (
                data.get("decision"),
                data.get("context"),
                data.get("decided_by"),
                decision_id,
                project_id,
            ),
        )
    conn.close()


def delete_decision(project_id: str, decision_id: int):
    conn = get_conn()
    with conn:
        conn.execute(
            "DELETE FROM decisions WHERE id = ? AND project_id = ?",
            (decision_id, project_id),
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


# ── Users ─────────────────────────────────────────────────────────────────────

def list_users():
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, name, email, created_at FROM users ORDER BY name COLLATE NOCASE"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user(user_id: int):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_email(email: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, name, email, created_at FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_user(name: str, email: str) -> int:
    conn = get_conn()
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO users (name, email) VALUES (?, ?)",
                (name, email),
            )
            return cur.lastrowid
    finally:
        conn.close()


def update_user(user_id: int, name: str, email: str) -> None:
    conn = get_conn()
    try:
        with conn:
            cur = conn.execute(
                "UPDATE users SET name = ?, email = ? WHERE id = ?",
                (name, email, user_id),
            )
            if cur.rowcount == 0:
                raise UserNotFoundError(f"User with id {user_id} not found.")
    finally:
        conn.close()


def delete_user(user_id: int) -> None:
    conn = get_conn()
    try:
        with conn:
            cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            if cur.rowcount == 0:
                raise UserNotFoundError(f"User with id {user_id} not found.")
    finally:
        conn.close()


# ── Tags ──────────────────────────────────────────────────────────────────────

def list_tags():
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, name, color FROM tags ORDER BY name COLLATE NOCASE"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _get_or_create_tag_tx(conn, name: str) -> int:
    normalized = name.strip()
    if not normalized:
        return 0
    row = conn.execute(
        "SELECT id FROM tags WHERE LOWER(name) = LOWER(?)",
        (normalized,),
    ).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO tags (name) VALUES (?)",
        (normalized,),
    )
    return cur.lastrowid


def _set_project_tags_tx(conn, project_id: str, tag_names):
    conn.execute("DELETE FROM project_tags WHERE project_id = ?", (project_id,))
    seen = set()
    for raw in tag_names:
        name = (raw or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        tag_id = _get_or_create_tag_tx(conn, name)
        conn.execute(
            "INSERT OR IGNORE INTO project_tags (project_id, tag_id) VALUES (?, ?)",
            (project_id, tag_id),
        )


def set_project_tags(project_id: str, tag_names):
    conn = get_conn()
    with conn:
        _set_project_tags_tx(conn, project_id, tag_names)
    conn.close()


def get_project_tags(project_id: str):
    conn = get_conn()
    rows = conn.execute(
        """SELECT t.id, t.name, t.color
           FROM project_tags pt JOIN tags t ON t.id = pt.tag_id
           WHERE pt.project_id = ?
           ORDER BY t.name""",
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
