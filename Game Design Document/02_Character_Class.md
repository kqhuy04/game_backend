# 02 — Character & Class System
> **GDD TinyWorld Clone** | Hệ thống Nhân vật & Kỹ năng

---

## 1. Base Stats (Chỉ số nền — dùng chung mọi class)

```csharp
// ScriptableObject: CharacterBaseData.cs
[CreateAssetMenu(fileName = "CharacterData", menuName = "TinyWorld/Character/BaseData")]
public class CharacterBaseData : ScriptableObject
{
    [Header("Identity")]
    public string  className;
    public ClassID classID;         // Enum: WARRIOR, GUARDIAN, RANGER, ...
    public ClassRole role;          // Enum: TANK, DPS, SUPPORT

    [Header("Base Stats (tại Level 1)")]
    public int   baseHP;            // Máu tối đa
    public int   baseMana;          // Mana (dùng kỹ năng)
    public int   baseAtk;           // Tấn công vật lý
    public int   baseMagAtk;        // Tấn công phép
    public int   baseDef;           // Phòng thủ vật lý
    public int   baseMagDef;        // Phòng thủ phép
    public float baseAtkSpeed;      // Số đòn / giây (idle auto)
    public float baseMoveSpeed;     // Tốc độ di chuyển trên Map
    public float baseCritRate;      // Tỷ lệ chí mạng (0.0 - 1.0)
    public float baseCritDmg;       // Hệ số dame chí mạng (mặc định 1.5)
    public float baseEvasion;       // Né đòn

    [Header("Stat Growth per Level")]
    public float hpGrowth;          // HP tăng thêm mỗi level
    public float atkGrowth;
    public float defGrowth;
}
```

### Công thức Scale Stat theo Level
```
FinalStat(level) = BaseStat + (StatGrowth × (level - 1)) + BonusFromEquipment
MaxHP(level)     = baseHP   + (hpGrowth  × (level - 1)) + EquipmentHP
```

---

## 2. Chỉ số Chiến đấu Phụ (Combat Modifiers)

| Chỉ số | Mô tả | Nguồn |
|---|---|---|
| `penetration` | Xuyên giáp vật lý (giảm DEF đối thủ) | Equipment |
| `magPenetration` | Xuyên kháng phép | Equipment |
| `lifeSteal` | Hút máu % dame gây ra | Skill / Equipment |
| `cooldownReduce` | Giảm thời gian hồi kỹ năng | Equipment |
| `dropRateBonus` | Tăng tỷ lệ rơi item khi AFK | Equipment |
| `expBonus` | Tăng EXP nhận được | Equipment / Buff |

---

## 3. Công thức Tính Sát Thương

```
PhysicalDamage = (ATK × SkillMultiplier) - max(0, DEF - Penetration)
MagicDamage    = (MAG_ATK × SkillMultiplier) - max(0, MAG_DEF - MagPenetration)

IsCrit = Random(0,1) < CritRate
FinalDamage = BaseDamage × (IsCrit ? CritDmg : 1.0f)
FinalDamage = max(1, FinalDamage)  // Dame tối thiểu = 1
```

---

## 4. Soul Level (Cấp Linh Hồn)

Ngoài Level thường, nhân vật còn có **Soul Level** riêng:
- Tăng bằng cách tiêu thụ **Soul Stones** (rơi từ Elite Monster)
- Dùng để **mở khóa Skill** (active + passive)
- Giới hạn: `|Level - SoulLevel| <= 7`

```csharp
public bool CanLearnSkill(SkillData skill) {
    return soulLevel >= skill.requiredSoulLevel 
        && level >= skill.requiredLevel;
}
```

---

## 5. Danh sách 9 Class

### 🛡️ TANK (2 class)

#### 5.1 Warrior (Chiến Binh)
- **Vai trò:** Tank kiêm DPS — tự bảo vệ mình trong khi gây dame
- **Cơ chế đặc biệt:** `Rage` — tích lũy khi nhận dame, xả ra để tăng ATK
- **Base Stats:** HP cao nhất, ATK trung bình, DEF cao

| Skill | Loại | Mô tả |
|---|---|---|
| Slash | Active | Đòn chém cơ bản, dame ×1.5 |
| Shield Wall | Active | Tăng DEF +40% trong 3s |
| Berserker | Active | Xả toàn bộ Rage: dame ×(1 + Rage/100) |
| Iron Skin | Passive | Tăng DEF +10% vĩnh viễn |
| Battle Cry | Active | Tăng ATK toàn đội +15% trong 10s |

#### 5.2 Guardian (Hộ Vệ)
- **Vai trò:** Pure Tank — giảm dame nhận vào cho đồng đội
- **Cơ chế đặc biệt:** `Taunt` — ép quái tấn công Guardian
- **Base Stats:** HP và DEF cao nhất game, ATK thấp

| Skill | Loại | Mô tả |
|---|---|---|
| Taunt | Active | Quái trong vùng 3m tấn công Guardian 5s |
| Holy Guard | Active | Giảm dame nhận cho đồng đội trong vùng 20% (8s) |
| Fortress | Passive | Mỗi 10% HP mất, tăng DEF 5% |
| Counter | Active | Phản dame 30% đòn tiếp theo nhận |

---

### ⚔️ DPS (5 class)

#### 5.3 Ranger (Cung Thủ)
- **Vai trò:** DPS tầm xa, ổn định, an toàn
- **Cơ chế đặc biệt:** `Focus` — đứng yên tích lũy để tăng dame mũi tên
- **Base Stats:** ATK cao, HP trung bình, tốc độ đánh nhanh

| Skill | Loại | Mô tả |
|---|---|---|
| Power Shot | Active | Mũi tên dame ×2.0, xuyên 1 kẻ thù |
| Rain of Arrows | Active | Mưa tên AOE vùng 4×4 |
| Eagle Eye | Passive | Tăng tầm đánh +20%, crit rate +5% |
| Evasive Roll | Active | Lăn né, tăng evasion +30% (3s) |

#### 5.4 Pyromancer (Hỏa Pháp)
- **Vai trò:** AOE DPS — dọn đám quái, group clear
- **Cơ chế đặc biệt:** `Ignite` — đốt cháy, gây dame overtime
- **Base Stats:** MAG_ATK rất cao, HP thấp, tốc độ đánh chậm

| Skill | Loại | Mô tả |
|---|---|---|
| Fireball | Active | Cầu lửa dame ×2.5 + Ignite 3s |
| Meteor Shower | Active | AOE mưa thiên thạch 5×5 (cooldown dài) |
| Flame Mastery | Passive | Ignite dame +25% |
| Fire Shield | Active | Khiên lửa phản dame 20% |

#### 5.5 Rogue (Sát Thủ)
- **Vai trò:** Burst DPS — dame cực cao nhưng cần setup
- **Cơ chế đặc biệt:** `Stealth` → xuất hiện gây dame ×3 (Backstab)
- **Base Stats:** ATK rất cao, HP thấp, tốc độ cao

| Skill | Loại | Mô tả |
|---|---|---|
| Backstab | Active | Từ Stealth: dame ×3.0, stun 1s |
| Shadow Step | Active | Teleport phía sau mục tiêu |
| Vanish | Active | Vào Stealth 5s |
| Poison Blade | Passive | Mỗi đòn có 20% gây độc 3s |

#### 5.6 Forest Spirit (Lâm Thần)
- **Vai trò:** Melee DPS hệ tự nhiên — cân bằng dame/trụ
- **Cơ chế đặc biệt:** `Nature Bond` — hồi phục HP % dame gây ra
- **Base Stats:** HP và ATK đều trung bình-cao, cân bằng

| Skill | Loại | Mô tả |
|---|---|---|
| Vine Whip | Active | Dame ×1.8 + Entangle (immobilize 2s) |
| Nature's Wrath | Active | AOE xung quanh, dame ×2.2 |
| Regeneration | Passive | Hồi 5% dame gây ra thành HP |
| Barkskin | Active | Tăng DEF +25% và regain 10% MaxHP |

#### 5.7 Wizard (Phù Thủy)
- **Vai trò:** DoT DPS — dame liên tục, kiểm soát
- **Cơ chế đặc biệt:** `Mana Surge` — tiêu nhiều mana hơn để nhân đôi dame
- **Base Stats:** MAG_ATK cao, HP thấp nhất game

| Skill | Loại | Mô tả |
|---|---|---|
| Arcane Bolt | Active | Dame ×1.2 × 5 phát liên tiếp |
| Blizzard | Active | AOE chậm + dame băng liên tục |
| Time Warp | Active | Giảm cooldown tất cả skill -50% (5s) |
| Arcane Mastery | Passive | +15% MAG_ATK |

---

### 💚 SUPPORT (2 class)

#### 5.8 Priest (Tế Tư)
- **Vai trò:** Healer — hồi máu, hồi sinh
- **Cơ chế đặc biệt:** `Holy Light` — heal theo % HP tối đa
- **Base Stats:** HP trung bình, MAG_ATK thấp, Mana nhiều nhất

| Skill | Loại | Mô tả |
|---|---|---|
| Heal | Active | Hồi HP đồng minh 15% MaxHP |
| Resurrection | Active | Hồi sinh đồng minh đã chết (60s CD) |
| Holy Ward | Active | Khiên hấp thụ dame tương đương 20% MaxHP |
| Divine Blessing | Passive | Tăng heal +15% |

#### 5.9 Wind Spirit (Phong Thần)
- **Vai trò:** Crowd Control + Speed buff
- **Cơ chế đặc biệt:** `Gale` — đẩy kẻ thù, interrupt kỹ năng
- **Base Stats:** Tốc độ cao nhất, HP trung bình

| Skill | Loại | Mô tả |
|---|---|---|
| Gale Blast | Active | Knockback kẻ thù 2m, interrupt skill |
| Tailwind | Active | Tăng MoveSpeed toàn đội +30% (8s) |
| Cyclone | Active | AOE kéo kẻ thù vào trung tâm (3s) |
| Wind Walk | Passive | Tăng tốc độ đánh +10% |

---

## 6. Class Inheritance (Cấu trúc code)

```csharp
// Abstract base — file: CharacterBase.cs
public abstract class CharacterBase : MonoBehaviour
{
    public CharacterBaseData data;
    protected int   _currentHP;
    protected int   _currentMana;
    protected int   _level;
    protected int   _soulLevel;

    // Abstract — mỗi class tự implement
    public abstract void UseSkill1();
    public abstract void UseSkill2();
    public abstract void UseSkill3();
    public abstract void OnSpecialMechanicTick(); // Rage, Focus, Stealth,...

    // Common — dùng chung
    public virtual void TakeDamage(int rawDamage, DamageType type) { ... }
    public virtual void Die() { ... }
    public void          LevelUp() { ... }
}

// Ví dụ class cụ thể
public class WarriorCharacter : CharacterBase
{
    private int _rage; // 0-100

    public override void UseSkill1() { /* Slash */ }
    public override void UseSkill2() { /* Shield Wall */ }
    public override void UseSkill3() { /* Berserker — consume _rage */ }
    public override void OnSpecialMechanicTick() {
        // Tích lũy Rage khi nhận dame
    }
}
```

---

## 7. ScriptableObject cho Skill

```csharp
[CreateAssetMenu(menuName = "TinyWorld/Skill/SkillData")]
public class SkillData : ScriptableObject
{
    public string   skillName;
    public SkillID  skillID;
    public SkillType type;          // ACTIVE, PASSIVE
    public int      requiredLevel;
    public int      requiredSoulLevel;
    public float    manaCost;
    public float    cooldown;       // giây
    public float    damageMultiplier;
    public bool     isAOE;
    public float    aoeRadius;
    public string   descriptionTemplate; // "Gây {dmg} dame + Ignite {dur}s"
    public Sprite   icon;
    public AnimationClip castAnimation;
}
```
