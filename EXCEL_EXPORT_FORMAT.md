# Excel Export Formatı - Profesyonel Sınav Programı

## 📊 Örnek Çıktı

Sistem artık tam olarak aşağıdaki formatta Excel çıktısı üretir:

```
╔═══════════════════════════════════════════════════════════════════════════╗
║        BİLGİSAYAR MÜHENDİSLİĞİ BÖLÜMÜ VİZE SINAV PROGRAMI               ║
╠═══════════╦══════════════╦═══════════════════════╦═══════════════╦═══════╣
║   Tarih   ║  Sınav Saati ║      Ders Adı        ║ Öğretim Elemanı ║Derslik║
╠═══════════╬══════════════╬═══════════════════════╬═════════════════╬═══════╣
║           ║    10.00     ║ İngilizce II (UE)    ║ Öğr.Gör.Ali SEZER║301-303║
║           ║    11.00     ║ Veritabanı Yönetimi  ║ Dr.Öğr.Üyesi HÖ  ║Büyük-A║
║ 14.04.2025║    12.30     ║ Otomata Teorisi      ║ Prof.Dr.Ahmet S  ║303-305║
║           ║    14.00     ║ Elektrik Elektronik  ║ Dr.Öğr.Üyesi BKS ║303-305║
║           ║    15.30     ║ Sayısal Entegre      ║ Doç.Dr.Suhap Ş   ║303-305║
╚═══════════╩══════════════╩═══════════════════════╩═════════════════╩═══════╝
```

## ✨ Özellikler

### 1. **Başlık Satırı (Turuncu Arka Plan)**
- Birleştirilmiş hücre (A1:E1)
- Bölüm adı + Sınav tipi
- Beyaz kalın yazı
- Ortalanmış

### 2. **Kolon Başlıkları (Turuncu Arka Plan)**
- **Tarih**: 12 karakter genişlik
- **Sınav Saati**: 12 karakter genişlik  
- **Ders Adı**: 40 karakter genişlik
- **Öğretim Elemanı**: 25 karakter genişlik
- **Derslik**: 20 karakter genişlik

### 3. **Tarih Hücreleri (Birleştirilmiş)**
- Aynı tarihteki tüm sınavlar için **dikey birleştirme**
- Gri arka plan (#F0F0F0)
- Kalın yazı
- Ortalanmış

### 4. **Veri Hücreleri**
- İnce kenarlıklar (thin borders)
- Sol mavi kalın kenar (thick left border - #3498DB)
- Orta dikey hizalama
- Saat ve Derslik: Ortala
- Ders Adı ve Öğretim Elemanı: Sola yasla

### 5. **Derslik Birleştirme**
Aynı dersin birden fazla derslikte yapıldığı durumda:
```
301-303-305-HKA
```
Tire (-) ile birleştirilir.

## 🎨 Renk Şeması

| Element | Renk Kodu | Kullanım |
|---------|-----------|----------|
| Başlık Arka Plan | `#E67E22` (Turuncu) | Başlık ve kolon başlıkları |
| Başlık Yazı | `#FFFFFF` (Beyaz) | Başlık ve kolon metinleri |
| Tarih Arka Plan | `#F0F0F0` (Açık Gri) | Birleştirilmiş tarih hücreleri |
| Sol Kenar | `#3498DB` (Mavi) | Veri satırlarının sol kenarı |

## 📐 Hücre Boyutları

```python
# Satır yükseklikleri
Başlık Satırı: 25 piksel
Kolon Başlıkları: 20 piksel
Veri Satırları: Otomatik (wrap_text ile)

# Kolon genişlikleri
A (Tarih): 12
B (Sınav Saati): 12
C (Ders Adı): 40
D (Öğretim Elemanı): 25
E (Derslik): 20
```

## 🔧 Kod Örneği

```python
# Başlık satırı oluştur
ws.merge_cells('A1:E1')
title_cell = ws['A1']
title_cell.value = f"{bolum_adi} {sinav_tipi.upper()} SINAV PROGRAMI"
title_cell.font = Font(size=14, bold=True, color="FFFFFF")
title_cell.fill = PatternFill(start_color="E67E22", end_color="E67E22", fill_type="solid")

# Tarih hücrelerini birleştir
if end_row > start_row:
    ws.merge_cells(f'A{start_row}:A{end_row}')
    merged_cell = ws.cell(row=start_row, column=1)
    merged_cell.fill = PatternFill(start_color="F0F0F0", end_color="F0F0F0", fill_type="solid")
```

## 📊 Veri Yapısı

Excel'e aktarılmadan önce veriler şu şekilde gruplanır:

1. **Tarih ve Saate Göre Grupla**
   ```python
   schedule_by_datetime[datetime_key] = [exam1, exam2, ...]
   ```

2. **Aynı Ders için Derslikleri Birleştir**
   ```python
   course_groups[(ders_id, ders_kodu, ders_adi)] = [exam_derslik1, exam_derslik2]
   ```

3. **Excel'e Yaz**
   ```python
   derslikler = '-'.join([exam['derslik_kodu'] for exam in course_exams])
   ws.append([tarih, saat, ders_adi, ogretim_elemani, derslikler])
   ```

## 🎯 Kullanım

1. Sınav programını oluşturun
2. **"📊 Excel'e Aktar"** butonuna tıklayın
3. Dosya adı ve konum seçin
4. Excel dosyası otomatik formatlanmış olarak kaydedilir

## 📝 Notlar

- Öğretim elemanı bilgisi ders tablosundan otomatik çekilir
- Aynı saatte birden fazla ders varsa, tüm dersler alt alta listelenir
- Tarih hücreleri otomatik birleştirilir
- Tüm kenarlıklar ve renkler otomatik uygulanır
- Excel dosyası `openpyxl` kütüphanesi ile oluşturulur

## ⚠️ Gereksinimler

```txt
openpyxl>=3.0.0
```

Bu format tam olarak örnek görseldeki gibi profesyonel bir sınav programı çıktısı sağlar!

