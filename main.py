import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import db
from routes import projects, decisions, users

app = FastAPI(title="Project Tracker — Activos Privados")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(projects.router)
app.include_router(decisions.router)
app.include_router(users.router)


@app.on_event("startup")
def startup():
    db.init_db()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
