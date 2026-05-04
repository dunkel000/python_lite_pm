# Technology Stack - Project Tracker

This document outlines the core technologies and frameworks used in the Project Tracker application.

## Backend
- **Language:** Python 3.x
- **Web Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous, high-performance)
- **Web Server:** [Uvicorn](https://www.uvicorn.org/)
- **Database:** [SQLite](https://www.sqlite.org/) (via `sqlite3` standard library)
- **Security & Sessions:**
  - CSRF protection (custom implementation)
  - Session management via `SessionMiddleware`
  - [itsdangerous](https://itsdangerous.palletsprojects.com/) for signing/serialization

## Frontend
- **Templating:** [Jinja2](https://jinja.palletsprojects.com/) (Server-side rendering)
- **Interactivity:** [HTMX](https://htmx.org/) (Dynamic UI updates without full page reloads)
- **Styling:** Custom CSS (`static/styles.css`)
- **UI Components:** "AGI" themed UI kit (`ui_kits/agi/`)

## Infrastructure & Integration
- **Obsidian Vault:** Automated management of project descriptions as Markdown files compatible with [Obsidian](https://obsidian.md/).
- **Deployment:** Configured for systemd (see `tracker.service`).
- **Environment Management:** Local `.env` file support via custom loader in `db.py`.

## Core Features
- Project lifecycle management (Backlog to Completed).
- Decision tracking and logging.
- Status history/log.
- User and Tag management.
- Dashboard with real-time stats.
