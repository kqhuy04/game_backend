from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.guild import Guild, GuildMember
from app.models.character import Character
from app.schemas.guild import CreateGuildRequest, GuildResponse, JoinGuildRequest
import uuid

router = APIRouter(prefix="/api/v1/guild", tags=["guild"])

GUILD_CREATE_COST = 10_000  # Gold để tạo guild


@router.post("", response_model=GuildResponse)
async def create_guild(
    body: CreateGuildRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    character = await _get_character(db, body.character_id, current_user["sub"])

    # Kiểm tra đã có guild chưa
    existing = await db.execute(
        select(GuildMember).where(GuildMember.character_id == character.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Already in a guild — leave first")

    # Kiểm tra tên guild trùng
    name_check = await db.execute(
        select(Guild).where(Guild.name == body.name)
    )
    if name_check.scalar_one_or_none():
        raise HTTPException(400, "Guild name already taken")

    # Trừ gold
    if character.gold < GUILD_CREATE_COST:
        raise HTTPException(400, f"Need {GUILD_CREATE_COST} gold to create a guild")
    character.gold -= GUILD_CREATE_COST

    # Tạo guild
    guild = Guild(
        id          = uuid.uuid4(),
        name        = body.name,
        description = body.description,
        leader_id   = character.id,
    )
    db.add(guild)
    await db.flush()  # Cần guild.id trước khi tạo member

    # Leader tự động join
    member = GuildMember(
        id           = uuid.uuid4(),
        guild_id     = guild.id,
        character_id = character.id,
        role         = "LEADER",
    )
    db.add(member)
    await db.commit()
    await db.refresh(guild)

    return {**guild.__dict__, "member_count": 1}


@router.get("/{guild_id}", response_model=GuildResponse)
async def get_guild(
    guild_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Guild).where(Guild.id == guild_id))
    guild  = result.scalar_one_or_none()
    if not guild:
        raise HTTPException(404, "Guild not found")

    count  = await db.execute(
        select(func.count()).where(GuildMember.guild_id == guild.id)
    )
    return {**guild.__dict__, "member_count": count.scalar()}


@router.post("/join")
async def join_guild(
    body: JoinGuildRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    character = await _get_character(db, body.character_id, current_user["sub"])

    # Kiểm tra đã có guild chưa
    existing = await db.execute(
        select(GuildMember).where(GuildMember.character_id == character.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Already in a guild")

    # Kiểm tra guild tồn tại và còn chỗ
    guild_result = await db.execute(select(Guild).where(Guild.id == body.guild_id))
    guild        = guild_result.scalar_one_or_none()
    if not guild:
        raise HTTPException(404, "Guild not found")

    count = await db.execute(
        select(func.count()).where(GuildMember.guild_id == guild.id)
    )
    if count.scalar() >= guild.max_members:
        raise HTTPException(400, "Guild is full")

    member = GuildMember(
        id           = uuid.uuid4(),
        guild_id     = guild.id,
        character_id = character.id,
        role         = "MEMBER",
    )
    db.add(member)
    await db.commit()
    return {"message": f"Joined guild {guild.name}"}


@router.post("/leave")
async def leave_guild(
    character_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    character = await _get_character(db, character_id, current_user["sub"])

    member_result = await db.execute(
        select(GuildMember).where(GuildMember.character_id == character.id)
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(400, "Not in a guild")
    if member.role == "LEADER":
        raise HTTPException(400, "Leader cannot leave — transfer leadership first")

    await db.delete(member)
    await db.commit()
    return {"message": "Left guild"}


@router.get("/{guild_id}/members")
async def get_members(
    guild_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(GuildMember, Character)
        .join(Character, GuildMember.character_id == Character.id)
        .where(GuildMember.guild_id == guild_id)
        .order_by(GuildMember.contribution.desc())
    )
    rows = result.all()
    return [
        {
            "character_id"  : str(m.character_id),
            "character_name": c.name,
            "role"          : m.role,
            "contribution"  : m.contribution,
            "joined_at"     : m.joined_at,
        }
        for m, c in rows
    ]


# ── Helper ────────────────────────────────────────────────

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