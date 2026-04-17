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

# 2. Crear entorno conda e instalar dependencias
conda create -n lite_pm python=3.10
conda activate lite_pm
pip install -r requirements.txt

# 3. Iniciar el servidor (crea la base de datos automáticamente)
python main.py
```

El servidor levanta en http://localhost:8000

### Actualizar el servidor

Si ya tienes el proyecto desplegado y solo quieres traer cambios del repositorio, usa este flujo:

```bash
# 1. Ir al directorio del proyecto
cd /ruta/a/python_lite_pm

# 2. Traer últimos cambios
git pull

# 3. (Opcional, recomendado) Reactivar entorno e instalar dependencias por si hubo cambios
conda activate lite_pm
pip install -r requirements.txt

# 4. Reiniciar servicio en el servidor
sudo systemctl restart tracker
sudo systemctl status tracker
```

#### ¿Hace falta reinstalar o recompilar?

- **Reinstalar dependencias**: solo si cambió `requirements.txt` (o si tienes errores de importación).
- **Recompilar**: **no aplica** en este proyecto, porque no usa pipeline de build (sin Node, sin bundlers, Tailwind por CDN).
- **Migraciones de base de datos**: el sistema las aplica al arrancar (`init_db()`), así que normalmente basta con reiniciar el servicio.

Flujo rápido para mantenimiento rutinario:

```bash
cd /ruta/a/python_lite_pm && git pull && conda activate lite_pm && pip install -r requirements.txt && sudo systemctl restart tracker
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
