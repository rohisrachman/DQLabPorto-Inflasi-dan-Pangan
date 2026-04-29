from flask import Flask, jsonify, request, Response, render_template, send_from_directory
from flask_cors import CORS
from flask_caching import Cache
import pandas as pd
import numpy as np
import folium
import json
import urllib.request
import os
import re
from functools import lru_cache

app = Flask(__name__, template_folder='backend/templates')
CORS(app)

# Configure caching - use SimpleCache for serverless environments
cache_config = {
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 600  # 10 minutes
}
cache = Cache(app, config=cache_config)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/data/<path:filename>")
def serve_data(filename):
    """Serve files from the Data directory with cache headers."""
    data_dir = os.path.join(os.path.dirname(__file__), 'Data')
    response = send_from_directory(data_dir, filename)
    response.headers['Cache-Control'] = 'public, max-age=3600'  # 1 hour cache
    return response


@app.route("/api")
def api_docs():
    return jsonify({
        "endpoints": {
            "GET /api/harga-latest?komoditas=Beras": "Harga terbaru per kota",
            "GET /api/harga-summary": "Ringkasan harga semua komoditas",
            "GET /api/harga-tren?komoditas=Beras": "Tren harga komoditas",
            "GET /api/inflasi-peta?tipe=YoY": "Data choropleth per provinsi",
            "GET /api/komoditas-list": "Daftar komoditas",
            "GET /api/kpi": "KPI nasional (YoY, MoM, YTD) + Harga Komoditas",
            "GET /api/map-inflasi?tipe=YoY": "HTML peta folium inflasi",
            "GET /api/map/<komoditas>": "HTML peta folium harga komoditas",
            "GET /api/period-list": "Daftar periode data",
            "GET /api/provinsi-list": "Daftar nama provinsi",
            "GET /api/top-inflasi": "10 provinsi inflasi tertinggi",
            "GET /api/tren-inflasi?provinsi=INDONESIA&tipe=YoY": "Data tren inflasi",
            "GET /api/regional-inflasi": "Rata-rata inflasi per region (Jawa, Sumatera, dll)",
            "GET /api/commodity-range": "Range harga (min/max/avg) per komoditas",
            "GET /api/price-index-provinsi": "Indeks harga gabungan per provinsi"
        },
        "message": "Dashboard Inflasi Indonesia API",
        "version": "1.1.0"
    })

DATA_DIR = os.path.join(os.path.dirname(__file__), "backend/data")
PROJECT_ROOT = os.path.dirname(__file__)
INFLASI_FILE = os.path.join(PROJECT_ROOT, "BPS_Inflasi_WideFormat_Datetime.xlsx")
PIHPS_FILE = os.path.join(PROJECT_ROOT, "PIHPS_Provinsi_WideFormat.csv")
GEOJSON_FILE = os.path.join(PROJECT_ROOT, "Data", "38 Provinsi Indonesia - Provinsi.json")

TIPE_MOM = "Inflasi Bulanan (M-to-M) 38 Provinsi (2022=100)"
TIPE_YTD = "Inflasi Tahun Kalender (Y-to-D) 38 Provinsi (2022=100)"
TIPE_YOY = "Inflasi Tahunan (Y-on-Y) 38 Provinsi (2022=100)"


# ── helpers ──────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def load_inflasi():
    df = pd.read_excel(INFLASI_FILE)
    date_cols = [c for c in df.columns if re.match(r"\d{4}-\d{2}", str(c))]
    # Filter out April-December 2026 data
    date_cols = [c for c in date_cols if not (str(c).startswith("2026-") and int(str(c).split("-")[1]) >= 4)]
    return df, date_cols


@lru_cache(maxsize=1)
def load_pihps():
    try:
        df = pd.read_csv(PIHPS_FILE)
    except FileNotFoundError:
        # Try alternative paths for Vercel deployment
        alt_paths = [
            os.path.join(os.path.dirname(__file__), "PIHPS_Provinsi_WideFormat.csv"),
            os.path.join(os.path.dirname(__file__), "Data/PIHPS/PIHPS_Avg_Price_By_Province.xlsx"),
            "PIHPS_Provinsi_WideFormat.csv",
            "Data/PIHPS/PIHPS_Avg_Price_By_Province.xlsx"
        ]
        df = None
        for path in alt_paths:
            try:
                if path.endswith('.xlsx'):
                    df = pd.read_excel(path)
                else:
                    df = pd.read_csv(path)
                print(f"Loaded PIHPS data from: {path}")
                break
            except:
                continue
        
        if df is None:
            raise FileNotFoundError(f"PIHPS data file not found. Tried: {PIHPS_FILE}, {alt_paths}")
    
    date_cols = [c for c in df.columns if re.match(r"[A-Za-z]+ \d{4}", str(c))]
    # parse prices
    for col in date_cols:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")
    return df, date_cols


def safe_val(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return round(float(v), 4)
    return v


def download_geojson():
    global GEOJSON_FILE
    if os.path.exists(GEOJSON_FILE):
        return
        
    # Fallback to /tmp for Serverless environments (read-only filesystem)
    GEOJSON_FILE = "/tmp/indonesia_provinces.geojson"
    if os.path.exists(GEOJSON_FILE):
        return

    url = "https://raw.githubusercontent.com/superpikar/indonesia-geojson/master/indonesia-edit.json"
    try:
        req = urllib.request.urlopen(url, timeout=30)
        with open(GEOJSON_FILE, "wb") as f:
            f.write(req.read())
    except Exception as e:
        print(f"GeoJSON download failed: {e}")


# normalise province names so inflasi & geojson match
PROVINCE_MAP = {
    "ACEH": ["aceh", "nanggroe aceh darussalam", "nanggroe aceh darussalam (nad)"],
    "SUMATERA UTARA": ["sumatera utara", "north sumatra"],
    "SUMATERA BARAT": ["sumatera barat", "west sumatra"],
    "RIAU": ["riau"],
    "KEPULAUAN RIAU": ["kepulauan riau", "riau islands"],
    "JAMBI": ["jambi"],
    "BENGKULU": ["bengkulu"],
    "SUMATERA SELATAN": ["sumatera selatan", "south sumatra"],
    "BANGKA BELITUNG": ["kepulauan bangka belitung", "bangka belitung islands", "bangka belitung"],
    "LAMPUNG": ["lampung"],
    "BANTEN": ["banten"],
    "DKI JAKARTA": ["dki jakarta", "jakarta"],
    "JAWA BARAT": ["jawa barat", "west java"],
    "JAWA TENGAH": ["jawa tengah", "central java"],
    "DI YOGYAKARTA": ["di yogyakarta", "yogyakarta"],
    "JAWA TIMUR": ["jawa timur", "east java"],
    "BALI": ["bali"],
    "NUSA TENGGARA BARAT": ["nusa tenggara barat", "west nusa tenggara"],
    "NUSA TENGGARA TIMUR": ["nusa tenggara timur", "east nusa tenggara"],
    "KALIMANTAN BARAT": ["kalimantan barat", "west kalimantan"],
    "KALIMANTAN TENGAH": ["kalimantan tengah", "central kalimantan"],
    "KALIMANTAN SELATAN": ["kalimantan selatan", "south kalimantan"],
    "KALIMANTAN TIMUR": ["kalimantan timur", "east kalimantan"],
    "KALIMANTAN UTARA": ["kalimantan utara", "north kalimantan"],
    "SULAWESI UTARA": ["sulawesi utara", "north sulawesi"],
    "GORONTALO": ["gorontalo"],
    "SULAWESI TENGAH": ["sulawesi tengah", "central sulawesi"],
    "SULAWESI BARAT": ["sulawesi barat", "west sulawesi"],
    "SULAWESI SELATAN": ["sulawesi selatan", "south sulawesi"],
    "SULAWESI TENGGARA": ["sulawesi tenggara", "southeast sulawesi"],
    "MALUKU": ["maluku"],
    "MALUKU UTARA": ["maluku utara", "north maluku"],
    "PAPUA": ["papua"],
    "PAPUA BARAT": ["papua barat", "west papua"],
}

def normalize_province(name):
    name_lower = str(name).lower().strip()
    for std, aliases in PROVINCE_MAP.items():
        if name_lower == std.lower() or name_lower in aliases:
            return std
    return str(name).upper().strip()


# ── API routes ────────────────────────────────────────────────────────────────

@app.route("/api/kpi")
@cache.cached(timeout=300, query_string=True)
def kpi():
    df, date_cols = load_inflasi()
    
    # Get provinsi parameter, default to INDONESIA
    provinsi = request.args.get('provinsi', 'INDONESIA').upper()
    
    # Use specified province row, latest available date with real value
    idn = df[df["Provinsi"] == provinsi]

    def latest_val(tipe):
        row = idn[idn["Tipe_Inflasi"] == tipe]
        if row.empty:
            return None, None
        vals = row[date_cols].iloc[0]
        valid = vals.dropna()
        valid = valid[valid.apply(lambda x: str(x).strip() not in ["-", ""])]
        valid = pd.to_numeric(valid, errors="coerce").dropna()
        if valid.empty:
            return None, None
        return float(round(valid.iloc[-1], 2)), valid.index[-1]

    yoy, yoy_date = latest_val(TIPE_YOY)
    mom, mom_date = latest_val(TIPE_MOM)
    ytd, ytd_date = latest_val(TIPE_YTD)

    # previous period for delta
    def prev_val(tipe):
        row = idn[idn["Tipe_Inflasi"] == tipe]
        if row.empty:
            return None
        vals = pd.to_numeric(row[date_cols].iloc[0], errors="coerce").dropna()
        if len(vals) < 2:
            return None
        return float(round(vals.iloc[-2], 2))

    # Get commodity prices from PIHPS
    df_pihps, date_cols_pihps = load_pihps()
    commodity_kpi = {}
    key_commodities = ['Beras', 'Daging Sapi', 'Telur Ayam Ras', 'Minyak Goreng']
    
    for kom in key_commodities:
        kom_data = df_pihps[df_pihps["Komoditas"] == kom]
        if not kom_data.empty:
            latest_vals = pd.to_numeric(kom_data[date_cols_pihps[-1]], errors="coerce").dropna()
            prev_vals = pd.to_numeric(kom_data[date_cols_pihps[-2]], errors="coerce").dropna()
            if not latest_vals.empty:
                avg = float(latest_vals.mean())
                prev_avg = float(prev_vals.mean()) if not prev_vals.empty else None
                change = round(((avg - prev_avg) / prev_avg * 100) if prev_avg else 0, 2) if prev_avg else 0
                commodity_kpi[kom] = {
                    "value": round(avg, 0),
                    "change": change,
                    "date": date_cols_pihps[-1]
                }

    return jsonify({
        "yoy": {"value": yoy, "date": yoy_date, "prev": prev_val(TIPE_YOY), "region": provinsi},
        "mom": {"value": mom, "date": mom_date, "prev": prev_val(TIPE_MOM), "region": provinsi},
        "ytd": {"value": ytd, "date": ytd_date, "prev": prev_val(TIPE_YTD), "region": provinsi},
        "commodities": commodity_kpi
    })


@app.route("/api/tren-inflasi")
@cache.cached(timeout=300, query_string=True)
def tren_inflasi():
    df, date_cols = load_inflasi()
    provinsi = request.args.get("provinsi", "INDONESIA")
    tipe = request.args.get("tipe", "YoY")
    tipe_map = {"YoY": TIPE_YOY, "MoM": TIPE_MOM, "YTD": TIPE_YTD}
    tipe_col = tipe_map.get(tipe, TIPE_YOY)

    # Handle multiple provinces
    prov_list = [p.strip() for p in provinsi.split(',') if p.strip()]
    
    result = []
    for prov in prov_list:
        row = df[(df["Provinsi"] == prov) & (df["Tipe_Inflasi"] == tipe_col)]
        if not row.empty:
            vals = row[date_cols].iloc[0]
            for d, v in vals.items():
                # Only replace standalone "-" (missing data), not minus signs in negative numbers
                val_str = str(v).strip()
                if val_str == "-":
                    num = None
                else:
                    num = safe_val(pd.to_numeric(val_str, errors="coerce"))
                if num is not None:
                    result.append({"date": str(d), "value": num, "provinsi": prov})

    return jsonify(result)


@app.route("/api/provinsi-list")
@cache.cached(timeout=3600, key_prefix='provinsi-list')
def provinsi_list():
    df, _ = load_inflasi()
    provs = sorted(df["Provinsi"].unique().tolist())
    return jsonify(provs)


@app.route("/api/inflasi-peta")
def inflasi_peta():
    """Return latest inflation value per province for choropleth."""
    df, date_cols = load_inflasi()
    tipe = request.args.get("tipe", "YoY")
    period = request.args.get("period", None)
    tipe_map = {"YoY": TIPE_YOY, "MoM": TIPE_MOM, "YTD": TIPE_YTD}
    tipe_col = tipe_map.get(tipe, TIPE_YOY)

    sub = df[df["Tipe_Inflasi"] == tipe_col].copy()
    sub = sub[sub["Provinsi"] != "INDONESIA"]

    result = []
    for _, row in sub.iterrows():
        vals = pd.to_numeric(row[date_cols], errors="coerce")
        if period and period in vals.index:
            v = vals[period]
        else:
            valid = vals.dropna()
            v = valid.iloc[-1] if not valid.empty else np.nan
        result.append({
            "provinsi": row["Provinsi"],
            "value": safe_val(v)
        })
    return jsonify(result)


@app.route("/api/komoditas-list")
@cache.cached(timeout=3600, key_prefix='komoditas-list')
def komoditas_list():
    df, _ = load_pihps()
    return jsonify(sorted(df["Komoditas"].unique().tolist()))


@app.route("/api/harga-tren")
def harga_tren():
    df, date_cols = load_pihps()
    komoditas = request.args.get("komoditas", "Beras")
    provinsi = request.args.get("provinsi", None)

    sub = df[df["Komoditas"] == komoditas]
    if provinsi:
        sub = sub[sub["name"].str.contains(provinsi, case=False, na=False)]

    if sub.empty:
        return jsonify([])

    # average across all matched rows
    avg = sub[date_cols].mean(numeric_only=True)
    result = [{"date": str(d), "value": safe_val(v)} for d, v in avg.items() if not pd.isna(v)]
    return jsonify(result)


@app.route("/api/harga-latest")
def harga_latest():
    """Latest price per province for each commodity."""
    df, date_cols = load_pihps()
    komoditas = request.args.get("komoditas", "Beras")
    sub = df[df["Komoditas"] == komoditas].copy()

    # get latest non-null price per row
    def latest_price(row):
        vals = pd.to_numeric(row[date_cols], errors="coerce").dropna()
        return float(vals.iloc[-1]) if not vals.empty else None

    sub["latest"] = sub.apply(latest_price, axis=1)
    result = sub[["name", "Provinsi", "latest"]].dropna().to_dict(orient="records")
    return jsonify(result)


@app.route("/api/harga-summary")
@cache.cached(timeout=300, key_prefix='harga-summary')
def harga_summary():
    """Per-commodity latest price stats: national avg, min, max, change."""
    df, date_cols = load_pihps()
    result = []
    for kom in df["Komoditas"].unique():
        sub = df[df["Komoditas"] == kom]
        latest_vals = pd.to_numeric(sub[date_cols[-1]], errors="coerce").dropna()
        prev_vals = pd.to_numeric(sub[date_cols[-2]], errors="coerce").dropna()
        avg = safe_val(latest_vals.mean())
        prev_avg = safe_val(prev_vals.mean())
        chg = round((avg - prev_avg) / prev_avg * 100, 2) if avg and prev_avg else None
        result.append({
            "komoditas": kom,
            "avg": avg,
            "min": safe_val(latest_vals.min()),
            "max": safe_val(latest_vals.max()),
            "change": chg,
            "period": date_cols[-1],
        })
    return jsonify(result)


@app.route("/api/period-list")
@cache.cached(timeout=3600, key_prefix='period-list')
def period_list():
    df, date_cols = load_inflasi()
    return jsonify(date_cols)


@app.route("/api/map-pangan")
def render_map_pangan():
    """Render a folium choropleth map for a given commodity using query parameter."""
    from urllib.parse import unquote
    
    download_geojson()
    
    # Get commodity from query parameter and URL-decode it
    komoditas = request.args.get("komoditas", "")
    komoditas = unquote(komoditas)
    
    return _render_pangan_map(komoditas)


@app.route("/api/map/<komoditas>")
def render_map_legacy(komoditas):
    """Legacy endpoint for backward compatibility - path parameter."""
    from urllib.parse import unquote
    
    # URL-decode the commodity name from path parameter
    komoditas = unquote(komoditas)
    
    return _render_pangan_map(komoditas)


def _render_pangan_map(komoditas):
    """Shared logic for rendering pangan map."""
    download_geojson()

    if not os.path.exists(GEOJSON_FILE):
        return Response("<h3>GeoJSON not available</h3>", content_type="text/html")

    df, date_cols = load_pihps()
    period = request.args.get("period", "")
    with open(GEOJSON_FILE) as f:
        geo = json.load(f)

    sub = df[df["Komoditas"] == komoditas].copy()
    latest_col = date_cols[-1]

    def latest_price(row):
        if period and period in date_cols:
            val = row.get(period)
            if val is None:
                return None
            val = pd.to_numeric(val, errors="coerce")
            return float(val) if not pd.isna(val) else None
        vals = pd.to_numeric(row[date_cols], errors="coerce").dropna()
        return float(vals.iloc[-1]) if not vals.empty else None

    sub["Harga"] = sub.apply(latest_price, axis=1)

    # average per province name
    price_by_prov = sub.groupby("name")["Harga"].mean().reset_index()
    price_by_prov.columns = ["name", "Harga"]
    # Filter out None values for choropleth (folium can't handle None)
    price_by_prov = price_by_prov[price_by_prov["Harga"].notna()]

    # try to match GeoJSON features
    for feat in geo["features"]:
        props = feat["properties"]
        prov_name = props.get("PROVINSI", props.get("state", props.get("name", props.get("Propinsi", ""))))
        match = price_by_prov[price_by_prov["name"].str.lower() == prov_name.lower()]
        if not match.empty:
            val = match["Harga"].values[0]
            harga_value = float(val) if val is not None else None
        else:
            harga_value = None
        props["Harga"] = harga_value
        props["Harga_formatted"] = "{:,.0f}".format(harga_value) if harga_value is not None else "Data belum tersedia"
        props["prov_name"] = prov_name

    m = folium.Map(location=[-2.5489, 118.0149], zoom_start=5, tiles="CartoDB positron")

    folium.Choropleth(
        geo_data=geo,
        data=price_by_prov,
        columns=["name", "Harga"],
        key_on="feature.properties.PROVINSI",
        fill_color="YlOrRd",
        fill_opacity=0.75,
        line_opacity=0.3,
        legend_name=f"Harga {komoditas} (Rp)",
        nan_fill_color="#e2e8f0",
        nan_fill_opacity=0.5,
    ).add_to(m)

    # Add click handler for zoom in/out
    geo_json_layer = folium.GeoJson(
        geo,
        style_function=lambda x: {"fillOpacity": 0, "weight": 0.5, "color": "#94a3b8"},
        tooltip=folium.GeoJsonTooltip(
            fields=["prov_name", "Harga_formatted"],
            aliases=["Provinsi:", f"Harga {komoditas} (Rp):"],
            localize=True,
            sticky=True,
        ),
    ).add_to(m)

    # Add JavaScript for interactive zoom with proper initialization check
    zoom_script = f'''
    <script>
    (function() {{
        var checkMap = setInterval(function() {{
            var map = window.{m.get_name()};
            var geoJsonLayer = window.{geo_json_layer.get_name()};
            
            if (map && geoJsonLayer) {{
                clearInterval(checkMap);
                
                // Add click handler to each feature for zoom in
                geoJsonLayer.eachLayer(function(layer) {{
                    layer.on('click', function(e) {{
                        map.fitBounds(e.target.getBounds());
                    }});
                }});
            }}
        }}, 100);
    }})();
    </script>
    '''
    m.get_root().html.add_child(folium.Element(zoom_script))

    return Response(m._repr_html_(), content_type="text/html")


@app.route("/api/map-inflasi")
def render_map_inflasi():
    """Render folium choropleth for inflation data."""
    download_geojson()

    if not os.path.exists(GEOJSON_FILE):
        return Response("<h3>GeoJSON not available</h3>", content_type="text/html")

    df, date_cols = load_inflasi()
    tipe = request.args.get("tipe", "YoY")
    period = request.args.get("period", "")
    tipe_map = {"YoY": TIPE_YOY, "MoM": TIPE_MOM, "YTD": TIPE_YTD}
    tipe_col = tipe_map.get(tipe, TIPE_YOY)

    sub = df[(df["Tipe_Inflasi"] == tipe_col) & (df["Provinsi"] != "INDONESIA")].copy()

    def latest_val(row):
        if period and period in date_cols:
            val = row.get(period)
            if val is None:
                return None
            val = pd.to_numeric(val, errors="coerce")
            return float(val) if not pd.isna(val) else None
        vals = pd.to_numeric(row[date_cols], errors="coerce").dropna()
        return float(vals.iloc[-1]) if not vals.empty else None

    sub["value"] = sub.apply(latest_val, axis=1)

    with open(GEOJSON_FILE) as f:
        geo = json.load(f)

    # Create mapping from normalized province name to GeoJSON PROVINSI name
    prov_mapping = {}
    for feat in geo["features"]:
        props = feat["properties"]
        prov_name = props.get("PROVINSI", props.get("state", props.get("name", "")))
        norm = normalize_province(prov_name)
        prov_mapping[norm] = prov_name
        match = sub[sub["Provinsi"] == norm]
        if not match.empty:
            val = match["value"].values[0]
            props["inflasi"] = float(val) if val is not None else None
        else:
            props["inflasi"] = None
        props["prov_name"] = prov_name

    # Create data rows with GeoJSON property name for matching
    data_rows = sub[["Provinsi", "value"]].copy()
    data_rows["geo_prov"] = data_rows["Provinsi"].map(prov_mapping)
    data_rows = data_rows[["geo_prov", "value"]]
    # Filter out None values for choropleth (folium can't handle None)
    data_rows = data_rows[data_rows["value"].notna()]

    m = folium.Map(location=[-2.5489, 118.0149], zoom_start=5, tiles="CartoDB positron")

    folium.Choropleth(
        geo_data=geo,
        data=data_rows,
        columns=["geo_prov", "value"],
        key_on="feature.properties.PROVINSI",
        fill_color="RdYlGn_r",
        fill_opacity=0.75,
        line_opacity=0.3,
        legend_name=f"Inflasi {tipe} (%)",
        nan_fill_color="#e2e8f0",
        nan_fill_opacity=0.5,
    ).add_to(m)

    # Add click handler for zoom in/out
    geo_json_layer = folium.GeoJson(
        geo,
        style_function=lambda x: {"fillOpacity": 0, "weight": 0.5, "color": "#94a3b8"},
        tooltip=folium.GeoJsonTooltip(
            fields=["prov_name", "inflasi"],
            aliases=["Provinsi:", f"Inflasi {tipe} (%):"],
            localize=True,
        ),
    ).add_to(m)

    # Add JavaScript for interactive zoom with proper initialization check
    zoom_script = f'''
    <script>
    (function() {{
        var checkMap = setInterval(function() {{
            var map = window.{m.get_name()};
            var geoJsonLayer = window.{geo_json_layer.get_name()};
            
            if (map && geoJsonLayer) {{
                clearInterval(checkMap);
                
                // Add click handler to each feature for zoom in
                geoJsonLayer.eachLayer(function(layer) {{
                    layer.on('click', function(e) {{
                        map.fitBounds(e.target.getBounds());
                    }});
                }});
            }}
        }}, 100);
    }})();
    </script>
    '''
    m.get_root().html.add_child(folium.Element(zoom_script))

    return Response(m._repr_html_(), content_type="text/html")


@app.route("/api/top-inflasi")
@cache.cached(timeout=300, key_prefix='top-inflasi')
def top_inflasi():
    """Top regions by inflation type (YoY/MtM/YTD)."""
    type_param = request.args.get('type', 'yoy')
    
    # Use inflasi data to get top regions by inflation
    df, date_cols = load_inflasi()
    
    # Filter by type and exclude national data
    type_map = {'yoy': TIPE_YOY, 'mom': TIPE_MOM, 'ytd': TIPE_YTD}
    tipe = type_map.get(type_param, TIPE_YOY)
    
    sub = df[(df["Tipe_Inflasi"] == tipe) & (df["Provinsi"] != "INDONESIA")].copy()
    
    def latest_val(row):
        vals = pd.to_numeric(row[date_cols], errors="coerce").dropna()
        return float(round(vals.iloc[-1], 2)) if not vals.empty else None
    
    sub["value"] = sub.apply(latest_val, axis=1)
    sub = sub[["Provinsi", "value"]].dropna().sort_values("value", ascending=False)

    result = sub.head(3).to_dict(orient="records")
    return jsonify(result)


@app.route("/api/regional-inflasi")
@cache.cached(timeout=300, key_prefix='regional-inflasi')
def regional_inflasi():
    """Average inflation by region (Jawa, Sumatera, Kalimantan, Sulawesi, Papua, dll)"""
    df, date_cols = load_inflasi()
    
    # Define regions by provinces
    regions = {
        "Jawa": ["DKI JAKARTA", "JAWA BARAT", "JAWA TENGAH", "DI YOGYAKARTA", "JAWA TIMUR", "BANTEN"],
        "Sumatera": ["ACEH", "SUMATERA UTARA", "SUMATERA BARAT", "RIAU", "JAMBI", "SUMATERA SELATAN", "BENGKULU", "LAMPUNG", "KEPULAUAN BANGKA BELITUNG", "KEPULAUAN RIAU"],
        "Kalimantan": ["KALIMANTAN BARAT", "KALIMANTAN TENGAH", "KALIMANTAN SELATAN", "KALIMANTAN TIMUR", "KALIMANTAN UTARA"],
        "Sulawesi": ["SULAWESI UTARA", "SULAWESI TENGAH", "SULAWESI SELATAN", "SULAWESI TENGGARA", "SULAWESI BARAT", "GORONTALALO"],
        "Bali-Nusa": ["BALI", "NUSA TENGGARA BARAT", "NUSA TENGGARA TIMUR"],
        "Maluku-Papua": ["MALUKU", "MALUKU UTARA", "PAPUA", "PAPUA BARAT", "PAPUA SELATAN", "PAPUA TENGAH", "PAPUA PEGUNUNGAN"]
    }
    
    result = []
    for region_name, provinces in regions.items():
        region_data = df[df["Provinsi"].isin(provinces)]
        yoy_data = region_data[region_data["Tipe_Inflasi"] == TIPE_YOY]
        if not yoy_data.empty:
            vals = pd.to_numeric(yoy_data[date_cols[-1]], errors="coerce").dropna()
            if not vals.empty:
                result.append({
                    "region": region_name,
                    "value": float(vals.mean()),
                    "count": len(vals)
                })
    
    return jsonify(result)


@app.route("/api/commodity-range")
@cache.cached(timeout=300, key_prefix='commodity-range')
def commodity_range():
    """Min, max, and average price for each commodity"""
    df, date_cols = load_pihps()
    result = []
    
    for kom in df["Komoditas"].unique():
        kom_data = df[df["Komoditas"] == kom]
        latest_vals = pd.to_numeric(kom_data[date_cols[-1]], errors="coerce").dropna()
        if not latest_vals.empty:
            result.append({
                "commodity": kom,
                "min": float(latest_vals.min()),
                "max": float(latest_vals.max()),
                "avg": float(latest_vals.mean()),
                "count": len(latest_vals)
            })
    
    return jsonify(sorted(result, key=lambda x: x["avg"], reverse=True)[:10])


@app.route("/api/price-index-provinsi")
@cache.cached(timeout=300, key_prefix='price-index-provinsi')
def price_index_provinsi():
    """Combined price index by province (average of key commodities)"""
    df, date_cols = load_pihps()
    key_commodities = ['Beras', 'Daging Sapi', 'Telur Ayam Ras', 'Minyak Goreng']
    
    result = []
    for prov in df["Provinsi"].unique():
        prov_data = df[df["Provinsi"] == prov]
        commodity_data = prov_data[prov_data["Komoditas"].isin(key_commodities)]
        if not commodity_data.empty:
            latest_vals = pd.to_numeric(commodity_data[date_cols[-1]], errors="coerce").dropna()
            if not latest_vals.empty:
                result.append({
                    "provinsi": prov,
                    "index": float(latest_vals.mean()),
                    "commodity_count": len(commodity_data["Komoditas"].unique())
                })
    
    return jsonify(sorted(result, key=lambda x: x["index"], reverse=True)[:10])


@app.route("/api/top-komoditas-provinsi")
@cache.cached(timeout=300, key_prefix='top-komoditas-provinsi')
def top_komoditas_provinsi():
    """Top commodities with highest price increase by province"""
    df, date_cols = load_pihps()
    result = []
    
    for kom in df["Komoditas"].unique():
        kom_data = df[df["Komoditas"] == kom]
        if kom_data.empty:
            continue
            
        # Calculate price change per province
        prov_changes = []
        for prov in kom_data["Provinsi"].unique():
            prov_kom_data = kom_data[kom_data["Provinsi"] == prov]
            latest_val = pd.to_numeric(prov_kom_data[date_cols[-1]], errors="coerce").mean()
            prev_val = pd.to_numeric(prov_kom_data[date_cols[-2]], errors="coerce").mean()
            
            if pd.notna(latest_val) and pd.notna(prev_val) and prev_val > 0:
                change_pct = ((latest_val - prev_val) / prev_val * 100)
                prov_changes.append({
                    "provinsi": prov,
                    "change": round(change_pct, 2),
                    "latest_price": round(latest_val, 0)
                })
        
        if prov_changes:
            # Find the province with highest increase for this commodity
            max_change = max(prov_changes, key=lambda x: x["change"])
            result.append({
                "komoditas": kom,
                "provinsi": max_change["provinsi"],
                "change": max_change["change"],
                "latest_price": max_change["latest_price"],
                "date": date_cols[-1]
            })
    
    # Sort by change percentage (highest first)
    result.sort(key=lambda x: x["change"], reverse=True)
    return jsonify(result[:3])


@app.route("/api/heatmap-harga-pangan")
@cache.cached(timeout=300, key_prefix='heatmap-harga-pangan')
def heatmap_harga_pangan():
    """Food price heatmap data with time on X-axis and commodities on Y-axis"""
    df, date_cols = load_pihps()
    
    # Focus on food commodities (pangan) - use exact names from data
    food_commodities = ["Beras", "Gula Pasir", "Minyak Goreng", "Daging Sapi", "Telur Ayam", "Bawang Merah", "Bawang Putih", "Cabai Merah", "Cabai Rawit"]
    
    # Filter to food commodities
    df_filtered = df[df["Komoditas"].isin(food_commodities)]
    
    # Calculate national average by grouping by commodity and averaging across all provinces
    df_national = df_filtered.groupby("Komoditas")[date_cols].mean().reset_index()
    
    # Get last 6 months of data
    recent_months = date_cols[-6:]
    
    # Format month labels
    month_labels = []
    for col in recent_months:
        try:
            # Parse date like "2024-03" to "Mar"
            parts = col.split("-")
            if len(parts) == 2:
                year, month = parts
                month_names = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
                month_idx = int(month) - 1
                month_labels.append(month_names[month_idx])
            else:
                month_labels.append(col)
        except:
            month_labels.append(col)
    
    # Build data structure with prices and changes
    data = {}
    changes = {}
    all_prices = []
    
    for _, row in df_national.iterrows():
        kom = row["Komoditas"]
        prices = []
        price_changes = []
        
        for idx, col in enumerate(recent_months):
            price = pd.to_numeric(row[col], errors="coerce")
            if pd.notna(price):
                prices.append(price)
                all_prices.append(price)
                
                # Calculate change from previous period
                if idx > 0 and pd.notna(prices[idx - 1]):
                    prev_price = prices[idx - 1]
                    change_pct = ((price - prev_price) / prev_price * 100)
                    price_changes.append(change_pct)
                else:
                    price_changes.append(0)  # First period has no change
            else:
                prices.append(0)
                price_changes.append(0)
        
        data[kom] = prices
        changes[kom] = price_changes
    
    # Calculate min and max for color scaling
    min_price = min(all_prices) if all_prices else 0
    max_price = max(all_prices) if all_prices else 0
    
    return jsonify({
        "months": month_labels,
        "data": data,
        "changes": changes,
        "minPrice": min_price,
        "maxPrice": max_price
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
