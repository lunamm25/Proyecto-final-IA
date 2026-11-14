from fastapi import FastAPI

from app.api.sandbox import router as sandbox_router

app = FastAPI(title="Asesor Pedagógico Inteligente")
app.include_router(sandbox_router)


@app.get("/api/salud")
def salud():
    return {"estado": "ok"}
