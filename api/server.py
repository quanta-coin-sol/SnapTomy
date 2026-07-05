import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

logger = logging.getLogger(__name__)

app = FastAPI(title="SnapTomy")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
