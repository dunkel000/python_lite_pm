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
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Iniciar el servidor (crea la base de datos automáticamente)
python main.py
```

El servidor levanta en http://localhost:8000

## Dependencias y política de compatibilidad

- `requirements.txt` usa versiones **pineadas** (`==`) para FastAPI, Uvicorn, Jinja2 y python-multipart para tener despliegues reproducibles.
- Compatibilidad esperada:
  - Python: **3.10.x**
  - FastAPI/Uvicorn: compatibles entre sí según las versiones fijadas en `requirements.txt`.
- No se garantiza compatibilidad automática con versiones mayores de esas librerías hasta validar en entorno de staging.

### Procedimiento de upgrade de dependencias

Cuando necesites actualizar FastAPI, Uvicorn, Jinja2 o python-multipart:

```bash
# 1. Crear rama de mantenimiento
git checkout -b chore/deps-upgrade

# 2. Actualizar pines en requirements.txt (editar manualmente)

# 3. Reinstalar limpio en el virtualenv del proyecto
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Levantar app y validar
python main.py
```

Checklist mínima de compatibilidad después del upgrade:

- Arranque correcto de la app sin errores de importación.
- Render de vistas Jinja2 (`/`, `/dashboard`, `/projects`).
- Flujos con formularios multipart (`python-multipart`) funcionando.
- Arranque en servidor con `tracker.service` y reinicio limpio de systemd.

## Configurar la ruta de la base de datos

Puedes definir una ubicación personalizada para SQLite con la variable de entorno `SQLITE_DB_PATH`.
La app ahora carga `.env` automáticamente al iniciar (si existe), así no necesitas exportar variables por terminal cada vez.

### Opción 1 (recomendada): archivo `.env`

```bash
cp .env.example .env
```

Luego edita `.env` y define la ruta deseada:

```env
SQLITE_DB_PATH=/opt/lite_pm_data/tracker.db
```

> `.env` está ignorado por git, por lo que no se versiona.

### Opción 2: variable de entorno en terminal (sesión actual)

```bash
# Ruta absoluta
export SQLITE_DB_PATH="/opt/lite_pm_data/tracker.db"
python main.py

# Ruta relativa al directorio actual
export SQLITE_DB_PATH="./storage/tracker.db"
python main.py
```

### Opción 3: systemd (persistente en servidor)

Usa `EnvironmentFile=` en `tracker.service` para separar configuración del archivo de servicio.

Ejemplo con `/etc/default/tracker`:

```ini
# /etc/default/tracker
SQLITE_DB_PATH=/opt/lite_pm_data/tracker.db
```

Después:

```bash
sudo systemctl daemon-reload
sudo systemctl restart tracker
```

> El servicio de ejemplo (`tracker.service`) asume virtualenv en `/home/ubuntu/python_lite_pm/.venv` y aplica hardening base (`NoNewPrivileges`, `PrivateTmp`, `ProtectSystem`, `ProtectHome`).

Si no defines `SQLITE_DB_PATH`, la aplicación usa por defecto `./data/tracker.db` (dentro del repositorio).

### Mover/copiar la base de datos creada en el primer inicio

Sí: este proyecto usa **SQLite** y crea el archivo automáticamente en el primer arranque.

Si ya levantaste la app una vez y quieres mover la base a otra ruta:

```bash
# 1. Ejecuta una vez para crear la DB inicial (si aún no existe)
python main.py

# 2. Detén la app y crea la carpeta destino
mkdir -p /opt/lite_pm_data

# 3. Copia la base actual a la nueva ubicación
cp data/tracker.db /opt/lite_pm_data/tracker.db

# 4. Configura la nueva ruta en .env
echo "SQLITE_DB_PATH=/opt/lite_pm_data/tracker.db" > .env

# 5. Levanta nuevamente la app usando la nueva ruta
python main.py
```

> Nota: si quieres **mover** en vez de copiar, usa `mv` en lugar de `cp`.

## Base de datos

La base de datos se crea automáticamente al iniciar el servidor. La ruta se toma desde `SQLITE_DB_PATH` o, por defecto, `data/tracker.db`. Incluye 5 proyectos de ejemplo pre-cargados.

### Descripciones Markdown para Obsidian

Al crear un proyecto desde la UI, puedes marcar la opción para generar una descripción en Markdown.

- La nota se crea en la misma ruta de la DB SQLite.
- Archivo generado: `project_descriptions/<ID_DEL_PROYECTO>.md`.
- Si no existe estructura de vault, se crea una mínima compatible con Obsidian (`.obsidian/app.json` y `.obsidian/core-plugins.json`).
- La nota arranca con una plantilla base (frontmatter + secciones de resumen, alcance, hitos y riesgos).

Para resetear la base de datos:

```bash
# Si usas .env y SQLITE_DB_PATH apunta fuera de /data:
rm /opt/lite_pm_data/tracker.db

# O, si usas la ruta por defecto:
rm data/tracker.db

python main.py  # Re-crea con datos de ejemplo
```

### Actualizar el servidor

Si ya tienes el proyecto desplegado y solo quieres traer cambios del repositorio, usa este flujo:

```bash
# 1. Ir al directorio del proyecto
cd /ruta/a/python_lite_pm

# 2. Traer últimos cambios
git -c http.sslVerify=false pull

# 3. (Opcional, recomendado) Reactivar entorno e instalar dependencias por si hubo cambios
source .venv/bin/activate
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
cd /ruta/a/python_lite_pm && source .venv/bin/activate && git -c http.sslVerify=false pull && pip install -r requirements.txt && sudo systemctl restart tracker
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
