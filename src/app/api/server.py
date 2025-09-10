# src/app/api/server.py
from fastapi import FastAPI
from .routes_public import router as doudian_router

def build_app() -> FastAPI:
    app = FastAPI(title="Doudian Login Service")
    app.include_router(doudian_router)

    @app.get("/healthz")
    async def healthz():
        return {"ok": True}

    return app

app = build_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.api.server:app", host="0.0.0.0", port=8080, reload=False)
