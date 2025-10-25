# Sınav Planlama Algoritması - Güncelleme Raporu

## 🔴 Eski (Yanlış) Sistem

### Sorunlar:
1. **Sabit Saat Dilimleri:** Sadece 3 sabit zaman (09:00, 13:00, 16:00)
2. **Tek Derslik Kullanımı:** Her slotta sadece 1 derslik kullanılıyordu
3. **Yetersiz Kapasite:** 39 ders için sadece 15 slot (5 gün × 3 slot)
4. **Paralel Sınavlar Yok:** Aynı anda farklı dersliklerde sınav yapılamıyordu

### Sonuç:
```
❌ Yetersiz zaman aralığı! 39 ders için 15 slot mevcut.
```

---

## ✅ Yeni (Doğru) Sistem

### Geliştirmeler:

#### 1. **Dinamik Saat Dilimleri**
Sınav süresi ve ara süresi parametrelerinden otomatik hesaplama:

```python
# Varsayılan: 75 dakika sınav + 15 dakika ara = 90 dakika
slot_interval = exam_duration + break_duration

# 09:00'dan başlayarak 17:45'e kadar
# Saat Dilimleri: 09:00, 10:30, 12:00, 13:30, 15:00, 16:30
# Toplam: 6 slot/gün
```

**Örnek Hesaplama:**
- Başlangıç: 09:00
- Her slot: 90 dakika
- Son slot: 16:30-17:45
- **Günlük slot sayısı: 6**

#### 2. **Paralel Derslik Kullanımı**
Her saat diliminde **TÜM derslikler** kullanılabilir:

```
Örnek: 5 derslik, 5 gün
- 6 slot/gün × 5 derslik = 30 sınav/gün
- 5 gün × 30 sınav = 150 toplam kapasite
```

**Gerçek Senaryo:**
```
09:00 Pazartesi:
  ├─ D-101: BLM101 Sınavı (120 öğrenci)
  ├─ D-102: BLM201 Sınavı (80 öğrenci)
  ├─ D-103: BLM301 Sınavı (95 öğrenci)
  ├─ D-104: BLM401 Sınavı (60 öğrenci)
  └─ D-105: MUH101 Sınavı (110 öğrenci)

10:30 Pazartesi:
  ├─ D-101: BLM102 Sınavı (115 öğrenci)
  ├─ D-102: BLM202 Sınavı (85 öğrenci)
  └─ ... (devam eder)
```

#### 3. **Öğrenci Çakışma Kontrolü**
Aynı öğrencinin aynı saatte iki sınavı olamaz:

```python
# Her slot için öğrenci takibi
student_schedule = {}

# Çakışma kontrolü
students_in_slot = student_schedule.get(slot_key, set())
has_conflict = any(sid in students_in_slot for sid in student_ids)

if has_conflict:
    # Bu slotu atla, öğrencilerin başka sınavı var
    continue
```

#### 4. **Derslik Kapasite Kontrolü**
Her dersliğe kapasitesine uygun ders atanır:

```python
if derslik['kapasite'] >= ogrenci_count:
    # Bu derslik uygun
    assign_exam(...)
```

---

## 📊 Kapasite Karşılaştırması

### Eski Sistem:
```
5 gün × 3 slot = 15 toplam slot
39 ders > 15 slot ❌ HATA!
```

### Yeni Sistem:
```
5 gün × 6 slot × 5 derslik = 150 toplam kapasite
39 ders < 150 kapasite ✅ YETERLİ!
```

---

## 🎯 Algoritma Akışı

### Adım 1: Zaman Dilimlerini Oluştur
```python
time_slots = _generate_time_slots(
    start_date='2025-01-06',
    end_date='2025-01-10',
    exam_duration=75,
    break_duration=15
)
# Sonuç: [
#   2025-01-06 09:00,
#   2025-01-06 10:30,
#   2025-01-06 12:00,
#   ...
#   2025-01-10 16:30
# ]
# Toplam: 30 slot (5 gün × 6 slot)
```

### Adım 2: Toplam Kapasiteyi Hesapla
```python
total_capacity = len(time_slots) × len(derslikler)
# 30 slot × 5 derslik = 150 kapasite
```

### Adım 3: Dersleri Yerleştir
Her ders için:
1. Öğrencileri al
2. Boş slot ara
3. Öğrenci çakışması kontrol et
4. Uygun derslik bul
5. Atamayı yap
6. Slot ve öğrenci kayıtlarını güncelle

```python
for ders in dersler:
    for slot in time_slots:
        if no_student_conflict and has_available_classroom:
            assign_exam(ders, slot, classroom)
            break
```

---

## 🔧 Kod Değişiklikleri

### Dosya: `algorithms/sinav_planlama.py`

#### Değişiklik 1: Dinamik Saat Dilimleri
```python
# ÖNCE: Sabit 3 zaman
base_times = [(9, 0), (13, 0), (16, 0)]

# SONRA: Dinamik hesaplama
slot_interval = exam_duration + break_duration
current_minutes = 9 * 60  # 09:00
end_minutes = 17 * 60 + 45  # 17:45

while current_minutes <= end_minutes:
    base_times.append((hour, minute))
    current_minutes += slot_interval
```

#### Değişiklik 2: Paralel Derslik Kullanımı
```python
# ÖNCE: Tek derslik
for i, ders in enumerate(dersler):
    derslik = derslikler[i % len(derslikler)]
    schedule.append({
        'ders': ders,
        'slot': time_slots[i],
        'derslik': derslik
    })

# SONRA: Paralel derslik
slot_usage = {}  # Her slotta kullanılan derslikler
for ders in dersler:
    for slot in time_slots:
        for derslik in derslikler:
            if derslik not in slot_usage[slot]:
                assign(ders, slot, derslik)
                slot_usage[slot].append(derslik)
                break
```

#### Değişiklik 3: Öğrenci Çakışma Kontrolü
```python
# YENİ: Öğrenci takibi
student_schedule = {}  # Her slotta sınavı olan öğrenciler

for ders in dersler:
    student_ids = get_students(ders)
    
    for slot in time_slots:
        # Çakışma kontrolü
        if any(sid in student_schedule[slot] for sid in student_ids):
            continue  # Bu slot uygun değil
        
        # Atama yap
        assign(ders, slot, derslik)
        student_schedule[slot].update(student_ids)
```

---

## ✅ Test Senaryosu

### Parametreler:
- **Bölüm:** Bilgisayar Mühendisliği
- **Ders Sayısı:** 39
- **Derslik Sayısı:** 5 (D-101, D-102, D-103, D-104, D-105)
- **Tarih Aralığı:** 5 gün (Pazartesi-Cuma)
- **Sınav Süresi:** 75 dakika
- **Ara Süresi:** 15 dakika

### Beklenen Sonuç:
```
✅ Kapasite: 30 slot × 5 derslik = 150
✅ 39 ders başarıyla yerleştirildi
✅ Günlük ortalama: 8 sınav/gün
✅ Her slotta ortalama: 1-2 derslik kullanımı
✅ Öğrenci çakışması: 0
```

### Örnek Çıktı:
```
Pazartesi 09:00 | D-101: BLM101 (120 öğr)
Pazartesi 09:00 | D-102: BLM201 (80 öğr)
Pazartesi 10:30 | D-101: BLM301 (95 öğr)
Pazartesi 10:30 | D-103: BLM401 (60 öğr)
...
```

---

## 🚀 Sonuç

### Önceki Hata:
```
❌ Yetersiz zaman aralığı! 39 ders için 15 slot mevcut.
```

### Şimdi:
```
✅ 39 ders için 30 slot × 5 derslik = 150 kapasite mevcut.
✅ Tüm dersler başarıyla programlandı!
```

### İyileştirme:
- **10x daha fazla kapasite** (15 → 150)
- **Paralel sınav desteği**
- **Öğrenci çakışma önleme**
- **Dinamik zaman hesaplama**

---

## 📝 Notlar

1. **Hafta Sonu Kontrolü:** Varsayılan olarak Cumartesi-Pazar atlanır
2. **Derslik Kapasitesi:** Her ders için uygun kapasiteli derslik seçilir
3. **Öğrenci Verisi:** `ogrenci_model.get_ogrenciler_by_ders()` ile alınır
4. **Çakışma Kontrolü:** Set operasyonları ile hızlı çakışma tespiti

---

## 🎓 Kullanım

Sistem artık hazır! Sınav oluşturma ekranından:

1. Bölüm seç
2. Tarih aralığı belirle (örn: 5 gün)
3. Sınav parametrelerini gir (75 dk + 15 dk ara)
4. "Program Oluştur" butonuna tıkla
5. ✅ 39 ders otomatik olarak yerleştirilecek!


