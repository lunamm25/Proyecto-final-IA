from fastapi import FastAPI

app = FastAPI(title="Asesor Pedagógico Inteligente")


@app.get("/api/salud")
def salud():
    return {"estado": "ok"}
