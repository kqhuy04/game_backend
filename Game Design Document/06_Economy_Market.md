# 06 — Economy & Market System
> **GDD TinyWorld Clone** | Kinh tế & Giao dịch Tự do

---

## 1. Tiền Tệ

| Tiền tệ | Ký hiệu | Cách kiếm | Dùng để |
|---|---|---|---|
| **Gold** | 💰 | Đánh quái AFK, bán item NPC | Mua đồ từ NPC, phí forge, chợ |
| **Gems** (Soul Gems) | 💎 | Rơi từ Elite/Boss, Daily Quest | Mở rộng túi đồ, Unbind Scroll, Battle Pass |
| **Magic Crystals** | 🔮 | Guild Boss, Dimensional Rift | Gamble (ra Yang Crystal) hoặc bán chợ |
| **Yang Crystals** | ✨ | Gamble từ Magic Crystal | Mua item đặc biệt từ Guild Shop |
| **Contribution Coins** | 🏅 | Guild Dungeon | Guild Shop (trang bị Guild) |

### Quy tắc cơ bản
- **Gold**: kiếm offline tự do, lạm phát được kiểm soát bằng thuế giao dịch (5%)
- **Gems**: nguồn cung giới hạn — không in ra tùy ý
- **Không có tỷ giá Gold ↔ Gems cố định** — chợ tự điều chỉnh

---

## 2. Chợ Giao Dịch (Free Market)

### Luồng Đăng Bán

```
Người bán                          Server
  |                                  |
  | Chọn item từ Inventory           |
  | → Nhập giá (Gold/Gems)           |
  | → POST /market/list              |
  |--------------------------------->|
  |                                  | VALIDATE:
  |                                  |  - Item tồn tại và thuộc về người bán?
  |                                  |  - Item là Unbound?
  |                                  |  - Giá nằm trong [min_price, max_price]?
  |                                  |  - Người bán không vượt giới hạn slot niêm yết (20)?
  |<-- 201 Created ------------------|
  |    { listing_id, expires_at }    |
  
  Item bị LOCK khỏi Inventory người bán
  Listing hết hạn sau 7 ngày → tự động hoàn trả item
```

### Luồng Mua

```
Người mua                          Server
  |                                  |
  | Tìm kiếm listing                 |
  | → GET /market/search?...         |
  |<-- 200 [{listing_id, price}] ----|
  |                                  |
  | Chọn listing, xác nhận mua       |
  | → POST /market/buy               |
  |--------------------------------->|
  |                                  | ATOMIC TRANSACTION:
  |                                  |  1. Lock listing (prevent double-buy)
  |                                  |  2. Kiểm tra Gold người mua đủ không
  |                                  |  3. Trừ Gold người mua
  |                                  |  4. Cộng Gold người bán (trừ 5% thuế)
  |                                  |  5. Transfer item → inventory người mua
  |                                  |  6. Xóa listing
  |<-- 200 OK ----------------------|
  |    { item_instance, receipt }    |
```

### Market Listing Data Model

```python
# models/market.py
class MarketListing(Base):
    __tablename__ = "market_listings"
    
    id              = Column(UUID, primary_key=True, default=uuid4)
    seller_id       = Column(UUID, ForeignKey("characters.id"))
    item_instance_id= Column(UUID, ForeignKey("item_instances.id"))
    price_gold      = Column(BigInteger, nullable=True)
    price_gems      = Column(Integer, nullable=True)
    listed_at       = Column(DateTime(timezone=True), default=func.now())
    expires_at      = Column(DateTime(timezone=True))        # +7 ngày
    status          = Column(Enum(ListingStatus))            # ACTIVE, SOLD, CANCELLED, EXPIRED
    
    # Denormalized để tìm kiếm nhanh (không cần JOIN)
    item_name       = Column(String)
    item_type       = Column(String)
    rarity          = Column(String)
    enhance_level   = Column(Integer)
```

---

## 3. Price Control (Kiểm soát Giá)

```python
# services/market_service.py

# Giới hạn giá để chống bot spam
MIN_PRICE_GOLD  = 100
MAX_PRICE_GOLD  = 999_999_999   # ~1 tỷ Gold

# Giá sàn theo rarity (tránh phá giá)
RARITY_MIN_PRICE = {
    "COMMON"    : 100,
    "UNCOMMON"  : 500,
    "RARE"      : 2_000,
    "EPIC"      : 10_000,
    "LEGENDARY" : 100_000,
    "MYTHIC"    : 1_000_000,
    "ANCIENT"   : 10_000_000,
}

# Thuế giao dịch
MARKET_TAX_RATE = 0.05   # 5% → vào quỹ "sink" Gold

def validate_listing_price(item_rarity: str, price: int) -> bool:
    min_price = RARITY_MIN_PRICE.get(item_rarity, MIN_PRICE_GOLD)
    return min_price <= price <= MAX_PRICE_GOLD
```

---

## 4. Tìm Kiếm & Lọc Chợ

```python
# schemas/market.py
class MarketSearchQuery(BaseModel):
    item_type    : Optional[str]         # "WEAPON", "ARMOR", ...
    item_name    : Optional[str]         # search text
    rarity       : Optional[list[str]]   # ["EPIC", "LEGENDARY"]
    min_price    : Optional[int]
    max_price    : Optional[int]
    min_enhance  : Optional[int]
    sort_by      : str = "price_asc"     # "price_asc", "price_desc", "newest"
    page         : int = 1
    page_size    : int = 20

# Endpoint
@router.get("/market/search")
async def search_market(query: MarketSearchQuery = Depends()):
    ...
```

---

## 5. Item Binding & Unlock

```
Bound rules (xem chi tiết ở file 03):

API endpoint để Unbind:
  POST /item/unbind
  Body: { item_instance_id, scroll_id }

  Server:
    1. Kiểm tra scroll_id là "Unbind Scroll" hợp lệ trong inventory
    2. Kiểm tra item là Bound
    3. Xóa scroll → set item.is_bound = false
    4. Commit
```

---

## 6. Rate Limit Giao Dịch (Anti-bot / Anti-exploit)

```python
# Giới hạn mỗi nhân vật
MAX_ACTIVE_LISTINGS     = 20    # Số listing đang active tối đa
MAX_LISTINGS_PER_HOUR   = 30    # Không đăng bán quá 30 lần/giờ
MAX_PURCHASES_PER_HOUR  = 50    # Không mua quá 50 lần/giờ

# Implement bằng Redis
async def check_rate_limit(char_id: str, action: str) -> bool:
    key   = f"rate:{action}:{char_id}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 3600)  # TTL = 1 giờ
    
    limits = {
        "list"     : MAX_LISTINGS_PER_HOUR,
        "purchase" : MAX_PURCHASES_PER_HOUR,
    }
    return count <= limits[action]
```

---

## 7. Market History & Price Chart

```python
# Lưu lịch sử giao dịch để hiển thị biểu đồ giá
class MarketTransaction(Base):
    __tablename__ = "market_transactions"
    
    id              = Column(UUID, primary_key=True)
    item_definition_id = Column(String)   # Template ID (không phải instance)
    rarity          = Column(String)
    enhance_level   = Column(Integer)
    sold_price      = Column(BigInteger)
    sold_at         = Column(DateTime(timezone=True))

# API trả về lịch sử 7 ngày
@router.get("/market/price-history/{item_def_id}")
async def price_history(item_def_id: str, rarity: str, enhance: int = 0):
    # Trả về list (timestamp, avg_price, min_price, max_price) theo ngày
    ...
```

---

## 8. Unity Market UI Client

```csharp
// MarketAPIClient.cs
public class MarketAPIClient : MonoBehaviour
{
    private const string BASE = "/api/v1/market";

    public async Task<List<MarketListing>> SearchListings(MarketSearchQuery query)
    {
        string qs = query.ToQueryString();
        return await APIClient.Get<List<MarketListing>>($"{BASE}/search?{qs}");
    }

    public async Task<MarketListing> ListItem(string instanceId, long price)
    {
        return await APIClient.Post<MarketListing>($"{BASE}/list", new {
            item_instance_id = instanceId,
            price_gold       = price,
        });
    }

    public async Task<PurchaseReceipt> BuyItem(string listingId)
    {
        return await APIClient.Post<PurchaseReceipt>($"{BASE}/buy", new {
            listing_id = listingId,
        });
    }

    public async Task CancelListing(string listingId)
    {
        await APIClient.Delete($"{BASE}/listing/{listingId}");
    }
}
```
