from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime

class CreateListingRequest(BaseModel):
    character_id:     str
    item_instance_id: str
    price_gold:       int

class ListingResponse(BaseModel):
    id:               UUID
    seller_id:        UUID
    item_instance_id: UUID
    price_gold:       int
    item_name:        str
    item_type:        str
    rarity:           str
    enhance_level:    int
    listed_at:        datetime
    expires_at:       datetime
    status:           str

    class Config:
        from_attributes = True

class PurchaseRequest(BaseModel):
    character_id: str
    listing_id:   str