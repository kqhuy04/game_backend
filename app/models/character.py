from sqlalchemy import Column, String, Integer, BigInteger, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base

class Character(Base):
    __tablename__ = "characters"

    id                       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id                  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name                     = Column(String(20), nullable=False)
    class_id                 = Column(String(20), nullable=False)
    level                    = Column(Integer, default=1)
    soul_level               = Column(Integer, default=0)
    current_exp              = Column(BigInteger, default=0)
    gold                     = Column(BigInteger, default=0)
    gems                     = Column(Integer, default=0)
    current_map_id           = Column(Integer, default=1)
    last_logout_timestamp    = Column(BigInteger, nullable=True)
    last_afk_claim_timestamp = Column(BigInteger, nullable=True)
    legendary_pity_counter   = Column(Integer, default=0)
    mythic_pity_counter      = Column(Integer, default=0)
    created_at               = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="characters")