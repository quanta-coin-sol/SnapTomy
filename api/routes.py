import logging

from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/positions")
async def list_positions():
    return {"positions": []}


@router.get("/config")
async def get_config(config: dict = None):
    return {"config": config}
