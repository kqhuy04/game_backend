from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.world_boss import WorldBoss, WorldBossParticipant
from app.models.character import Character
import uuid, random

router = APIRouter(prefix="/api/v1/world-boss", tags=["world-boss"])
async def _get_active_boss(db) -> WorldBoss | None:
    now    = datetime.now(timezone.utc)
    result = await db.execute(
        select(WorldBoss).where(
            WorldBoss.is_alive     == True,
            WorldBoss.spawn_time   <= now,
            WorldBoss.despawn_time >= now,
        )
    )
    return result.scalar_one_or_none()


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
    return character


async def _get_damage_rank(db, boss_id, character_id) -> int:
    result = await db.execute(
        select(WorldBossParticipant)
        .where(WorldBossParticipant.boss_id == boss_id)
        .order_by(WorldBossParticipant.total_damage.desc())
    )
    participants = result.scalars().all()
    for i, p in enumerate(participants):
        if str(p.character_id) == str(character_id):
            return i + 1
    return 999

# Lịch spawn: 8:00, 12:00, 20:00 server time
SPAWN_HOURS     = [8, 12, 20]
BOSS_DURATION   = timedelta(hours=1)
ATTACK_COOLDOWN = 5  # giây giữa 2 lần attack

# Reward tiers
REWARD_TIERS = {
    "gold": {"exp": 5000,  "gold": 3000},   # top 3
    "silver": {"exp": 2000, "gold": 1200},  # top 4-10
    "bronze": {"exp": 500,  "gold": 300},   # tham gia
}


@router.get("/schedule")
async def get_schedule():
    """Lịch spawn World Boss hôm nay"""
    now    = datetime.now(timezone.utc)
    today  = now.date()
    spawns = []
    for hour in SPAWN_HOURS:
        spawn_time   = datetime(today.year, today.month, today.day, hour, 0, 0, tzinfo=timezone.utc)
        despawn_time = spawn_time + BOSS_DURATION
        spawns.append({
            "spawn_time"  : spawn_time.isoformat(),
            "despawn_time": despawn_time.isoformat(),
            "is_active"   : spawn_time <= now <= despawn_time,
        })
    return {"schedule": spawns}


@router.get("/current")
async def get_current_boss(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Lấy World Boss đang active"""
    boss = await _get_active_boss(db)
    if not boss:
        raise HTTPException(404, "No active World Boss right now")

    # Đếm số người tham gia
    count = await db.execute(
        select(func.count()).where(WorldBossParticipant.boss_id == boss.id)
    )
    return {
        "id"          : str(boss.id),
        "name"        : boss.name,
        "max_hp"      : boss.max_hp,
        "current_hp"  : boss.current_hp,
        "hp_percent"  : round(boss.current_hp / boss.max_hp * 100, 1),
        "level"       : boss.level,
        "despawn_time": boss.despawn_time.isoformat(),
        "participants": count.scalar(),
    }


@router.post("/join")
async def join_boss(
    character_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    character = await _get_character(db, character_id, current_user["sub"])
    boss      = await _get_active_boss(db)
    if not boss:
        raise HTTPException(404, "No active World Boss right now")

    # Kiểm tra đã join chưa
    existing = await db.execute(
        select(WorldBossParticipant).where(
            WorldBossParticipant.boss_id      == boss.id,
            WorldBossParticipant.character_id == character.id,
        )
    )
    if existing.scalar_one_or_none():
        return {"message": "Already joined", "boss_id": str(boss.id)}

    participant = WorldBossParticipant(
        id           = uuid.uuid4(),
        boss_id      = boss.id,
        character_id = character.id,
    )
    db.add(participant)
    await db.commit()
    return {"message": f"Joined fight against {boss.name}!", "boss_id": str(boss.id)}


@router.post("/attack")
async def attack_boss(
    character_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    character = await _get_character(db, character_id, current_user["sub"])
    boss      = await _get_active_boss(db)
    if not boss:
        raise HTTPException(404, "No active World Boss")

    # Lấy participant record
    part_result = await db.execute(
        select(WorldBossParticipant).where(
            WorldBossParticipant.boss_id      == boss.id,
            WorldBossParticipant.character_id == character.id,
        )
    )
    participant = part_result.scalar_one_or_none()
    if not participant:
        raise HTTPException(400, "Join the boss fight first")

    # Cooldown check
    now = datetime.now(timezone.utc)
    if participant.last_attack_at:
        last = participant.last_attack_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if (now - last).total_seconds() < ATTACK_COOLDOWN:
            wait = ATTACK_COOLDOWN - int((now - last).total_seconds())
            raise HTTPException(429, f"Attack cooldown: wait {wait}s")

    # Tính damage dựa vào stats nhân vật
    base_dmg  = character.level * 100
    damage    = random.randint(int(base_dmg * 0.8), int(base_dmg * 1.2))
    damage    = min(damage, boss.current_hp)  # Không damage quá HP còn lại

    # Cập nhật boss HP
    boss.current_hp         -= damage
    participant.total_damage += damage
    participant.last_attack_at = now

    if boss.current_hp <= 0:
        boss.current_hp = 0
        boss.is_alive   = False
        boss.killed_at  = now

    await db.commit()
    return {
        "damage_dealt": damage,
        "boss_hp_remaining": boss.current_hp,
        "boss_defeated": not boss.is_alive,
        "your_total_damage": participant.total_damage,
    }


@router.post("/claim-reward")
async def claim_reward(
    character_id: str,
    boss_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    character = await _get_character(db, character_id, current_user["sub"])

    # Lấy boss
    boss_result = await db.execute(select(WorldBoss).where(WorldBoss.id == boss_id))
    boss        = boss_result.scalar_one_or_none()
    if not boss:
        raise HTTPException(404, "Boss not found")
    if boss.is_alive:
        raise HTTPException(400, "Boss is still alive")

    # Lấy participant
    part_result = await db.execute(
        select(WorldBossParticipant).where(
            WorldBossParticipant.boss_id      == boss.id,
            WorldBossParticipant.character_id == character.id,
        )
    )
    participant = part_result.scalar_one_or_none()
    if not participant:
        raise HTTPException(400, "Did not participate in this boss")
    if participant.reward_claimed:
        raise HTTPException(400, "Reward already claimed")

    # Xác định tier reward dựa vào rank
    rank   = await _get_damage_rank(db, boss.id, character.id)
    tier   = "gold" if rank <= 3 else "silver" if rank <= 10 else "bronze"
    reward = REWARD_TIERS[tier]

    character.current_exp += reward["exp"]
    character.gold        += reward["gold"]
    participant.reward_claimed = True

    await db.commit()
    return {
        "rank"      : rank,
        "tier"      : tier,
        "exp_gained": reward["exp"],
        "gold_gained": reward["gold"],
        "total_damage": participant.total_damage,
    }


@router.get("/leaderboard/{boss_id}")
async def get_leaderboard(
    boss_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(WorldBossParticipant, Character)
        .join(Character, WorldBossParticipant.character_id == Character.id)
        .where(WorldBossParticipant.boss_id == boss_id)
        .order_by(WorldBossParticipant.total_damage.desc())
        .limit(20)
    )
    rows = result.all()
    return [
        {
            "rank"          : i + 1,
            "character_name": c.name,
            "total_damage"  : p.total_damage,
            "reward_tier"   : "gold" if i < 3 else "silver" if i < 10 else "bronze",
        }
        for i, (p, c) in enumerate(rows)
    ]


@router.post("/dev/spawn")
async def dev_spawn_boss(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Endpoint tạm để spawn boss test — xóa trước production"""
    now  = datetime.now(timezone.utc)
    boss = WorldBoss(
        id           = uuid.uuid4(),
        name         = "Ancient Dragon",
        level        = 50,
        max_hp       = 1_000_000,
        current_hp   = 1_000_000,
        spawn_time   = now,
        despawn_time = now + BOSS_DURATION,
    )
    db.add(boss)
    await db.commit()
    await db.refresh(boss)
    return {"boss_id": str(boss.id), "name": boss.name, "hp": boss.max_hp}


# ── Helpers ───────────────────────────────────────────────

