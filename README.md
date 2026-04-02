# Project Tracker — Activos Privados

Dashboard web para gestión de proyectos del equipo de Middle Office (Activos Privados).

## Stack

- **Backend**: Python + FastAPI
- **Templates**: Jinja2 (server-side rendering)
- **Interactividad**: HTMX + Alpine.js (sin Node, sin build step)
- **Estilos**: Tailwind CSS via CDN
- **Base de datos**: SQLite (stdlib)
- **Deploy**: uvicorn + systemd

## Desarrollo local

```bash
# 1. Clonar el repositorio
git clone https://github.com/dunkel000/python_lite_pm.git
cd python_lite_pm

# 2. Crear entorno virtual e instalar dependencias
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Iniciar el servidor (crea la base de datos automáticamente)
python main.py
```

El servidor levanta en http://localhost:8000

## Deploy en Oracle ARM (dragon000)

**Servidor**: 146.235.243.23  
**SSH key**: `~/Downloads/ssh-key-2025-01-28-dragon000-private.key`

```bash
# Conectarse al servidor
ssh -i ~/Downloads/ssh-key-2025-01-28-dragon000-private.key ubuntu@146.235.243.23

# En el servidor: clonar el repo
git clone https://github.com/dunkel000/python_lite_pm.git
cd python_lite_pm

# Instalar dependencias
pip3 install -r requirements.txt

# Copiar el servicio systemd
sudo cp tracker.service /etc/systemd/system/tracker.service

# Editar el servicio si la ruta del repo es diferente
sudo nano /etc/systemd/system/tracker.service

# Habilitar e iniciar
sudo systemctl daemon-reload
sudo systemctl enable tracker
sudo systemctl start tracker

# Verificar estado
sudo systemctl status tracker
sudo journalctl -u tracker -f
```

La app queda disponible en http://146.235.243.23:8000

### Actualizar el servidor

```bash
ssh -i ~/Downloads/ssh-key-2025-01-28-dragon000-private.key ubuntu@146.235.243.23
cd python_lite_pm
git pull origin main
sudo systemctl restart tracker
```

## Estructura de archivos

```
python_lite_pm/
├── main.py                  — Entry point FastAPI + uvicorn
├── db.py                    — SQLite: init, migrations, queries
├── requirements.txt
├── tracker.service          — Systemd service file
├── routes/
│   ├── projects.py          — CRUD proyectos + Gantt + partials
│   └── decisions.py         — CRUD decisiones
├── templates/
│   ├── base.html            — Layout con sidebar
│   ├── dashboard.html       — Vista principal (KPIs + tabla)
│   ├── gantt.html           — Vista Gantt
│   ├── decisions.html       — Vista decisiones global
│   └── partials/            — Fragmentos HTML para HTMX
├── static/
│   └── styles.css           — CSS custom (Gantt bars)
└── data/
    └── tracker.db           — SQLite (creado automáticamente, no en git)
```

## Base de datos

La base de datos se crea automáticamente en `data/tracker.db` al iniciar el servidor. Incluye 5 proyectos de ejemplo pre-cargados.

Para resetear la base de datos:

```bash
rm data/tracker.db
python main.py  # Re-crea con datos de ejemplo
```
