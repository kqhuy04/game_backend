# 03 — Item & Inventory System
> **GDD TinyWorld Clone** | Vật phẩm & Túi đồ

---

## 1. Item ID Schema

Mọi item trong game đều có **ID độc nhất** theo định dạng:

```
{TypeCode}{RarityCode}{BaseItemID}{UniqueSerial}

Ví dụ:
  WP_R_0042_A3F9C1  →  Weapon, Rare, BaseItem #42, Serial A3F9C1
  AR_M_0011_7B2D44  →  Armor, Mythic, BaseItem #11, Serial 7B2D44
  MT_C_0001_000000  →  Material, Common, BaseItem #1, (Serial = 0 nếu stackable)
```

| TypeCode | Loại |
|---|---|
| `WP` | Weapon |
| `AR` | Armor (Body) |
| `HM` | Helmet |
| `BT` | Boots |
| `AC` | Accessory (Ring/Necklace) |
| `MT` | Material (stackable) |
| `CO` | Consumable |
| `KY` | Key Item (Dungeon Key, etc.) |

| RarityCode | Rarity |
|---|---|
| `C` | Common |
| `U` | Uncommon |
| `R` | Rare |
| `E` | Epic |
| `L` | Legendary |
| `M` | Mythic |
| `A` | Ancient |

---

## 2. Phân cấp Độ Hiếm (Rarity Tier)

| Rarity | Màu UI | Drop Rate (thường) | Bonus Stats | Tradeable |
|---|---|---|---|---|
| **Common** | Trắng | 60% | +0% | ✅ |
| **Uncommon** | Xanh lá | 25% | +15% | ✅ |
| **Rare** | Xanh dương | 10% | +35% | ✅ |
| **Epic** | Tím | 4% | +65% | ✅ |
| **Legendary** | Cam | 0.9% | +100% | ✅ |
| **Mythic** | Đỏ | 0.1% | +150% | ✅ |
| **Ancient** | Vàng (hiệu ứng glow) | 0.001% | +250% | ✅ (giới hạn) |

> Drop rate hiển thị công khai trong UI — không có hộp ẩn.

---

## 3. Loại Trang Bị & Slots

```
Nhân vật có 6 Equipment Slot:
  [Weapon]  [Helmet]
  [Armor]   [Boots]
  [Ring]    [Necklace]
```

### Item Data Model

```csharp
[CreateAssetMenu(menuName = "TinyWorld/Item/ItemDefinition")]
public class ItemDefinition : ScriptableObject
{
    [Header("Identity")]
    public string     itemName;
    public string     uniqueItemID;       // TypeCode + RarityCode + BaseID (template)
    public ItemType   itemType;
    public RarityTier rarity;
    public Sprite     icon;
    public string     description;

    [Header("Equipment Stats (nếu là trang bị)")]
    public int   bonusHP;
    public int   bonusATK;
    public int   bonusDEF;
    public int   bonusMAGATK;
    public int   bonusMAGDEF;
    public float bonusCritRate;
    public float bonusCritDmg;
    public float bonusDropRate;     // % tăng drop rate khi AFK
    public float bonusExpBonus;

    [Header("Requirement")]
    public int     requiredLevel;
    public ClassID requiredClass;   // ClassID.NONE = tất cả class đều dùng được

    [Header("Trade")]
    public bool  isBound;           // true = không trade được
    public int   baseGoldValue;     // Giá bán tại NPC

    [Header("Material / Consumable")]
    public bool  isStackable;
    public int   maxStackSize;
}
```

### Runtime Instance (Item đã rơi)

```csharp
[Serializable]
public class ItemInstance
{
    public string       instanceID;     // UniqueSerial — gen bằng GUID
    public string       definitionID;   // Trỏ về ItemDefinition
    public RarityTier   rarity;
    public int          enhanceLevel;   // +0 đến +15 (Forge)
    public bool         isBound;
    public long         droppedTimestamp;
    public string       droppedByCharacterID; // Để trace
    
    // Stats cuối cùng (sau enhance)
    public ItemStatBlock finalStats;
}
```

---

## 4. Hệ thống Forge (Nâng cấp trang bị)

```
Enhance Level: +0 → +15
Tỷ lệ thành công:
  +0  → +5  : 100%
  +6  → +9  : 70%
  +10 → +12 : 40%
  +13 → +14 : 20%
  +15         : 10%

Thất bại:
  +0  → +9  : Không mất gì (chỉ mất vật liệu)
  +10 → +12 : Về lại +9
  +13 → +15 : Hủy item (cần Protect Scroll để giữ)

Vật liệu:
  +1  → +5  : Enhancement Stone (Common)
  +6  → +9  : Enhancement Stone (Rare)
  +10 → +12 : Magic Crystal
  +13 → +15 : Ancient Crystal (cực hiếm)
```

---

## 5. Thuật toán Sinh Item Ngẫu nhiên (RNG Drop)

### 5.1 Quy trình Drop khi quái chết

```python
# Backend — services/loot_service.py

def roll_item_drop(monster: MonsterData, character: CharacterData) -> Optional[ItemInstance]:
    """
    1. Check xem có drop không (dựa vào drop_rate của quái)
    2. Nếu drop: chọn item template từ drop table
    3. Roll rarity
    4. Gen instance với GUID
    """
    base_drop_chance = monster.base_drop_rate
    final_drop_chance = base_drop_chance * (1 + character.drop_rate_bonus)
    
    if random.random() > final_drop_chance:
        return None  # Không drop
    
    # Chọn item template từ bảng drop của quái
    item_template = _weighted_choice(monster.drop_table)
    
    # Roll rarity (bị ảnh hưởng bởi bonus)
    rarity = _roll_rarity(character.luck_bonus)
    
    # Gen instance
    instance = ItemInstance(
        instance_id     = str(uuid.uuid4())[:6].upper(),
        definition_id   = item_template.id,
        rarity          = rarity,
        enhance_level   = 0,
        is_bound        = False,
        dropped_timestamp = int(time.time()),
    )
    return instance

def _roll_rarity(luck_bonus: float = 0.0) -> RarityTier:
    """
    Rarity weights — có thể điều chỉnh bằng luck_bonus
    """
    weights = {
        RarityTier.COMMON    : 60.0,
        RarityTier.UNCOMMON  : 25.0,
        RarityTier.RARE      : 10.0,
        RarityTier.EPIC      : 4.0,
        RarityTier.LEGENDARY : 0.9,
        RarityTier.MYTHIC    : 0.1 * (1 + luck_bonus),
        RarityTier.ANCIENT   : 0.001 * (1 + luck_bonus * 2),
    }
    return random.choices(list(weights.keys()), weights=list(weights.values()))[0]
```

### 5.2 Pity System (Bảo đảm độ hiếm)

```
Mỗi nhân vật có bộ đếm pity riêng:
  legendary_pity_counter  : Sau 200 kill không có Legendary → drop guaranteed
  mythic_pity_counter     : Sau 1000 kill không có Mythic → drop guaranteed

Pity reset về 0 khi trigger.
Lưu trữ: character.pity_counters (DB)
```

---

## 6. Inventory (Túi đồ)

```
Mặc định: 40 slot
Mở rộng: +10 slot / lần, tối đa 100 slot (trả Gems)

Slot types:
  - Equipment Slot: không stack
  - Material Slot: stack lên đến maxStackSize

Khi đầy túi:
  - Item rơi → vào "Ground Loot Buffer" (tối đa 20 item)
  - Sau 5 phút không nhặt → biến mất
  - Thông báo push nếu buffer sắp đầy
```

```csharp
// Unity — Inventory.cs
public class Inventory : MonoBehaviour
{
    public static readonly int BASE_SLOTS    = 40;
    public static readonly int MAX_SLOTS     = 100;
    public static readonly int SLOT_EXPAND   = 10;
    
    [SerializeField] private List<ItemSlot> _slots;
    
    public bool TryAddItem(ItemInstance item) { ... }
    public bool RemoveItem(string instanceID) { ... }
    public ItemInstance GetItem(string instanceID) { ... }
    public List<ItemInstance> GetItemsByType(ItemType type) { ... }
    
    // Serialize để gửi lên server
    public string SerializeToJson() => JsonConvert.SerializeObject(_slots);
}
```

---

## 7. Item Binding Rules

| Tình huống | Trạng thái |
|---|---|
| Item mới rơi từ quái | `Unbound` — có thể trade |
| Trang bị lên người | `Bound` — không thể trade |
| Tháo ra khỏi slot | Vẫn `Bound` — vĩnh viễn |
| Dùng `Unbind Scroll` | Về lại `Unbound` (scroll hiếm, mua bằng Gems) |
| Item từ Guild Reward | `Bound` ngay từ đầu |

> **Lý do:** Ngăn chặn exploit "mặc đồ tốt → đánh boss → tháo bán chợ". Muốn bán thì phải dùng đồ chưa trang bị.
