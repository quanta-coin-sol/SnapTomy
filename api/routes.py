import json
import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


def _engine():
    from .server import trading_engine
    return trading_engine


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/positions")
async def list_positions():
    engine = _engine()
    if not engine:
        return {"positions": []}
    open_positions = engine.position_manager.get_open_positions()
    closed_positions = engine.position_manager.get_closed_positions()
    return {"open": open_positions, "closed": closed_positions, "count": len(open_positions)}


@router.get("/portfolio")
async def portfolio():
    engine = _engine()
    if not engine:
        return {"balance": 0, "total_value": 0, "pnl": 0}
    positions = engine.position_manager.positions
    engine.portfolio.update(engine.position_manager.get_open_positions(), engine.executor.balance_usd)
    metrics = engine.portfolio.get_metrics(positions)
    return metrics


@router.get("/config")
async def get_config():
    engine = _engine()
    if not engine:
        return {"config": {}}
    return {"config": engine.config}


@router.get("/logs")
async def get_logs(lines: int = 50):
    try:
        with open("bot.log") as f:
            all_lines = f.readlines()
            return {"logs": all_lines[-lines:]}
    except Exception:
        return {"logs": []}
