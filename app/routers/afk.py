from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.character import Character
import random

router = APIRouter(prefix="/api/v1/afk", tags=["afk"])

MAX_AFK_SECONDS    = 3 * 3600   # 3 giờ
AFK_CLAIM_COOLDOWN = 60          # giây

# Bảng reward đơn giản theo map (sẽ mở rộng sau)
MAP_REWARDS = {
    1: {"exp_per_min": 50,  "gold_per_min": 30},
    2: {"exp_per_min": 120, "gold_per_min": 80},
    3: {"exp_per_min": 250, "gold_per_min": 170},
    4: {"exp_per_min": 500, "gold_per_min": 350},
    5: {"exp_per_min": 900, "gold_per_min": 600},
}

@router.get("/preview")
async def preview_afk_reward(
    character_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Xem trước reward mà không nhận — dùng để hiển thị UI"""
    character = await _get_character(db, character_id, current_user["sub"])
    reward = _calculate_reward(character)
    return reward

@router.post("/claim")
async def claim_afk_reward(
    character_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    character = await _get_character(db, character_id, current_user["sub"])
    server_now = int(datetime.now(timezone.utc).timestamp())

    # Rate limit: không claim liên tục
    if character.last_afk_claim_timestamp:
        since_last = server_now - character.last_afk_claim_timestamp
        if since_last < AFK_CLAIM_COOLDOWN:
            raise HTTPException(429, f"Wait {AFK_CLAIM_COOLDOWN - since_last}s before claiming again")

    reward = _calculate_reward(character)

    # Áp dụng reward vào nhân vật
    character.current_exp              += reward["total_exp"]
    character.gold                     += reward["total_gold"]
    character.last_afk_claim_timestamp  = server_now
    character.last_logout_timestamp     = server_now  # reset timer

    # Level up nếu đủ EXP
    character.level = _calculate_level(character.current_exp)

    await db.commit()
    await db.refresh(character)

    return {
        **reward,
        "new_level"  : character.level,
        "new_exp"    : character.current_exp,
        "new_gold"   : character.gold,
    }

# ── Helpers ──────────────────────────────────────────────

async def _get_character(db, character_id: str, user_id: str) -> Character:
    result = await db.execute(
        select(Character).where(
            Character.id      == character_id,
            Character.user_id == user_id,
        )
    )
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(404, "Character not found")
    if not character.last_logout_timestamp:
        raise HTTPException(400, "No offline session found — call /character/logout first")
    return character

def _calculate_reward(character: Character) -> dict:
    server_now  = int(datetime.now(timezone.utc).timestamp())
    delta_sec   = server_now - character.last_logout_timestamp
    capped_sec  = min(delta_sec, MAX_AFK_SECONDS)
    was_capped  = delta_sec > MAX_AFK_SECONDS
    minutes     = capped_sec / 60.0

    map_data    = MAP_REWARDS.get(character.current_map_id, MAP_REWARDS[1])
    exp_bonus   = 1.0   # sẽ dùng equipment bonus sau
    gold_bonus  = 1.0

    total_exp   = int(map_data["exp_per_min"]  * minutes * exp_bonus)
    total_gold  = int(map_data["gold_per_min"] * minutes * gold_bonus)

    return {
        "offline_seconds" : capped_sec,
        "offline_minutes" : round(minutes, 1),
        "was_capped"      : was_capped,
        "total_exp"       : total_exp,
        "total_gold"      : total_gold,
    }

def _calculate_level(total_exp: int) -> int:
    """Tính level từ tổng EXP tích lũy"""
    level = 1
    while True:
        exp_needed = int(100 * (level ** 1.8))
        if total_exp < exp_needed:
            break
        total_exp -= exp_needed
        level     += 1
        if level >= 999:
            break
    return level