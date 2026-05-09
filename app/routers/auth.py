from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
import uuid

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Kiểm tra username đã tồn tại chưa
    result = await db.execute(select(User).where(User.username == body.username))
    if result.scalar_one_or_none():
        raise HTTPException(400, "Username already exists")

    user = User(
        id            = uuid.uuid4(),
        username      = body.username,
        email         = body.email,
        password_hash = hash_password(body.password),
    )
    db.add(user)
    await db.commit()

    payload = {"sub": str(user.id), "username": user.username}
    return TokenResponse(
        access_token  = create_access_token(payload),
        refresh_token = create_refresh_token(payload),
    )

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == body.username))
    user   = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid username or password")

    payload = {"sub": str(user.id), "username": user.username}
    return TokenResponse(
        access_token  = create_access_token(payload),
        refresh_token = create_refresh_token(payload),
    )