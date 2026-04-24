# 🇮🇩 Inflasi dan Pangan

Dashboard interaktif untuk analisis data inflasi nasional (BPS) dan harga pangan strategis (PIHPS) berbasis **Python Flask** + **Alpine.js** + **TailwindCSS** + **Chart.js**.

---

## 📊 Fitur Utama

| Fitur | Deskripsi |
|---|---|
| **KPI Ringkasan** | Inflasi YoY, MtM, YTD terbaru dengan delta vs bulan sebelumnya |
| **Tren Inflasi** | Line chart interaktif multi-provinsi dengan search dan download |
| **Distribusi Spasial** | Peta choropleth interaktif inflasi per provinsi dengan filter kategori |
| **Heatmap Harga Pangan** | Heatmap harga komoditas pangan dengan color coding perubahan harga |
| **Top 3 Inflasi Daerah** | 3 provinsi inflasi tertinggi dengan selector YoY/MtM/YTD |
| **Perbandingan Regional** | Komparasi inflasi nasional vs regional |
| **Top Komoditas Penyumbang** | 3 komoditas dengan kenaikan harga tertinggi |
| **Dark Mode** | Toggle tema gelap/terang dengan persistence |
| **Export PDF/PNG** | Export dashboard ke format PDF atau PNG |
| **Mobile Responsive** | Design responsif untuk berbagai ukuran layar |
| **Loading States** | Skeleton screens dan loading indicators |
| **Animated Transitions** | Transisi animasi saat perubahan data |
| **Caching** | Server-side caching untuk performa lebih cepat |
| **Error Boundary** | Graceful error handling |
| **Data Quality Indicator** | Indikator kualitas data |

---

## 🗂️ Struktur Proyek

```
DQLAB Porto/
├── backend/                  # Python Flask API
│   ├── app.py                # Semua endpoint API
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── templates/
│   │   ├── base.html         # Base template dengan Alpine.js
│   │   └── index.html        # Halaman dashboard utama
│   └── data/
│       ├── BPS/
│       │   ├── BPS_Inflasi_WideFormat.csv
│       │   ├── BPS_Inflasi_LongFormat.csv
│       │   └── Inflasi data Excel files
│       ├── PIHPS/
│       │   ├── PIHPS_Joined_Provinsi_Komoditas.csv
│       │   └── Data harga per provinsi Excel files
│       ├── indonesia_provinces.geojson
│       └── logo.png
│
└── Data/                     # Raw data files
```

---

## 🚀 Cara Menjalankan

### Local Development

#### 1. Install Dependencies
```bash
cd backend
pip install flask flask-cors flask-caching pandas numpy folium openpyxl
```

#### 2. Run Server
```bash
python3 app.py
# → Dashboard berjalan di http://localhost:5000
```

### Docker (Production)
```bash
docker-compose up --build
# → Dashboard: http://localhost:5000
```

---

## 🔌 Endpoint API Flask

| Method | Path | Deskripsi |
|---|---|---|
| GET | `/api/kpi` | KPI nasional (YoY, MtM, YTD) |
| GET | `/api/tren-inflasi?provinsi=INDONESIA&tipe=YoY` | Data tren inflasi |
| GET | `/api/top-inflasi?type=yoy` | 3 provinsi inflasi tertinggi |
| GET | `/api/komoditas-list` | Daftar komoditas |
| GET | `/api/harga-summary` | Ringkasan harga semua komoditas |
| GET | `/api/period-list` | Daftar periode data |
| GET | `/api/provinsi-list` | Daftar nama provinsi |
| GET | `/api/regional-inflasi` | Rata-rata inflasi per region |
| GET | `/api/commodity-range` | Min, max, avg harga per komoditas |
| GET | `/api/price-index-provinsi` | Index harga per provinsi |
| GET | `/api/top-komoditas-provinsi` | Top komoditas per provinsi |
| GET | `/api/heatmap-harga-pangan` | Data heatmap harga pangan |
| GET | `/api/map-inflasi?tipe=YoY` | HTML peta folium inflasi |
| GET | `/api/map/<komoditas>` | HTML peta folium harga komoditas |
| GET | `/data/<filename>` | Serve static files dari Data directory |

---

## 📁 Sumber Data

| Dataset | Sumber | Periode |
|---|---|---|
| `BPS_Inflasi_*` | Badan Pusat Statistik | Jan 2024 – Apr 2026 |
| `PIHPS_*` | Pusat Informasi Harga Pangan Strategis | Jan 2024 – Apr 2026 |

---

## 🗺️ Catatan Peta

Peta choropleth menggunakan data GeoJSON Indonesia dari file `indonesia_provinces.geojson`. Peta dirender menggunakan library Folium dan di-embed via `<iframe>`.

---

## 🛠️ Teknologi

- **Backend**: Python 3.14, Flask 3.1, Pandas, NumPy, Flask-Caching
- **Frontend**: Alpine.js 3.x, TailwindCSS, Chart.js
- **Charts**: Chart.js (Line Chart, Bubble Chart)
- **Map**: Folium (choropleth + tooltip)
- **Export**: html2canvas, jsPDF
- **Deploy**: Docker + Docker Compose

---

## 📝 Fitur Tambahan

### Caching
- Server-side caching dengan FileSystemCache (timeout: 10 menit)
- Cache headers untuk static files (1 hour)
- @lru_cache untuk data loading functions

### Performance
- Responsive grid system (mobile-friendly)
- Loading skeleton screens
- Animated transitions dengan staggered delays
- Error boundary untuk graceful error handling

### UX Enhancements
- Dark mode dengan localStorage persistence
- Interactive tooltips dengan detail informasi
- Data quality indicators
- Export dashboard ke PDF/PNG
