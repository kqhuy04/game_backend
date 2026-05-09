from fastapi import FastAPI
from fastapi.security import HTTPBearer
from app.routers import auth, character, afk, market, guild, world_boss

security = HTTPBearer()

app = FastAPI(title="TinyWorld API", version="0.1.0")

app.include_router(auth.router)
app.include_router(character.router)
app.include_router(afk.router)
app.include_router(market.router)
app.include_router(guild.router)
app.include_router(world_boss.router)

@app.get("/health")
async def health():
    return {"status": "ok"}