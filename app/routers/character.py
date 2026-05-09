from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.character import Character
from app.schemas.character import CreateCharacterRequest, CharacterResponse
from datetime import datetime, timezone
        
import uuid

router = APIRouter(prefix="/api/v1/character", tags=["character"])

VALID_CLASSES = [
    "WARRIOR", "GUARDIAN", "RANGER", "PYROMANCER",
    "ROGUE", "FOREST_SPIRIT", "WIZARD", "PRIEST", "WIND_SPIRIT"
]

@router.post("", response_model=CharacterResponse)
async def create_character(
    body: CreateCharacterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Validate class
    if body.class_id not in VALID_CLASSES:
        raise HTTPException(400, f"Invalid class. Choose from: {VALID_CLASSES}")

    # Mỗi user tối đa 3 nhân vật
    result = await db.execute(
        select(Character).where(Character.user_id == current_user["sub"])
    )
    existing = result.scalars().all()
    if len(existing) >= 3:
        raise HTTPException(400, "Maximum 3 characters per account")

    character = Character(
        id       = uuid.uuid4(),
        user_id  = current_user["sub"],
        name     = body.name,
        class_id = body.class_id,
    )
    db.add(character)
    await db.commit()
    await db.refresh(character)
    return character

@router.get("/me", response_model=list[CharacterResponse])
async def get_my_characters(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Character).where(Character.user_id == current_user["sub"])
    )
    return result.scalars().all()

@router.patch("/map")
async def change_map(
    map_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Character).where(Character.user_id == current_user["sub"])
    )
    character = result.scalars().first()
    if not character:
        raise HTTPException(404, "Character not found")

    character.current_map_id = map_id
    await db.commit()
    return {"map_id": map_id}

@router.post("/logout")
async def character_logout(
    character_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Character).where(
            Character.id == character_id,
            Character.user_id == current_user["sub"]
        )
    )
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(404, "Character not found")

    character.last_logout_timestamp = int(datetime.now(timezone.utc).timestamp())
    await db.commit()
    return {"logged_out_at": character.last_logout_timestamp}