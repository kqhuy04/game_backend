# 07 — Server Architecture
> **GDD TinyWorld Clone** | Kiến trúc Máy chủ & API Design

---

## 1. Tổng quan Kiến trúc

```
┌─────────────────────────────────────────────────────────┐
│                    MOBILE CLIENT (Unity)                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │ GameMgr  │  │ AFKMgr   │  │ MarketUI │  │ AuthUI │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───┬────┘  │
│       └─────────────┴─────────────┴─────────────┘       │
│                         APIClient (C#)                   │
└───────────────────────────┬─────────────────────────────┘
                            │ HTTPS / REST
                            ▼
                    ┌───────────────┐
                    │   Cloudflare  │  ← CDN, DDoS protect, Rate Limit
                    └───────┬───────┘
                            │
                    ┌───────▼───────┐
                    │  FastAPI App  │  ← Uvicorn + Gunicorn workers
                    │  (Python 3.11)│
                    └───┬───────┬───┘
                        │       │
              ┌─────────▼─┐  ┌──▼──────────┐
              │ PostgreSQL │  │   Redis 7   │
              │    (main)  │  │  (cache,    │
              │            │  │  sessions,  │
              └────────────┘  │  rate limit)│
                              └─────────────┘
                              
              ┌───────────────────────┐
              │  Celery Worker        │  ← Tính AFK batch, cleanup tasks
              │  (Redis broker)       │
              └───────────────────────┘
```

---

## 2. Authentication Flow

### 2.1 Register / Login
```
POST /api/v1/auth/register
Body: { username, email, password }
→ Server hash password (bcrypt)
→ Tạo account + character mặc định
→ Trả về access_token + refresh_token

POST /api/v1/auth/login
Body: { username, password }
→ Verify password hash
→ Trả về access_token (15 phút) + refresh_token (7 ngày)

POST /api/v1/auth/refresh
Header: Authorization: Bearer <refresh_token>
→ Kiểm tra refresh_token còn hạn không
→ Trả về access_token mới

POST /api/v1/auth/logout
→ Blacklist refresh_token trong Redis
→ Ghi last_logout_timestamp cho character
```

### 2.2 Token Structure (JWT)
```python
# Access Token payload
{
    "sub"       : "user_id",
    "char_id"   : "character_id",
    "username"  : "player_name",
    "exp"       : unix_timestamp + 900,   # 15 phút
    "type"      : "access"
}

# Refresh Token payload
{
    "sub"   : "user_id",
    "exp"   : unix_timestamp + 604800,    # 7 ngày
    "jti"   : "unique_token_id",          # Để blacklist
    "type"  : "refresh"
}
```

---

## 3. API Endpoints — Full List

### Auth
```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
```

### Character
```
GET    /api/v1/character/me              # Lấy thông tin nhân vật hiện tại
PATCH  /api/v1/character/map            # Đổi Map (chuyển vùng)
POST   /api/v1/character/logout         # Ghi logout timestamp
GET    /api/v1/character/stats          # Chi tiết stats đầy đủ
```

### Inventory
```
GET    /api/v1/inventory                # Toàn bộ túi đồ
POST   /api/v1/inventory/equip          # Trang bị item
POST   /api/v1/inventory/unequip        # Tháo trang bị
DELETE /api/v1/inventory/item/{id}      # Vứt item
POST   /api/v1/inventory/forge          # Nâng cấp (forge) item
POST   /api/v1/item/unbind              # Unbind item dùng scroll
```

### AFK
```
POST   /api/v1/afk/claim                # Nhận AFK reward
GET    /api/v1/afk/preview              # Preview reward (không nhận)
```

### Market
```
GET    /api/v1/market/search            # Tìm kiếm listing
POST   /api/v1/market/list              # Đăng bán item
POST   /api/v1/market/buy               # Mua item
DELETE /api/v1/market/listing/{id}      # Hủy listing
GET    /api/v1/market/my-listings        # Listing của mình
GET    /api/v1/market/price-history/{def_id}  # Lịch sử giá
```

### Guild
```
GET    /api/v1/guild/{id}               # Thông tin guild
POST   /api/v1/guild/create
POST   /api/v1/guild/join
POST   /api/v1/guild/leave
GET    /api/v1/guild/boss/status        # Trạng thái Guild Boss hôm nay
POST   /api/v1/guild/boss/join          # Tham gia đánh Guild Boss
```

### World Boss
```
GET    /api/v1/world-boss/schedule      # Lịch World Boss
GET    /api/v1/world-boss/current       # Boss hiện tại (nếu đang active)
POST   /api/v1/world-boss/join
POST   /api/v1/world-boss/attack        # Gửi combat report
GET    /api/v1/world-boss/leaderboard
```

---

## 4. Database Schema (Core Tables)

```sql
-- Users
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username      VARCHAR(30) UNIQUE NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Characters (mỗi user tối đa 3 nhân vật)
CREATE TABLE characters (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID REFERENCES users(id),
    name                    VARCHAR(20) NOT NULL,
    class_id                VARCHAR(20) NOT NULL,
    level                   INT DEFAULT 1,
    soul_level              INT DEFAULT 0,
    current_exp             BIGINT DEFAULT 0,
    gold                    BIGINT DEFAULT 0,
    gems                    INT DEFAULT 0,
    current_map_id          INT DEFAULT 1,
    last_logout_timestamp   BIGINT,             -- Unix timestamp
    last_afk_claim_timestamp BIGINT,
    legendary_pity_counter  INT DEFAULT 0,
    mythic_pity_counter     INT DEFAULT 0,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- Item Instances
CREATE TABLE item_instances (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id        UUID REFERENCES characters(id),
    definition_id   VARCHAR(20) NOT NULL,
    rarity          VARCHAR(20) NOT NULL,
    enhance_level   INT DEFAULT 0,
    is_bound        BOOLEAN DEFAULT FALSE,
    is_equipped     BOOLEAN DEFAULT FALSE,
    equipped_slot   VARCHAR(20),
    is_in_market    BOOLEAN DEFAULT FALSE,
    dropped_at      BIGINT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Market Listings
CREATE TABLE market_listings (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seller_id        UUID REFERENCES characters(id),
    item_instance_id UUID REFERENCES item_instances(id),
    price_gold       BIGINT,
    listed_at        TIMESTAMPTZ DEFAULT NOW(),
    expires_at       TIMESTAMPTZ,
    status           VARCHAR(20) DEFAULT 'ACTIVE'  -- ACTIVE, SOLD, CANCELLED, EXPIRED
);

-- Index quan trọng
CREATE INDEX idx_market_status         ON market_listings(status);
CREATE INDEX idx_market_item_def       ON item_instances(definition_id);
CREATE INDEX idx_char_user             ON characters(user_id);
```

---

## 5. Unity API Client (Generic)

```csharp
// Core/APIClient.cs
public static class APIClient
{
    private static readonly string BASE_URL = "https://api.tinyworldclone.com/api/v1";
    private static string _accessToken;

    public static async Task<T> Get<T>(string endpoint)
    {
        using var req = UnityWebRequest.Get(BASE_URL + endpoint);
        SetAuthHeader(req);
        
        await req.SendWebRequest();
        HandleErrors(req);
        
        return JsonConvert.DeserializeObject<T>(req.downloadHandler.text);
    }

    public static async Task<T> Post<T>(string endpoint, object body)
    {
        string json = JsonConvert.SerializeObject(body);
        using var req = new UnityWebRequest(BASE_URL + endpoint, "POST");
        req.uploadHandler   = new UploadHandlerRaw(Encoding.UTF8.GetBytes(json));
        req.downloadHandler = new DownloadHandlerBuffer();
        req.SetRequestHeader("Content-Type", "application/json");
        SetAuthHeader(req);
        
        await req.SendWebRequest();
        HandleErrors(req);
        
        return JsonConvert.DeserializeObject<T>(req.downloadHandler.text);
    }

    public static async Task Delete(string endpoint)
    {
        using var req = UnityWebRequest.Delete(BASE_URL + endpoint);
        SetAuthHeader(req);
        await req.SendWebRequest();
        HandleErrors(req);
    }

    private static void SetAuthHeader(UnityWebRequest req)
    {
        if (!string.IsNullOrEmpty(_accessToken))
            req.SetRequestHeader("Authorization", $"Bearer {_accessToken}");
    }

    private static void HandleErrors(UnityWebRequest req)
    {
        if (req.result == UnityWebRequest.Result.ConnectionError)
            throw new NetworkException("No internet connection");

        if (req.responseCode == 401)
        {
            // Token hết hạn → tự động refresh
            _ = RefreshTokenAsync();
            throw new UnauthorizedException();
        }

        if (req.responseCode >= 400)
        {
            var error = JsonConvert.DeserializeObject<APIError>(req.downloadHandler.text);
            throw new APIException(req.responseCode, error.detail);
        }
    }

    private static async Task RefreshTokenAsync()
    {
        // Gọi /auth/refresh → lấy token mới → lưu lại
    }
    
    public static void SetToken(string token) => _accessToken = token;
}
```

---

## 6. Offline Mode Fallback

```
Khi không có internet:
  - Game vẫn chạy được (gameplay offline, dùng cached data)
  - AFK reward: tính local nhưng KHÔNG cộng vào account
    → Khi online lại: server tính lại từ stored logout_timestamp (luôn đúng)
  - Market: ẩn tính năng Trade, hiển thị thông báo "Cần kết nối internet"
  - Inventory: hiển thị từ cache, chặn thao tác cần đồng bộ

Cache strategy:
  PlayerPrefs (local):
    - character_snapshot: {level, stats, inventory} — snapshot gần nhất
    - last_logout_timestamp: để show "bạn offline X giờ" offline
  
  Khi online lại:
    - Sync toàn bộ từ server (server là source of truth)
    - Discard local cache
```

---

## 7. Security Checklist

```
✅ Tất cả logic reward (AFK, drop item) chạy server-side
✅ Client KHÔNG tự tính rồi báo lên — chỉ gửi action, nhận kết quả
✅ Rate limiting tại Cloudflare + Redis
✅ JWT blacklist cho logout
✅ Atomic transaction cho market (tránh double-spend)
✅ Timestamp validation — server dùng timestamp của mình
✅ Input validation bằng Pydantic tất cả endpoint
✅ SQL injection protected bằng SQLAlchemy ORM
✅ HTTPS bắt buộc (Cloudflare SSL)
✅ Password hashed bằng bcrypt (cost factor 12)
```
