from sqlalchemy import Column, String, Integer, BigInteger, Boolean, DateTime, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base

class Guild(Base):
    __tablename__ = "guilds"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name              = Column(String(30), unique=True, nullable=False)
    description       = Column(Text, default="")
    leader_id         = Column(UUID(as_uuid=True), ForeignKey("characters.id"), nullable=False)
    level             = Column(Integer, default=1)
    max_members       = Column(Integer, default=20)
    contribution_pool = Column(BigInteger, default=0)  # Tổng contribution coins
    created_at        = Column(DateTime(timezone=True), server_default=func.now())

    members = relationship("GuildMember", back_populates="guild")


class GuildMember(Base):
    __tablename__ = "guild_members"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guild_id     = Column(UUID(as_uuid=True), ForeignKey("guilds.id"), nullable=False)
    character_id = Column(UUID(as_uuid=True), ForeignKey("characters.id"), nullable=False)
    role         = Column(String(20), default="MEMBER")  # LEADER, OFFICER, MEMBER
    contribution = Column(BigInteger, default=0)         # Contribution coins cá nhân
    joined_at    = Column(DateTime(timezone=True), server_default=func.now())

    guild = relationship("Guild", back_populates="members")