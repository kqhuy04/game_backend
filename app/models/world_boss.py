from sqlalchemy import Column, String, Integer, BigInteger, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base

class WorldBoss(Base):
    __tablename__ = "world_bosses"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name            = Column(String(50), nullable=False)
    max_hp          = Column(BigInteger, nullable=False)
    current_hp      = Column(BigInteger, nullable=False)
    level           = Column(Integer, nullable=False)
    is_alive        = Column(Boolean, default=True)
    spawn_time      = Column(DateTime(timezone=True), nullable=False)
    despawn_time    = Column(DateTime(timezone=True), nullable=False)  # +1 giờ
    killed_at       = Column(DateTime(timezone=True), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())


class WorldBossParticipant(Base):
    __tablename__ = "world_boss_participants"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    boss_id         = Column(UUID(as_uuid=True), ForeignKey("world_bosses.id"), nullable=False)
    character_id    = Column(UUID(as_uuid=True), ForeignKey("characters.id"), nullable=False)
    total_damage    = Column(BigInteger, default=0)
    last_attack_at  = Column(DateTime(timezone=True), nullable=True)
    reward_claimed  = Column(Boolean, default=False)