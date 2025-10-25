# Bölüm Seçimi Sistemi - Test Senaryoları

## ✅ Yapılan Değişiklikler

### 1. Yeni Dosyalar
- `views/koordinator/bolum_secim_view.py` - Bölüm seçim ekranı

### 2. Güncellenen Dosyalar
- `views/main_window.py` - Admin akış kontrolü eklendi

## Test Senaryoları

### Senaryo 1: Admin Giriş Yapıyor (Bölüm Seçimi Gerekli)
**Kullanıcı:** `admin@kocaeli.edu.tr` (bolum_id = NULL)
**Şifre:** `admin123`

**Beklenen Davranış:**
1. ✅ Giriş başarılı
2. ✅ Ana sayfa yerine "Bölüm Seçimi" ekranı açılır
3. ✅ Sidebar'da sadece "🎓 Bölüm Seçimi" menüsü görünür
4. ✅ Diğer menülere erişim YOK
5. ✅ Veritabanındaki bölümler (örn: Bilgisayar Mühendisliği) kart olarak görünür
6. ✅ Bir bölüm seçildiğinde:
   - Onay mesajı gösterilir
   - Sidebar yeniden oluşturulur
   - Tüm menüler (Derslikler, Ders Listesi, vb.) erişilebilir hale gelir
   - Seçilen bölüm sidebar'da gösterilir
   - "Bölüm Değiştir" menüsü eklenir

### Senaryo 2: Excel'den Ders Yükleme
**Kullanıcı:** Admin (bölüm seçmiş)

**Adımlar:**
1. Bölüm seç (örn: Bilgisayar Mühendisliği, bolum_id=1)
2. "📚 Ders Listesi" menüsüne git
3. "📤 Excel Yükle" butonuna tıkla
4. `Ders Listesi.xlsx` dosyasını seç
5. Kaydet

**Beklenen Davranış:**
- ✅ Tüm dersler `bolum_id=1` ile kaydedilir
- ❌ "null value in column bolum_id" hatası ALMAMALI
- ✅ Başarı mesajı: "X ders kaydedildi"

### Senaryo 3: Excel'den Öğrenci Yükleme
**Kullanıcı:** Admin (bölüm seçmiş)

**Adımlar:**
1. "👨‍🎓 Öğrenci Listesi" menüsüne git
2. "📤 Excel Yükle" butonuna tıkla
3. Öğrenci Excel dosyasını seç
4. Kaydet

**Beklenen Davranış:**
- ✅ Tüm öğrenciler `bolum_id` ile kaydedilir
- ❌ "null value in column bolum_id" hatası ALMAMALI

### Senaryo 4: Bölüm Değiştirme
**Kullanıcı:** Admin (bölüm seçmiş)

**Adımlar:**
1. "🎓 Bölüm Değiştir" menüsüne tıkla
2. Bölüm seçim ekranı tekrar açılır
3. Farklı bir bölüm seç
4. Sidebar güncellenir

**Beklenen Davranış:**
- ✅ Yeni bölüm seçilir
- ✅ Tüm sayfalar yeni bölüm context'i ile çalışır
- ✅ Dashboard istatistikleri yeni bölüm için gösterilir

### Senaryo 5: Koordinatör Giriş Yapıyor (Bölüm Zaten Var)
**Kullanıcı:** `koordinator.bmu@kocaeli.edu.tr` (bolum_id = 1)
**Şifre:** `admin123`

**Beklenen Davranış:**
1. ✅ Giriş başarılı
2. ✅ Direkt dashboard açılır (bölüm seçimi GEREKMİYOR)
3. ✅ Tüm koordinatör menüleri erişilebilir
4. ❌ "Bölüm Değiştir" menüsü YOK (sadece admin için)

## Kod Değişiklikleri Özeti

### `views/koordinator/bolum_secim_view.py` (YENİ)
```python
class BolumSecimView(QWidget):
    """Department selection view for Admin users"""
    bolum_selected = Signal(dict)
    
    def on_bolum_selected(self, bolum_data):
        """Handle department selection"""
        self.bolum_selected.emit(bolum_data)
```

### `views/main_window.py` (GÜNCELLENDİ)
```python
def __init__(self, user_data, parent=None):
    # Admin için bölüm kontrolü
    self.is_admin = user_data.get('role') == 'Admin'
    self.needs_bolum_selection = self.is_admin and not user_data.get('bolum_id')
    
def on_bolum_selected(self, bolum_data):
    """Handle department selection"""
    # Update user_data with bolum_id
    self.user_data['bolum_id'] = bolum_data['bolum_id']
    self.selected_bolum = bolum_data
    self.needs_bolum_selection = False
    # Recreate sidebar with full menu
    self.recreate_sidebar()
```

## Doğrulama Kontrol Listesi

- [ ] Admin giriş yaptığında bölüm seçim ekranı görünüyor mu?
- [ ] Bölüm seçildiğinde tüm menüler erişilebilir oluyor mu?
- [ ] Excel'den ders yüklendiğinde `bolum_id` doğru kaydediliyor mu?
- [ ] Excel'den öğrenci yüklendiğinde `bolum_id` doğru kaydediliyor mu?
- [ ] Sidebar'da seçilen bölüm görünüyor mu?
- [ ] "Bölüm Değiştir" seçeneği çalışıyor mu?
- [ ] Koordinatör kullanıcısı için normal akış çalışıyor mu?

## Veritabanı Kontrolü

Ders kaydedildikten sonra:
```sql
SELECT ders_id, bolum_id, ders_kodu, ders_adi 
FROM dersler 
WHERE bolum_id IS NOT NULL
ORDER BY ders_id DESC 
LIMIT 10;
```

**Beklenen:** Tüm derslerde `bolum_id` dolu olmalı.


