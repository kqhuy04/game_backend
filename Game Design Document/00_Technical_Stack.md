# 00 — Technical Stack
> **GDD TinyWorld Clone** | Tài liệu tham chiếu kỹ thuật cho AI code generation

---

## 1. Tổng quan Dự án

| Thuộc tính | Giá trị |
|---|---|
| Tên dự án | TinyWorld Clone |
| Thể loại | Idle MMORPG 2D Pixel Art |
| Nền tảng mục tiêu | Android, iOS (Mobile-first) |
| Phong cách đồ họa | 2D Pixel Art, top-down hoặc side-scroll |
| Ngôn ngữ dev | C# (Unity), Python (Backend) |

---

## 2. Client — Unity

| Thành phần | Lựa chọn | Ghi chú |
|---|---|---|
| **Unity Version** | Unity 6 LTS (6000.x) | Dùng version LTS để ổn định |
| **Render Pipeline** | URP (Universal Render Pipeline) | Hỗ trợ tốt cho mobile 2D |
| **Scripting Backend** | IL2CPP | Bắt buộc cho iOS release |
| **Target API Level** | Android API 24+ / iOS 14+ | |
| **2D Framework** | Unity Tilemap + Sprite Atlas | Map dạng lưới ô vuông |
| **Animation** | Animator Controller + Sprite Sheet | Frame-by-frame pixel art |
| **Physics** | Rigidbody2D + Collider2D | Tránh dùng MeshCollider |
| **UI Framework** | Unity UI (uGUI) | Canvas dạng Screen Space - Overlay |
| **Addressables** | Addressable Asset System | Load asset theo yêu cầu, tiết kiệm RAM |
| **Data Persistence** | PlayerPrefs (offline) + REST API (online) | |
| **Serialization** | Newtonsoft.Json (Json.NET) | `com.unity.nuget.newtonsoft-json` |
| **Dependency Injection** | Không dùng DI framework nặng — dùng ScriptableObject làm data bus | |

### Naming Convention (C#)
```
Class / ScriptableObject : PascalCase       → CharacterData, ItemDefinition
Method                   : PascalCase       → CalculateDamage()
Field (private)          : _camelCase       → _currentHp
Field (public/serialized): camelCase        → maxHp
Constant                 : UPPER_SNAKE_CASE → MAX_INVENTORY_SLOT
Interface                : IPascalCase      → IDamageable
```

### Cấu trúc thư mục Unity
```
Assets/
├── _Project/
│   ├── Scripts/
│   │   ├── Core/           # GameManager, EventBus, SaveSystem
│   │   ├── Character/      # Base class, Class-specific
│   │   ├── Combat/         # DamageCalculator, StatusEffect
│   │   ├── Inventory/      # Item, Slot, Bag
│   │   ├── Idle/           # AFKManager, OfflineReward
│   │   ├── Market/         # TradeManager, APIClient
│   │   └── UI/             # HUD, Panel, Popup
│   ├── ScriptableObjects/
│   │   ├── Characters/
│   │   ├── Items/
│   │   └── Skills/
│   ├── Prefabs/
│   ├── Sprites/
│   ├── Tilemaps/
│   └── Scenes/
└── Plugins/
    └── Newtonsoft.Json/
```

---

## 3. Backend — Python

| Thành phần | Lựa chọn | Ghi chú |
|---|---|---|
| **Framework** | FastAPI | Async, tự gen Swagger docs |
| **Python Version** | 3.11+ | |
| **ASGI Server** | Uvicorn | Production: Gunicorn + Uvicorn worker |
| **Database** | PostgreSQL 15 | Dữ liệu chính: nhân vật, item, giao dịch |
| **ORM** | SQLAlchemy 2.0 (async) | Async session với asyncpg driver |
| **Cache / Session** | Redis 7 | Session token, rate limit, leaderboard |
| **Auth** | JWT (python-jose) | Access Token 15 phút + Refresh Token 7 ngày |
| **Validation** | Pydantic v2 | Request/Response schema |
| **Migration** | Alembic | Version control DB schema |
| **Task Queue** | Celery + Redis broker | Tính toán AFK reward theo batch |
| **Containerization** | Docker + docker-compose | Dev environment |

### Naming Convention (Python)
```
Class         : PascalCase    → CharacterModel, ItemSchema
Function      : snake_case    → calculate_afk_reward()
Variable      : snake_case    → current_hp, max_level
Constant      : UPPER_SNAKE   → MAX_AFK_HOURS, BASE_EXP_RATE
API Endpoint  : kebab-case    → /api/v1/afk-reward, /api/v1/market/list
```

### Cấu trúc thư mục Backend
```
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py       # Settings từ .env
│   │   ├── security.py     # JWT helpers
│   │   └── database.py     # DB session
│   ├── models/             # SQLAlchemy models
│   ├── schemas/            # Pydantic schemas
│   ├── routers/
│   │   ├── auth.py
│   │   ├── character.py
│   │   ├── afk.py
│   │   └── market.py
│   └── services/           # Business logic
├── alembic/
├── tests/
├── Dockerfile
└── docker-compose.yml
```

---

## 4. API Communication

- **Base URL (dev):** `http://localhost:8000/api/v1`
- **Base URL (prod):** `https://api.tinyworldclone.com/api/v1`
- **Protocol:** HTTPS REST (JSON)
- **Auth Header:** `Authorization: Bearer <access_token>`
- **Content-Type:** `application/json`
- **Timeout client:** 10 giây — sau đó fallback về offline mode

### HTTP Status Code Convention
| Code | Ý nghĩa |
|---|---|
| 200 | OK — thành công |
| 201 | Created — tạo mới thành công |
| 400 | Bad Request — sai input |
| 401 | Unauthorized — token hết hạn |
| 403 | Forbidden — không có quyền |
| 409 | Conflict — xung đột dữ liệu (vd: item đã được mua) |
| 422 | Unprocessable Entity — lỗi validation |
| 429 | Too Many Requests — rate limit |
| 500 | Internal Server Error |

---

## 5. External Services

| Dịch vụ | Mục đích |
|---|---|
| Firebase Auth (optional) | Login Google / Apple nhanh |
| Firebase Analytics | Track retention, funnel |
| Google Play / App Store | Distribution |
| Cloudflare | CDN, DDoS protection cho backend |

---

## 6. Dev Environment

```bash
# Unity: cài package qua Package Manager
com.unity.nuget.newtonsoft-json
com.unity.addressables
com.unity.2d.tilemap

# Python backend
pip install fastapi uvicorn sqlalchemy asyncpg
pip install redis celery pydantic python-jose alembic
```

> **Lưu ý cho AI:** Khi gen code Unity, luôn dùng `using Newtonsoft.Json;` thay vì `JsonUtility` để xử lý JSON phức tạp. Khi gen code Python, luôn dùng `async def` và `await` với SQLAlchemy 2.0.
