from sqlalchemy import Column, String, Integer, BigInteger, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base

class ItemInstance(Base):
    __tablename__ = "item_instances"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id       = Column(UUID(as_uuid=True), ForeignKey("characters.id"), nullable=False)
    definition_id  = Column(String(20), nullable=False)
    item_name      = Column(String(100), nullable=False)
    item_type      = Column(String(20), nullable=False)   # WEAPON, ARMOR, ...
    rarity         = Column(String(20), nullable=False)   # COMMON, RARE, ...
    enhance_level  = Column(Integer, default=0)
    is_bound       = Column(Boolean, default=False)
    is_equipped    = Column(Boolean, default=False)
    is_in_market   = Column(Boolean, default=False)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())


class MarketListing(Base):
    __tablename__ = "market_listings"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id        = Column(UUID(as_uuid=True), ForeignKey("characters.id"), nullable=False)
    item_instance_id = Column(UUID(as_uuid=True), ForeignKey("item_instances.id"), nullable=False)
    price_gold       = Column(BigInteger, nullable=False)
    item_name        = Column(String(100), nullable=False)
    item_type        = Column(String(20), nullable=False)
    rarity           = Column(String(20), nullable=False)
    enhance_level    = Column(Integer, default=0)
    listed_at        = Column(DateTime(timezone=True), server_default=func.now())
    expires_at       = Column(DateTime(timezone=True), nullable=False)
    status           = Column(String(20), default="ACTIVE")  # ACTIVE, SOLD, CANCELLED