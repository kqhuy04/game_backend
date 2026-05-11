# 01 — Pitch & Game Vision
> **GDD TinyWorld Clone** | Tổng quan & Tầm nhìn sản phẩm

---

## 1. Một câu mô tả game

> **"Idle MMORPG Pixel Art mobile — treo máy 3 tiếng, giao dịch tự do, 9 hệ phái chiến đấu độc lập."**

---

## 2. Bối cảnh & Cảm hứng

Game clone lấy cảm hứng từ **TinyWorld-Idle MMORPG** (OhMyPixel). Mục tiêu không phải sao chép 1:1 mà tái tạo lại phần cốt lõi:
- **Treo máy tích lũy tài nguyên** (AFK Offline Reward)
- **9 hệ phái** với vai trò Tank / DPS / Support
- **Hệ thống chợ giao dịch tự do** (Free Trade Market)
- **Dungeon đa dạng** từ solo đến guild co-op
- **World Boss** theo lịch hàng ngày

---

## 3. Target Player

| Nhóm | Mô tả |
|---|---|
| **Casual Gamer** | 18-35 tuổi, bận rộn, chỉ online 5-15 phút/ngày |
| **MMORPG Veteran** | Thích xây dựng nhân vật dài hạn, trade kiếm lợi |
| **Guild Player** | Muốn nội dung co-op, guild boss, ranking |

**Khẩu hiệu:** *"5 phút online, 3 tiếng offline — vẫn đủ mạnh."*

---

## 4. Core Loop (Vòng lặp cốt lõi)

```
[ONLINE]
  Login → Nhận AFK Reward (offline loot)
       → Kiểm tra túi đồ / bán đồ dư
       → Tham gia Dungeon / Guild Boss / World Boss
       → Nâng cấp trang bị / kỹ năng
       → Đặt nhân vật vào Map tiếp theo
  Logout

[OFFLINE - tối đa 3 giờ]
  Timestamp ghi lại lúc logout
  Nhân vật tự động: đánh quái → nhặt EXP + Gold + Item
  Server tính toán reward khi user quay lại
```

**Công thức vắn tắt:**
```
Đánh quái → EXP/Gold/Loot → Lên cấp → Mở Skill → Vào Map mạnh hơn
                ↓
           Giao dịch Chợ → Mua đồ tốt hơn → ↑ sức mạnh
                ↓
           Guild → Dungeon Co-op → Phần thưởng đặc biệt
```

---

## 5. Điểm khác biệt so với TinyWorld gốc

| Feature | TinyWorld Gốc | Bản Clone (Mục tiêu) |
|---|---|---|
| P2W | Cao (boss drop bất công) | Thấp — drop rate công khai, không bán sức mạnh |
| Server | Cross-server, Top China players dominate | Regional server hoặc single-server balance |
| Drop Rate | Không rõ ràng | Hiển thị công khai trong UI |
| Trade | Có nhưng bị giới hạn | Tự do hoàn toàn với thuế nhẹ |

---

## 6. Tính năng chính (Feature List)

### ✅ MVP (Phase 1)
- [ ] Đăng ký / Đăng nhập (JWT)
- [ ] Tạo nhân vật, chọn hệ phái (9 class)
- [ ] Auto-combat trên Map (Idle)
- [ ] AFK Offline Reward (tối đa 3h)
- [ ] Hệ thống túi đồ (Inventory)
- [ ] Trang bị & nâng cấp (Forge)
- [ ] Chợ giao dịch (Market)
- [ ] Solo Dungeon (Daily)

### 🔜 Phase 2
- [ ] Guild system
- [ ] Guild Boss (daily/weekly)
- [ ] Party Matching (4 người)
- [ ] World Boss (multi-player)
- [ ] PvP Arena

### 🔮 Phase 3
- [ ] Dimensional Rift (Limited dungeon)
- [ ] Title system
- [ ] Season / Battle Pass
- [ ] Cross-server World Boss

---

## 7. Monetization (Định hướng)

> **Không bán sức mạnh trực tiếp.** Tất cả item chiến đấu đều kiếm được qua gameplay.

| Nguồn thu | Mô tả |
|---|---|
| **Cosmetic** | Skin nhân vật, hiệu ứng kỹ năng, pet trang trí |
| **Convenience** | Mở rộng túi đồ thêm slot, tăng thời gian AFK từ 3h → 6h |
| **Battle Pass** | Season pass với reward mỹ phẩm |
| **Chợ Tax** | 5% thuế mỗi giao dịch → doanh thu game |

---

## 8. Tóm tắt cho AI

Khi AI nhận context này, hãy luôn nhớ:
1. Game là **Idle** — auto-combat là tính năng cốt lõi, KHÔNG phải bug.
2. Mọi tính toán tài nguyên (EXP, Gold, Loot) đều phải **deterministic** dựa trên timestamp — dễ verify, chống gian lận.
3. Item có **ID độc nhất** — quan trọng cho hệ thống trade và lưu trữ.
4. Logic nhạy cảm (AFK reward, giao dịch chợ) phải chạy ở **server** — client chỉ hiển thị kết quả.
5. Thiết kế hướng đến **mobile-first**: UI lớn, tap-friendly, hiệu năng tối ưu.
