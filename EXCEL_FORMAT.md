# 📊 Excel Dosya Formatları

Bu dosya, sistem tarafından kabul edilen Excel dosya formatlarını açıklar.

## 📚 Ders Listesi Excel Formatı

**Zorunlu Sütunlar:**
- `Ders Kodu` - Dersin kodu (örn: BIL101)
- `Ders Adı` - Dersin adı (örn: Programlama I)

**Opsiyonel Sütunlar:**
- `Öğretim Elemanı` - Dersi veren hoca adı (varsayılan: "Belirtilmemiş")
- `Sınıf` - Dersin hangi sınıfa ait olduğu (varsayılan: 1)
- `Ders Yapısı` - "Zorunlu" veya "Seçmeli" (varsayılan: "Zorunlu")

**Örnek Excel:**
```
| Ders Kodu | Ders Adı           | Öğretim Elemanı    | Sınıf | Ders Yapısı |
|-----------|--------------------|--------------------|-------|-------------|
| BIL101    | Programlama I      | Prof. Dr. Ali YILMAZ | 1     | Zorunlu     |
| MAT101    | Matematik I        | Doç. Dr. Ayşe KAYA | 1     | Zorunlu     |
| FIZ101    | Fizik I            | Dr. Mehmet DEMİR   | 1     | Seçmeli     |
```

---

## 👨‍🎓 Öğrenci Listesi Excel Formatı

**Zorunlu Sütunlar:**
- `Öğrenci No` - Öğrenci numarası (örn: 20210101001)
- `Ad Soyad` - Öğrencinin adı ve soyadı

**Opsiyonel Sütunlar:**
- `Sınıf` - Öğrencinin sınıfı (varsayılan: 1)

**Örnek Excel:**
```
| Öğrenci No  | Ad Soyad        | Sınıf |
|-------------|-----------------|-------|
| 20210101001 | Ahmet YILMAZ    | 1     |
| 20210101002 | Ayşe KAYA       | 1     |
| 20200101015 | Mehmet DEMİR    | 2     |
```

---

## 🏛 Derslik Listesi Excel Formatı

**Zorunlu Sütunlar:**
- `Derslik Kodu` - Derslik kodu (örn: A101)
- `Derslik Adı` - Derslik adı (örn: Amfi-1)
- `Kapasite` - Derslik kapasitesi

**Opsiyonel Sütunlar:**
- `Satır Sayısı` - Sıra satır sayısı (varsayılan: 10)
- `Sütun Sayısı` - Sıra sütun sayısı (varsayılan: 6)
- `Sıra Yapısı` - Araya bırakılacak sıra (varsayılan: 3)

**Örnek Excel:**
```
| Derslik Kodu | Derslik Adı | Kapasite | Satır Sayısı | Sütun Sayısı | Sıra Yapısı |
|--------------|-------------|----------|--------------|--------------|-------------|
| A101         | Amfi-1      | 120      | 15           | 8            | 3           |
| B201         | Lab-1       | 40       | 8            | 5            | 2           |
| C301         | 301         | 60       | 10           | 6            | 3           |
```

---

## 📝 Notlar

1. **Sütun İsimleri:** Sistem, sütun isimlerini büyük/küçük harf duyarlı değildir.
   - ✅ "Ders Kodu", "ders kodu", "DERS KODU" hepsi kabul edilir
   - ✅ Türkçe karakterler kullanılabilir: "Öğrenci No", "Sınıf"

2. **Alternatif İsimler:** Bazı sütunlar için alternatif isimler kullanılabilir:
   - Öğretim Elemanı: "Hoca", "Öğretim Elemanı"
   - Sınıf: "Dönem", "Sınıf"
   - Ders Yapısı: "Tür", "Tip", "Ders Yapısı"

3. **Dosya Formatı:** `.xlsx` veya `.xls` formatında olmalıdır.

4. **Boş Satırlar:** Excel dosyasında boş satırlar varsa otomatik olarak atlanır.

5. **Hata Mesajları:** Eksik veya hatalı sütunlar için açıklayıcı hata mesajları gösterilir.

---

## ⚠️ Sık Karşılaşılan Hatalar

### "Eksik sütunlar" Hatası
**Sebep:** Zorunlu sütunlar Excel'de bulunamadı.
**Çözüm:** Zorunlu sütunların doğru isimlerle eklendiğinden emin olun.

### "Excel dosyası okunamadı" Hatası
**Sebep:** Dosya formatı hatalı veya bozuk.
**Çözüm:** Dosyayı `.xlsx` formatında kaydedin ve tekrar deneyin.

### Encoding Hatası
**Sebep:** Türkçe karakterler düzgün görünmüyor.
**Çözüm:** Excel'i UTF-8 encoding ile kaydedin.

---

## 🔧 Örnek Dosyalar

Sistem, `examples/` klasöründe örnek Excel dosyaları içerir:
- `ornek_ders_listesi.xlsx`
- `ornek_ogrenci_listesi.xlsx`
- `ornek_derslik_listesi.xlsx`

Bu dosyaları kullanarak kendi verilerinizi hazırlayabilirsiniz.

