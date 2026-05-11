# 05 — Idle / AFK System
> **GDD TinyWorld Clone** | Trái tim của Idle Game — Hệ thống Treo máy

---

## 1. Tổng quan

```
Khi người chơi LOGOUT hoặc tắt app:
  → Ghi Timestamp logout lên server
  → Nhân vật "ảo" tiếp tục đánh quái trên Map họ đang ở
  → Tài nguyên tích lũy theo thời gian (có giới hạn tối đa 3 giờ)

Khi người chơi LOGIN lại:
  → Server tính Δt = now - logout_timestamp
  → Nội suy lượng EXP, Gold, Item nhận được
  → Trả về "AFK Report" cho client hiển thị màn hình tổng kết
```

---

## 2. AFK Reward Calculation (Backend)

```python
# backend/services/afk_service.py

from datetime import datetime, timezone
import math, random
from typing import List

MAX_AFK_HOURS    = 3.0          # Giới hạn treo máy tối đa
RESOURCE_TICK    = 60.0         # Tính toán theo từng "phút ảo"

def calculate_afk_reward(
    character: CharacterData,
    logout_timestamp: int,      # Unix timestamp (giây)
    login_timestamp:  int,
) -> AFKRewardResult:

    # 1. Tính thời gian offline (giới hạn tối đa)
    delta_sec    = login_timestamp - logout_timestamp
    capped_sec   = min(delta_sec, MAX_AFK_HOURS * 3600)
    actual_hours = capped_sec / 3600.0

    # 2. Lấy Map stats nhân vật đang ở
    map_data     = get_map_data(character.current_map_id)
    monster_pool = map_data.monster_pool

    # 3. Tính tổng reward dựa trên số "phút ảo" đã trôi qua
    total_exp    = 0
    total_gold   = 0
    items_dropped: List[ItemInstance] = []

    # Simulate từng phút
    virtual_minutes = int(capped_sec / RESOURCE_TICK)
    
    for minute in range(virtual_minutes):
        # Số quái kill trong 1 phút
        kills_per_minute = estimate_kills_per_minute(character, monster_pool)
        
        for _ in range(kills_per_minute):
            monster = weighted_choice(monster_pool)
            
            # EXP
            exp = monster_exp_reward(monster.level, character.level)
            total_exp += int(exp * (1 + character.exp_bonus))
            
            # Gold
            gold = random.randint(monster.gold_min, monster.gold_max)
            total_gold += int(gold * (1 + character.gold_bonus))
            
            # Item drop (ít hơn online để khuyến khích chơi trực tiếp)
            if random.random() < monster.base_drop_rate * AFK_ITEM_DROP_PENALTY:
                item = roll_item_drop(monster, character)
                if item:
                    items_dropped.append(item)

    return AFKRewardResult(
        actual_offline_seconds = capped_sec,
        was_capped             = delta_sec > MAX_AFK_HOURS * 3600,
        total_exp              = total_exp,
        total_gold             = total_gold,
        items_dropped          = items_dropped[:MAX_AFK_ITEM_SLOTS],  # Giới hạn 30 item
    )

# Hệ số giảm item khi AFK (khuyến khích online)
AFK_ITEM_DROP_PENALTY = 0.6  # 60% drop rate so với online

# Slot tối đa item AFK nhận được 1 lần
MAX_AFK_ITEM_SLOTS = 30
```

---

## 3. Estimate Kills Per Minute

```python
def estimate_kills_per_minute(char: CharacterData, monsters: List[MonsterData]) -> int:
    """
    Ước tính số quái kill được trong 1 phút
    Dựa trên: ATK nhân vật, HP quái, tốc độ đánh
    """
    avg_monster = get_average_monster(monsters)
    
    # Thời gian kill 1 quái (giây)
    dps = (char.atk - avg_monster.def_) * char.atk_speed
    dps = max(dps, 1)  # Tối thiểu 1 DPS
    
    time_to_kill = avg_monster.base_hp / dps
    time_to_kill = max(time_to_kill, 1.0)  # Tối thiểu 1 giây/quái
    
    # Thêm thời gian di chuyển ước tính
    travel_time  = 2.0  # giây trung bình di chuyển giữa các quái
    
    kills = int(60.0 / (time_to_kill + travel_time))
    return max(kills, 1)
```

---

## 4. Anti-Cheat: Timestamp Validation (Backend)

```python
# backend/routers/afk.py

@router.post("/afk-reward")
async def claim_afk_reward(
    request: AFKClaimRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    character = await get_character(db, request.character_id, current_user.id)
    
    # VALIDATION 1: Timestamp hợp lệ
    server_now = int(datetime.now(timezone.utc).timestamp())
    
    if request.login_timestamp > server_now + 30:
        raise HTTPException(400, "Invalid timestamp: future time detected")
    
    # VALIDATION 2: Dùng logout_timestamp từ SERVER, không tin client
    # Client gửi lên chỉ để double-check — server dùng giá trị đã lưu
    stored_logout = character.last_logout_timestamp
    
    if stored_logout is None:
        raise HTTPException(400, "No logout record found")
    
    # VALIDATION 3: Khoảng cách logout vs login phải hợp lý
    delta = server_now - stored_logout
    if delta < 0:
        raise HTTPException(400, "Suspicious: logout is in the future")
    
    # VALIDATION 4: Rate limit — không claim liên tục
    if character.last_afk_claim_timestamp:
        since_last_claim = server_now - character.last_afk_claim_timestamp
        if since_last_claim < 60:
            raise HTTPException(429, "Claim cooldown: wait 60 seconds")
    
    # Tính reward bằng stored_logout (không trust client timestamp)
    reward = calculate_afk_reward(character, stored_logout, server_now)
    
    # Cập nhật DB
    await apply_afk_reward(db, character, reward)
    character.last_afk_claim_timestamp = server_now
    await db.commit()
    
    return reward
```

---

## 5. Logout Timestamp — Luồng ghi nhận

```
Client                          Server
  |                               |
  |--- POST /character/logout --->|
  |    { character_id, map_id }   |  ← Ghi last_logout_timestamp = now()
  |<-- 200 OK --------------------|
  |    { logged_out_at: 1234567 } |
  
  [... thời gian offline ...]
  
  |--- POST /afk/claim ---------->|
  |    { character_id }           |  ← Server tự tính delta từ DB
  |<-- 200 OK --------------------|
  |    AFKRewardResult            |
```

```csharp
// Unity — AFKManager.cs
public class AFKManager : MonoBehaviour
{
    private const string PREF_LOGOUT_TIME = "last_logout_timestamp";

    void OnApplicationPause(bool isPaused)
    {
        if (isPaused) OnAppBackground();
    }

    void OnApplicationQuit() => OnAppBackground();

    async void OnAppBackground()
    {
        // Thông báo server trước khi tắt
        await APIClient.Post("/character/logout", new {
            character_id = GameManager.CurrentCharacterId,
            map_id       = MapManager.CurrentMapId,
        });
        
        // Lưu local timestamp để hiển thị UI "bạn đã offline X giờ"
        PlayerPrefs.SetString(PREF_LOGOUT_TIME, 
            DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString());
    }

    public async Task<AFKRewardResult> ClaimAFKReward()
    {
        return await APIClient.Post<AFKRewardResult>("/afk/claim", new {
            character_id = GameManager.CurrentCharacterId,
        });
    }
}
```

---

## 6. AFK Report UI

```
Màn hình hiển thị khi login (nếu có AFK reward):

┌─────────────────────────────────┐
│  ⏰  BẠN ĐÃ OFFLINE  2h 30m     │
│                                 │
│  💎  EXP      +45,000           │
│  💰  Gold     +12,300           │
│  🎒  Items    8 vật phẩm        │
│                                 │
│  [Xem vật phẩm]   [Nhận tất cả] │
└─────────────────────────────────┘

Nếu bị cap 3h:
  "Túi đồ đầy sau 3 tiếng! Login sớm hơn để không bỏ lỡ phần thưởng."
```

---

## 7. Tăng Thời Gian AFK (Monetization)

```
Mặc định    : tối đa 3 giờ
VIP Tier 1  : tối đa 6 giờ   (Battle Pass hoặc mua Gems)
VIP Tier 2  : tối đa 12 giờ  (Premium Battle Pass)

Cách tăng tạm thời:
  - "AFK Booster x2h" : item tiêu thụ, tăng thêm 2h giới hạn AFK
  - Rơi từ dungeon hoặc mua bằng Gold
```
