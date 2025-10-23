# 🎓 Kocaeli Üniversitesi Sınav Takvimi Yönetim Sistemi

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-Proprietary-red.svg)

Professional exam scheduling and management system for Kocaeli University.

---

## 📋 İçindekiler

- [Özellikler](#-özellikler)
- [Sistem Gereksinimleri](#-sistem-gereksinimleri)
- [Kurulum](#-kurulum)
- [Yapılandırma](#-yapılandırma)
- [Kullanım](#-kullanım)
- [Proje Yapısı](#-proje-yapısı)
- [Teknolojiler](#-teknolojiler)
- [Katkıda Bulunma](#-katkıda-bulunma)

---

## ✨ Özellikler

### 🎯 Temel Özellikler
- ✅ **Otomatik Sınav Programı Oluşturma** - Akıllı algoritmalarla çakışmasız program
- ✅ **Derslik Yönetimi** - Kapasite ve yerleşim planı ile derslik yönetimi
- ✅ **Öğrenci & Ders Yönetimi** - Excel ile toplu veri yükleme
- ✅ **Oturma Planı** - Otomatik oturma düzeni oluşturma
- ✅ **Raporlama** - PDF ve Excel formatında detaylı raporlar
- ✅ **Güvenli Kimlik Doğrulama** - BCrypt ile şifrelenmiş giriş sistemi

### 🎨 Kullanıcı Arayüzü
- Modern ve profesyonel PySide6 arayüzü
- Responsive tasarım
- Dark/Light tema desteği
- Animasyonlu geçişler
- Kullanıcı dostu formlar

### 🔒 Güvenlik
- Şifreli veritabanı bağlantıları
- BCrypt password hashing
- Role-based access control (RBAC)
- Session yönetimi
- SQL injection koruması

---

## 💻 Sistem Gereksinimleri

### Yazılım
- **Python**: 3.8 veya üzeri
- **PostgreSQL**: 12.0 veya üzeri
- **İşletim Sistemi**: Windows 10/11, macOS 10.14+, Linux (Ubuntu 20.04+)

### Donanım (Minimum)
- **İşlemci**: Dual-core 2.0 GHz
- **RAM**: 4 GB
- **Disk**: 1 GB boş alan
- **Ekran**: 1280x720 çözünürlük

### Donanım (Önerilen)
- **İşlemci**: Quad-core 2.5 GHz veya üzeri
- **RAM**: 8 GB veya üzeri
- **Disk**: 5 GB boş alan (SSD önerilir)
- **Ekran**: 1920x1080 veya üzeri çözünürlük

---

## 🚀 Kurulum

### 1. Projeyi Klonlayın
```bash
git clone https://github.com/your-org/sinav-takvimi-sistemi.git
cd sinav-takvimi-sistemi
```

### 2. Sanal Ortam Oluşturun
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### 4. Veritabanını Kurun
```bash
# PostgreSQL'e bağlanın
psql -U postgres

# SQL dosyasını çalıştırın
\i sinav_takvimi_final.sql
```

### 5. Ortam Değişkenlerini Ayarlayın
```bash
# .env dosyası oluşturun (örnek dosyadan kopyalayın)
cp .env.example .env

# .env dosyasını düzenleyin
nano .env  # veya tercih ettiğiniz editör
```

### 6. Uygulamayı Çalıştırın
```bash
python main.py
```

---

## ⚙ Yapılandırma

### Veritabanı Ayarları (.env)
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sinav_takvimi_db
DB_USER=postgres
DB_PASSWORD=your_password_here
```

### Uygulama Ayarları
```env
APP_ENV=production
APP_DEBUG=False
APP_LOG_LEVEL=INFO
PASSWORD_MIN_LENGTH=8
SESSION_TIMEOUT=480
```

### Sınav Varsayılan Ayarları
```env
DEFAULT_EXAM_DURATION=120
DEFAULT_BREAK_DURATION=30
MAX_EXAMS_PER_DAY=3
```

---

## 📖 Kullanım

### İlk Giriş
1. Uygulamayı başlatın: `python main.py`
2. Varsayılan kullanıcılardan biriyle giriş yapın:
   - **Admin**: `admin@kocaeli.edu.tr` / `admin123`
   - **Koordinatör**: `koordinator.bmu@kocaeli.edu.tr` / `koordinator123`

### Derslik Ekleme
1. Ana menüden **Derslikler** sekmesine gidin
2. **Yeni Derslik Ekle** butonuna tıklayın
3. Derslik bilgilerini doldurun
4. **Kaydet** butonuna tıklayın

### Excel İle Toplu Veri Yükleme

#### Ders Listesi Format
```
| Ders Kodu | Ders Adı                  | Kredi | Yarıyıl | Ders Yapısı |
|-----------|---------------------------|-------|---------|-------------|
| BMU101    | Programlamaya Giriş       | 3     | 1       | Zorunlu     |
| BMU102    | Matematik I               | 4     | 1       | Zorunlu     |
```

#### Öğrenci Listesi Format
```
| Öğrenci No | Ad Soyad       | Sınıf | E-posta                   |
|------------|----------------|-------|---------------------------|
| 210101001  | Ahmet Yılmaz   | 2     | ahmet@kocaeli.edu.tr     |
| 210101002  | Ayşe Demir     | 2     | ayse@kocaeli.edu.tr      |
```

### Sınav Programı Oluşturma
1. **Sınav Programı** sekmesine gidin
2. Sınav parametrelerini ayarlayın:
   - Sınav tipi (Vize/Final/Bütünleme)
   - Başlangıç ve bitiş tarihleri
   - Günlük sınav sayısı
   - Sınav süresi
3. **Programı Oluştur** butonuna tıklayın
4. Oluşan programı inceleyin
5. **Programı Kaydet** ile veritabanına kaydedin

### Oturma Planı Oluşturma
1. **Oturma Planı** sekmesine gidin
2. Sınav seçin
3. **Oturma Planı Oluştur** butonuna tıklayın
4. Oluşan planı inceleyin
5. **Planı Kaydet** ile kaydedin

### Rapor Alma
1. **Raporlar** sekmesine gidin
2. Rapor türünü seçin
3. Format seçin (Excel/PDF)
4. Ek seçenekleri işaretleyin
5. **Raporu İndir** butonuna tıklayın

---

## 📁 Proje Yapısı

```
PythonProject/
├── algorithms/                 # Algoritma modülleri
│   ├── __init__.py
│   ├── oturma_planlama.py     # Oturma planı algoritması
│   └── sinav_planlama.py      # Sınav programı algoritması
│
├── config/                     # Yapılandırma dosyaları
│   ├── __init__.py
│   └── database_config.py     # Veritabanı ayarları
│
├── controllers/                # İş mantığı katmanı
│   ├── __init__.py
│   ├── ders_controller.py
│   ├── derslik_controller.py
│   ├── login_controller.py
│   ├── ogrenci_controller.py
│   ├── oturma_controller.py
│   └── sinav_controller.py
│
├── models/                     # Veri erişim katmanı
│   ├── __init__.py
│   ├── bolum_model.py
│   ├── database.py            # Veritabanı bağlantı yöneticisi
│   ├── ders_model.py
│   ├── derslik_model.py
│   ├── ogrenci_model.py
│   ├── oturma_model.py
│   ├── sinav_model.py
│   └── user_model.py
│
├── styles/                     # Tema ve stil dosyaları
│   ├── __init__.py
│   └── theme.py               # Ana tema sistemi
│
├── utils/                      # Yardımcı fonksiyonlar
│   ├── __init__.py
│   ├── excel_parser.py        # Excel dosya işlemleri
│   ├── export_utils.py        # Dışa aktarma araçları
│   ├── password_utils.py      # Şifre güvenliği
│   └── validators.py          # Veri doğrulama
│
├── views/                      # Kullanıcı arayüzü
│   ├── koordinator/           # Koordinatör görünümleri
│   │   ├── __init__.py
│   │   ├── ayarlar_view.py
│   │   ├── ders_yukle_view.py
│   │   ├── derslik_view.py
│   │   ├── ogrenci_yukle_view.py
│   │   ├── oturma_plani_view.py
│   │   ├── raporlar_view.py
│   │   └── sinav_olustur_view.py
│   ├── __init__.py
│   ├── login_view.py          # Giriş ekranı
│   └── main_window.py         # Ana pencere
│
├── logs/                       # Uygulama logları
├── .env.example               # Ortam değişkenleri örneği
├── main.py                    # Uygulama giriş noktası
├── requirements.txt           # Python bağımlılıkları
├── sinav_takvimi_final.sql   # Veritabanı şeması
└── README.md                  # Bu dosya
```

---

## 🛠 Teknolojiler

### Backend
- **Python 3.8+** - Ana programlama dili
- **PostgreSQL 12+** - İlişkisel veritabanı
- **psycopg2** - PostgreSQL adaptörü
- **BCrypt** - Şifre hashleme

### Frontend (GUI)
- **PySide6 (Qt6)** - Modern GUI framework
- **Qt Designer** - UI tasarım araçları

### Data Processing
- **pandas** - Veri işleme ve analiz
- **openpyxl** - Excel dosya işlemleri
- **ReportLab** - PDF oluşturma

### Utilities
- **python-dotenv** - Ortam değişkenleri yönetimi
- **logging** - Uygulama loglama
- **validators** - Veri doğrulama

---

## 📝 Veritabanı Şeması

### Ana Tablolar
- `users` - Kullanıcı bilgileri ve kimlik doğrulama
- `bolumler` - Bölüm tanımları
- `dersler` - Ders bilgileri
- `derslikler` - Derslik tanımları
- `ogrenciler` - Öğrenci kayıtları
- `sinav_programlari` - Sınav program başlıkları
- `sinavlar` - Bireysel sınav kayıtları
- `sinav_derslikleri` - Sınav-derslik ilişkileri
- `oturma_planlari` - Öğrenci oturma düzenleri

### İlişkiler
```
users → bolumler (many-to-one)
dersler → bolumler (many-to-one)
derslikler → bolumler (many-to-one)
ogrenciler → bolumler (many-to-one)
sinavlar → dersler (many-to-one)
sinavlar → sinav_programlari (many-to-one)
oturma_planlari → sinavlar (many-to-one)
oturma_planlari → ogrenciler (many-to-one)
```

---

## 🔐 Güvenlik

### En İyi Uygulamalar
- ✅ Şifreler BCrypt ile hashlenmiş
- ✅ SQL injection koruması (parametreli sorgular)
- ✅ Session timeout mekanizması
- ✅ Role-based access control
- ✅ Hassas bilgiler .env dosyasında
- ✅ Güvenli bağlantı havuzu

### Öneriler
1. **Üretim ortamında:**
   - Güçlü ve benzersiz şifreler kullanın
   - `.env` dosyasını asla commit etmeyin
   - SSL/TLS ile veritabanı bağlantısı yapın
   - Düzenli yedekleme yapın

2. **Kullanıcı yönetimi:**
   - Varsayılan şifreleri değiştirin
   - Minimum 8 karakter, büyük harf, küçük harf ve rakam gerektirin
   - Başarısız giriş denemelerini logla

---

## 🐛 Sorun Giderme

### Veritabanı Bağlantı Hatası
```
Hata: could not connect to server
Çözüm:
1. PostgreSQL servisinin çalıştığından emin olun
2. .env dosyasındaki bağlantı bilgilerini kontrol edin
3. Firewall ayarlarını kontrol edin
```

### Import Hatası
```
Hata: ModuleNotFoundError
Çözüm:
1. pip install -r requirements.txt komutunu çalıştırın
2. Sanal ortamın aktif olduğundan emin olun
```

### Excel Yükleme Hatası
```
Hata: Geçersiz Excel formatı
Çözüm:
1. Excel sütun isimlerinin doğru olduğundan emin olun
2. .xlsx formatını kullanın
3. Örnek dosyaları referans alın
```

---

## 📞 Destek ve İletişim

**Kocaeli Üniversitesi**
- Email: bilgiislem@kocaeli.edu.tr
- Website: www.kocaeli.edu.tr

**Teknik Destek**
- Issue Tracker: GitHub Issues
- Wiki: GitHub Wiki

---

## 📜 Lisans

Bu proje Kocaeli Üniversitesi'ne aittir ve özel lisans altındadır.
Tüm hakları saklıdır © 2025 Kocaeli Üniversitesi

---

## 🙏 Teşekkürler

Bu projeyi geliştiren ekibe ve katkıda bulunan herkese teşekkürler.

---

**⚠️ Not:** Bu uygulama profesyonel bir eğitim kurumu için geliştirilmiştir. 
Üretim ortamında kullanmadan önce kapsamlı testler yapılması önerilir.

