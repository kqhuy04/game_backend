from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.routers import auth, character, afk, market, guild, world_boss
import logging
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

security = HTTPBearer()

app = FastAPI(title="TinyWorld API", version="0.1.0")

@app.on_event("startup")
async def run_migrations():
    logger.info("Running migrations...")
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True, text=True
    )
    logger.info(result.stdout)
    if result.returncode != 0:
        logger.error(result.stderr)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__}
    )

app.include_router(auth.router)
app.include_router(character.router)
app.include_router(afk.router)
app.include_router(market.router)
app.include_router(guild.router)
app.include_router(world_boss.router)

@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    return {
        "status"  : "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "version" : "0.1.0",
    }