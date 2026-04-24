# 🇮🇩 Dashboard Inflasi Indonesia

Dashboard interaktif untuk analisis data inflasi nasional (BPS) dan harga pangan strategis (PIHPS) berbasis **Python Flask** + **Next.js** + **TailwindCSS**.

---

## 📊 Fitur Utama

| Fitur | Deskripsi |
|---|---|
| **KPI Ringkasan** | Inflasi YoY, MoM, YTD terbaru dengan delta vs bulan lalu |
| **Tren Inflasi** | Line chart interaktif multi-provinsi (hingga 5 sekaligus) |
| **Peta Choropleth** | Peta folium interaktif — inflasi per provinsi & harga per kota |
| **Harga Komoditas** | 10 komoditas PIHPS: tren, rata-rata, min, max |
| **Ranking Provinsi** | Bar chart 10 provinsi inflasi tertinggi |
| **Filter Lengkap** | Jenis inflasi (YoY/MoM/YTD), provinsi, komoditas |

---

## 🗂️ Struktur Proyek

```
inflation-dashboard/
├── backend/                  # Python Flask API
│   ├── app.py                # Semua endpoint API
│   ├── requirements.txt
│   ├── Dockerfile
│   └── data/
│       ├── BPS_Inflasi_WideFormat_Datetime.xlsx
│       └── PIHPS_Provinsi_WideFormat.csv
│
├── frontend/                 # Next.js 14 + TailwindCSS
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx      # Halaman utama (routing antar panel)
│   │   │   ├── layout.tsx
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── KPICards.tsx
│   │   │   ├── TrenInflasiChart.tsx
│   │   │   ├── KomoditasPanel.tsx
│   │   │   ├── PetaPanel.tsx
│   │   │   └── RankingProvinsi.tsx
│   │   └── lib/
│   │       └── api.ts        # Fetch helpers & type definitions
│   ├── next.config.js        # Proxy → Flask :5000
│   ├── tailwind.config.js
│   ├── Dockerfile
│   └── package.json
│
└── docker-compose.yml        # One-command startup
```

---

## 🚀 Cara Menjalankan

### Opsi A — Manual (Development)

#### 1. Backend (Flask)
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
# → API berjalan di http://localhost:5000
```

#### 2. Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev
# → Dashboard berjalan di http://localhost:3000
```

### Opsi B — Docker Compose (Production)
```bash
docker-compose up --build
# → Dashboard: http://localhost:3000
# → API:       http://localhost:5000
```

---

## 🔌 Endpoint API Flask

| Method | Path | Deskripsi |
|---|---|---|
| GET | `/api/kpi` | KPI nasional (YoY, MoM, YTD) |
| GET | `/api/tren-inflasi?provinsi=INDONESIA&tipe=YoY` | Data tren inflasi |
| GET | `/api/inflasi-peta?tipe=YoY` | Data choropleth per provinsi |
| GET | `/api/top-inflasi` | 10 provinsi inflasi tertinggi |
| GET | `/api/harga-summary` | Ringkasan harga semua komoditas |
| GET | `/api/harga-tren?komoditas=Beras` | Tren harga komoditas |
| GET | `/api/harga-latest?komoditas=Beras` | Harga terbaru per kota |
| GET | `/api/map-inflasi?tipe=YoY` | HTML peta folium inflasi |
| GET | `/api/map/<komoditas>` | HTML peta folium harga komoditas |
| GET | `/api/provinsi-list` | Daftar nama provinsi |
| GET | `/api/komoditas-list` | Daftar komoditas |
| GET | `/api/period-list` | Daftar periode data |

---

## 📁 Sumber Data

| Dataset | Sumber | Periode |
|---|---|---|
| `BPS_Inflasi_WideFormat_Datetime.xlsx` | Badan Pusat Statistik | Jan 2024 – Apr 2026 |
| `PIHPS_Provinsi_WideFormat.csv` | Pusat Informasi Harga Pangan Strategis | Jan 2024 – Apr 2026 |

---

## 🗺️ Catatan Peta

Peta choropleth menggunakan data GeoJSON Indonesia dari:
```
https://raw.githubusercontent.com/superpikar/indonesia-geojson/master/indonesia-edit.json
```
File akan diunduh otomatis saat pertama kali endpoint `/api/map/*` atau `/api/map-inflasi` dipanggil. Pastikan backend memiliki koneksi internet saat startup pertama.

---

## 🛠️ Teknologi

- **Backend**: Python 3.11, Flask 3.0, Pandas, Folium, NumPy
- **Frontend**: Next.js 14 (App Router), React 18, TypeScript, TailwindCSS, Recharts
- **Charts**: Recharts (AreaChart, LineChart, BarChart)
- **Map**: Folium (choropleth + tooltip) di-embed via `<iframe>`
- **Deploy**: Docker + Docker Compose
