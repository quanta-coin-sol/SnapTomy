import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .routes import router

logger = logging.getLogger(__name__)

app = FastAPI(title="SnapTomy")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

trading_engine = None


def set_trading_engine(engine):
    global trading_engine
    trading_engine = engine


@app.get("/")
async def serve_dashboard():
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard", "index.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return {"error": "dashboard not found"}
