from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.item import ItemInstance, MarketListing
from app.models.character import Character
from app.schemas.market import CreateListingRequest, ListingResponse, PurchaseRequest
import uuid

router = APIRouter(prefix="/api/v1/market", tags=["market"])

MARKET_TAX_RATE      = 0.05   # 5% thuế
MAX_ACTIVE_LISTINGS  = 20     # Tối đa 20 listing mỗi nhân vật
LISTING_EXPIRE_DAYS  = 7

RARITY_MIN_PRICE = {
    "COMMON"    : 100,
    "UNCOMMON"  : 500,
    "RARE"      : 2_000,
    "EPIC"      : 10_000,
    "LEGENDARY" : 100_000,
    "MYTHIC"    : 1_000_000,
    "ANCIENT"   : 10_000_000,
}

@router.get("/search", response_model=list[ListingResponse])
async def search_listings(
    item_type:  str  = None,
    rarity:     str  = None,
    min_price:  int  = None,
    max_price:  int  = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = select(MarketListing).where(MarketListing.status == "ACTIVE")

    if item_type:
        query = query.where(MarketListing.item_type == item_type.upper())
    if rarity:
        query = query.where(MarketListing.rarity == rarity.upper())
    if min_price:
        query = query.where(MarketListing.price_gold >= min_price)
    if max_price:
        query = query.where(MarketListing.price_gold <= max_price)

    query  = query.order_by(MarketListing.price_gold.asc()).limit(50)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/list", response_model=ListingResponse)
async def list_item(
    body: CreateListingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Lấy character
    character = await _get_character(db, body.character_id, current_user["sub"])

    # Lấy item — phải thuộc về character này
    item_result = await db.execute(
        select(ItemInstance).where(
            ItemInstance.id       == body.item_instance_id,
            ItemInstance.owner_id == character.id,
        )
    )
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item not found")
    if item.is_bound:
        raise HTTPException(400, "Item is bound and cannot be traded")
    if item.is_equipped:
        raise HTTPException(400, "Unequip item before listing")
    if item.is_in_market:
        raise HTTPException(400, "Item is already listed")

    # Kiểm tra giá sàn
    min_price = RARITY_MIN_PRICE.get(item.rarity, 100)
    if body.price_gold < min_price:
        raise HTTPException(400, f"Minimum price for {item.rarity} is {min_price} gold")

    # Kiểm tra số listing đang active
    count_result = await db.execute(
        select(MarketListing).where(
            MarketListing.seller_id == character.id,
            MarketListing.status    == "ACTIVE",
        )
    )
    if len(count_result.scalars().all()) >= MAX_ACTIVE_LISTINGS:
        raise HTTPException(400, f"Maximum {MAX_ACTIVE_LISTINGS} active listings reached")

    # Tạo listing
    listing = MarketListing(
        id               = uuid.uuid4(),
        seller_id        = character.id,
        item_instance_id = item.id,
        price_gold       = body.price_gold,
        item_name        = item.item_name,
        item_type        = item.item_type,
        rarity           = item.rarity,
        enhance_level    = item.enhance_level,
        expires_at       = datetime.now(timezone.utc) + timedelta(days=LISTING_EXPIRE_DAYS),
    )
    item.is_in_market = True

    db.add(listing)
    await db.commit()
    await db.refresh(listing)
    return listing


@router.post("/buy")
async def buy_item(
    body: PurchaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    buyer = await _get_character(db, body.character_id, current_user["sub"])

    # Lấy listing
    listing_result = await db.execute(
        select(MarketListing).where(
            MarketListing.id     == body.listing_id,
            MarketListing.status == "ACTIVE",
        )
    )
    listing = listing_result.scalar_one_or_none()
    if not listing:
        raise HTTPException(404, "Listing not found or already sold")
    if str(listing.seller_id) == str(buyer.id):
        raise HTTPException(400, "Cannot buy your own listing")

    # Kiểm tra Gold đủ không
    if buyer.gold < listing.price_gold:
        raise HTTPException(400, f"Not enough gold. Need {listing.price_gold}, have {buyer.gold}")

    # Lấy seller
    seller_result = await db.execute(
        select(Character).where(Character.id == listing.seller_id)
    )
    seller = seller_result.scalar_one_or_none()

    # Lấy item
    item_result = await db.execute(
        select(ItemInstance).where(ItemInstance.id == listing.item_instance_id)
    )
    item = item_result.scalar_one_or_none()

    # Atomic: trừ gold buyer, cộng gold seller (trừ thuế), transfer item
    tax          = int(listing.price_gold * MARKET_TAX_RATE)
    seller_gets  = listing.price_gold - tax

    buyer.gold  -= listing.price_gold
    seller.gold += seller_gets

    item.owner_id    = buyer.id
    item.is_in_market = False

    listing.status = "SOLD"

    await db.commit()

    return {
        "message"     : "Purchase successful",
        "item_name"   : item.item_name,
        "price_paid"  : listing.price_gold,
        "tax"         : tax,
        "seller_got"  : seller_gets,
    }


@router.delete("/listing/{listing_id}")
async def cancel_listing(
    listing_id:   str,
    character_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    character = await _get_character(db, character_id, current_user["sub"])

    listing_result = await db.execute(
        select(MarketListing).where(
            MarketListing.id        == listing_id,
            MarketListing.seller_id == character.id,
            MarketListing.status    == "ACTIVE",
        )
    )
    listing = listing_result.scalar_one_or_none()
    if not listing:
        raise HTTPException(404, "Listing not found")

    # Hoàn trả item
    item_result = await db.execute(
        select(ItemInstance).where(ItemInstance.id == listing.item_instance_id)
    )
    item = item_result.scalar_one_or_none()
    if item:
        item.is_in_market = False

    listing.status = "CANCELLED"
    await db.commit()
    return {"message": "Listing cancelled, item returned to inventory"}


@router.get("/my-listings", response_model=list[ListingResponse])
async def my_listings(
    character_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    character = await _get_character(db, character_id, current_user["sub"])
    result    = await db.execute(
        select(MarketListing).where(
            MarketListing.seller_id == character.id,
            MarketListing.status    == "ACTIVE",
        )
    )
    return result.scalars().all()


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
@router.post("/dev/add-test-item")
async def add_test_item(
    character_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Endpoint tạm để test — xóa trước khi production"""
    character = await _get_character(db, character_id, current_user["sub"])

    item = ItemInstance(
        id            = uuid.uuid4(),
        owner_id      = character.id,
        definition_id = "WP_R_0001",
        item_name     = "Iron Sword",
        item_type     = "WEAPON",
        rarity        = "RARE",
        enhance_level = 0,
        is_bound      = False,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"item_id": str(item.id), "item_name": item.item_name}