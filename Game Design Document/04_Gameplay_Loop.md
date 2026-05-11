# 04 — Gameplay Loop: Combat & Progression
> **GDD TinyWorld Clone** | Cơ chế Chiến đấu & Vượt ải

---

## 1. Map System (Hệ thống Bản đồ)

### Cấu trúc Map
```
World Map gồm nhiều Zone:
  Zone 1: Enchanted Forest (Lv 1-10)
  Zone 2: Goblin Ruins     (Lv 11-20)
  Zone 3: Dark Swamp       (Lv 21-35)
  Zone 4: Dragon Peak      (Lv 36-50)
  Zone 5: Abyss Rift       (Lv 51-65)
  ...

Mỗi Zone có nhiều Map con (Stage):
  Stage = 1 màn chơi, có quái, có địa hình

Unlock: Clear Stage hiện tại → mở Stage kế tiếp
```

### Map Data (ScriptableObject)
```csharp
[CreateAssetMenu(menuName = "TinyWorld/Map/MapData")]
public class MapData : ScriptableObject
{
    public string    mapName;
    public int       mapID;
    public int       recommendedLevel;
    public int       tileWidth, tileHeight;  // Kích thước lưới ô vuông
    public TileBase  groundTile;
    public List<MonsterSpawnRule> spawnRules;
    public List<ItemDefinition>  possibleDrops;
    public float     baseExpMultiplier;
    public float     baseGoldMultiplier;
}
```

---

## 2. Monster System

### Monster Data
```csharp
[CreateAssetMenu(menuName = "TinyWorld/Monster/MonsterData")]
public class MonsterData : ScriptableObject
{
    public string    monsterName;
    public MonsterType type;        // NORMAL, ELITE, BOSS, WORLD_BOSS
    public int       level;
    public int       baseHP;
    public int       baseATK;
    public int       baseDEF;
    public float     baseDropRate;  // Xác suất drop item (0-1)
    public int       expReward;
    public int       goldReward;
    public List<DropTableEntry> dropTable;
    public float     respawnTimeSec; // Giây — chỉ dùng ở World Map
}

[Serializable]
public class DropTableEntry
{
    public ItemDefinition itemDef;
    public float          weight;    // Weight trong random pool
    public int            minQty;
    public int            maxQty;
}
```

### Monster Spawn Logic
```csharp
public class MonsterSpawner : MonoBehaviour
{
    [SerializeField] private MapData      _mapData;
    [SerializeField] private Transform[]  _spawnPoints;
    private List<MonsterController>       _activeMonsters;

    // Số quái tối đa trên Map tại một thời điểm
    private int MaxMonsterCount => _mapData.spawnRules.Sum(r => r.maxCount);

    void Start() => StartCoroutine(SpawnLoop());

    IEnumerator SpawnLoop()
    {
        while (true)
        {
            if (_activeMonsters.Count < MaxMonsterCount)
                SpawnOne();
            yield return new WaitForSeconds(2f);
        }
    }

    void SpawnOne()
    {
        // Chọn spawn rule theo weight
        var rule    = WeightedRandom(_mapData.spawnRules);
        var point   = _spawnPoints[Random.Range(0, _spawnPoints.Length)];
        var monster = Instantiate(rule.prefab, point.position, Quaternion.identity);
        _activeMonsters.Add(monster);
    }
}
```

---

## 3. Auto-Combat (Chiến đấu Tự động)

```
Auto-combat là tính năng CHÍNH, không phải tùy chọn.
Người chơi chọn Map → nhân vật tự động chiến đấu.
Người chơi có thể: điều chỉnh target priority, bật/tắt skill cụ thể.
```

### Combat Loop (Client-side simulation, Server verify)
```csharp
public class AutoCombatManager : MonoBehaviour
{
    private CharacterBase _character;
    private MonsterController _currentTarget;
    private float _attackTimer;

    void Update()
    {
        if (_currentTarget == null || _currentTarget.IsDead)
            _currentTarget = FindNearestEnemy();

        if (_currentTarget == null) return;

        // Tự động đi đến tầm đánh
        if (!InAttackRange(_currentTarget))
        {
            MoveToward(_currentTarget.transform.position);
            return;
        }

        // Auto-attack
        _attackTimer -= Time.deltaTime;
        if (_attackTimer <= 0)
        {
            PerformAutoAttack();
            _attackTimer = 1f / _character.data.baseAtkSpeed;
        }

        // Auto-skill (cooldown-based)
        TryUseSkillsInPriority();
    }

    void PerformAutoAttack()
    {
        int dmg = DamageCalculator.Calculate(_character, _currentTarget);
        _currentTarget.TakeDamage(dmg);
        OnHitEffects(dmg);
    }
}
```

---

## 4. EXP Curve (Công thức lên cấp)

### Công thức EXP cần để lên cấp

```python
# EXP cần để đạt Level N
def exp_required(level: int) -> int:
    """
    Công thức: EXP(n) = BASE_EXP × n^EXP_EXPONENT × GROWTH_FACTOR
    Tham số điều chỉnh:
      BASE_EXP      = 100
      EXP_EXPONENT  = 1.8   (tăng dần nhưng không quá dốc)
      GROWTH_FACTOR = 1.05  (thêm 5% mỗi 10 level)
    """
    BASE_EXP     = 100
    EXP_EXPONENT = 1.8
    
    # Growth factor tăng nhẹ mỗi 10 level
    tier         = level // 10
    growth       = 1.0 + tier * 0.05
    
    return int(BASE_EXP * (level ** EXP_EXPONENT) * growth)

# Ví dụ:
# Level  1 → 2  :    100 EXP
# Level  5 → 6  :    350 EXP
# Level 10 → 11 :    870 EXP
# Level 20 → 21 :  3,200 EXP
# Level 50 → 51 : 36,000 EXP
```

### EXP Quái thưởng
```python
def monster_exp_reward(monster_level: int, char_level: int) -> int:
    """
    Penalize nếu quái quá yếu so với nhân vật (grinding map cũ)
    """
    base_exp    = int(50 * (monster_level ** 1.5))
    level_diff  = char_level - monster_level
    
    if level_diff <= 5:
        multiplier = 1.0
    elif level_diff <= 10:
        multiplier = 0.6
    elif level_diff <= 15:
        multiplier = 0.3
    else:
        multiplier = 0.1   # Quái quá yếu, EXP gần như không có
    
    return int(base_exp * multiplier)
```

---

## 5. Pathfinding (Tìm đường)

### Grid-based A* (Unity)
```
Map dạng lưới ô vuông (Tilemap)
Mỗi ô = 1 tile (walkable / obstacle)
Nhân vật và quái dùng A* để tìm đường

Đơn giản hóa cho Idle game:
  - Pathfinding chạy mỗi 0.5s (không real-time mỗi frame)
  - Nếu path bị block, đứng yên và attack từ xa nếu có thể
```

```csharp
public class GridPathfinder : MonoBehaviour
{
    private static GridPathfinder _instance;
    private bool[,] _walkableGrid;
    
    public List<Vector2Int> FindPath(Vector2Int start, Vector2Int end)
    {
        // A* implementation
        var openSet   = new PriorityQueue<Vector2Int, float>();
        var cameFrom  = new Dictionary<Vector2Int, Vector2Int>();
        var gScore    = new Dictionary<Vector2Int, float>();
        
        openSet.Enqueue(start, 0);
        gScore[start] = 0;
        
        while (openSet.Count > 0)
        {
            var current = openSet.Dequeue();
            if (current == end) return ReconstructPath(cameFrom, current);
            
            foreach (var neighbor in GetNeighbors(current))
            {
                float tentative_g = gScore[current] + 1;
                if (!gScore.ContainsKey(neighbor) || tentative_g < gScore[neighbor])
                {
                    cameFrom[neighbor] = current;
                    gScore[neighbor]   = tentative_g;
                    float f            = tentative_g + Heuristic(neighbor, end);
                    openSet.Enqueue(neighbor, f);
                }
            }
        }
        return null; // No path
    }
    
    float Heuristic(Vector2Int a, Vector2Int b)
        => Mathf.Abs(a.x - b.x) + Mathf.Abs(a.y - b.y); // Manhattan distance
}
```

---

## 6. Dungeon System

### Loại Dungeon

| Loại | Reset | Số người | Reward |
|---|---|---|---|
| **Daily Solo** | Hàng ngày | 1 | Materials, EXP |
| **Party Dungeon** | Hàng ngày | 2-4 | Epic/Legendary loot |
| **Guild Dungeon** | Hàng ngày | Guild | Contribution Coins |
| **Guild Mysterious** | Hàng tuần | All Guilds | Amulets, Ancient Mats |
| **Dimensional Rift** | 2 ngày / lần | 1-4 | Ancient gear |
| **World Boss** | Hàng ngày | Server | Boss Chest |

### Dungeon Flow
```
1. Vào dungeon → load DungeonScene
2. Wave-based: dọn sạch wave → wave tiếp theo
3. Boss wave cuối: kill boss → nhận reward
4. Reward tính toán:
   - Individual reward: dựa vào DPS contribution
   - Participation reward: chỉ cần có mặt
5. Dungeon kết thúc → return về World Map
```

---

## 7. World Boss

```
- Xuất hiện tại thời điểm cố định (8:00, 12:00, 20:00 server time)
- Tất cả người chơi trong server có thể tham gia
- HP Boss rất lớn (scale theo số người tham gia)
- Reward: Boss Chest (guaranteed drop khi đánh >= 1% HP)
  → Tránh vấn đề "top player quét hết" của TinyWorld gốc

Reward phân phối:
  Top 3 DPS    : Boss Chest (Gold)    — 3 item choices
  Top 4-10 DPS : Boss Chest (Silver)  — 2 item choices
  Tham gia     : Boss Chest (Bronze)  — 1 item ngẫu nhiên
```
