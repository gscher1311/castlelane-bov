#!/usr/bin/env python3
"""build_bov.py - Castle Lane Triplex BOV - La Canada Flintridge, CA"""

import base64, math, io, os, urllib.request, urllib.parse
from PIL import Image, ImageDraw, ImageFont

IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
OUT_FILE   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

# ─────────────────────────────────────────────────────────────────────────────
# DEAL CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
LIST_PRICE        = 1_300_000
UNITS             = 3
SF                = 2_335
LOT_SF            = 6_098
YEAR_BUILT        = 1952
SUBJECT_LAT       = 34.21673
SUBJECT_LNG       = -118.22614
GSR               = 70_812        # current gross scheduled rent ($5,901/mo × 12)
PF_GSR            = 86_292        # pro forma GSR at market rents ($2,095+$2,548+$2,548=$7,191/mo × 12)
VACANCY_PCT       = 0.0
OTHER_INCOME      = 0
TAX_RATE          = 0.0117        # LA County benchmark rate (1.17%)
INTEREST_RATE     = 0.0625
AMORTIZATION_YRS  = 30
MAX_LTV           = 0.50
TRADE_LOW         = 1_275_000
TRADE_HIGH        = 1_375_000
INCREMENT         = 25_000

CNAME      = "castlelane.laaa.com"
PDF_URL    = (
    "https://laaa-pdf-worker.laaa-team.workers.dev/"
    "?url=https%3A%2F%2F" + CNAME +
    "&filename=Castle-Lane-BOV.pdf"
)

# ─────────────────────────────────────────────────────────────────────────────
# EXPENSE ITEMS (owner actuals 2025 + normalized repairs/service)
# ─────────────────────────────────────────────────────────────────────────────
FIXED_TAX_CUR = 15_210     # reassessed at purchase price ($1,300,000 x 1.17% LA County benchmark)
INS           = 1_918      # owner actual 2025
PEST          = 1_032      # owner actual 2025
UTILITIES     = 2_772      # owner actual 2025 (water; owner-paid)
TRASH         = 1_496      # owner actual 2025
REPAIRS       = 2_250      # normalized; 1952 vintage with new water heater (2025 CapEx credit applied)
SERVICE       = 1_500      # gardener + maintenance contracts

CURRENT_EGI   = GSR        # no vacancy deduction (owner-occupied buyer market)
PF_EGI        = PF_GSR
NON_TAX_FIXED = INS + PEST + UTILITIES + TRASH + REPAIRS + SERVICE   # 10,968
CUR_TOTAL_EXP = FIXED_TAX_CUR + NON_TAX_FIXED                        # 26,178
PF_TOTAL_EXP  = FIXED_TAX_CUR + NON_TAX_FIXED                        # 26,178
CUR_NOI       = CURRENT_EGI - CUR_TOTAL_EXP                          # 44,634
PF_NOI        = PF_EGI - PF_TOTAL_EXP                                # 60,114

# ─────────────────────────────────────────────────────────────────────────────
# GEOCOORDS
# ─────────────────────────────────────────────────────────────────────────────
COMP1_LAT, COMP1_LNG   = 34.208673, -118.233407   # 2511 Hermosa Ave Montrose
COMP2_LAT, COMP2_LNG   = 34.222732, -118.252174   # 3357 Honolulu Ave La Canada Flintridge
COMP3_LAT, COMP3_LNG   = 34.21743,  -118.22638    # 4543 Rockland Pl La Canada Flintridge
RENT2_LAT, RENT2_LNG   = 34.221609, -118.233674   # 2535 Cross St
RENT3_LAT, RENT3_LNG   = 34.228053, -118.246102   # 3055 Foothill Blvd
RENT4_LAT, RENT4_LNG   = 34.2090,   -118.2315     # Montrose area (approx Honolulu Ave)

# ─────────────────────────────────────────────────────────────────────────────
# IMAGE LOADING
# ─────────────────────────────────────────────────────────────────────────────
def load_b64(filename):
    path = os.path.join(IMAGES_DIR, filename)
    if not os.path.exists(path):
        print(f"WARNING: {path} not found")
        return ""
    ext = filename.rsplit(".", 1)[-1].lower()
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, "image/png")
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{data}"

# ─────────────────────────────────────────────────────────────────────────────
# STATIC MAP GENERATOR
# ─────────────────────────────────────────────────────────────────────────────
def generate_static_map(center_lat, center_lng, markers, width=800, height=300, zoom=14):
    n = 2 ** zoom
    tiles_x = math.ceil(width / 256) + 2
    tiles_y = math.ceil(height / 256) + 2
    cx = int((center_lng + 180) / 360 * n)
    lat_rad = math.radians(center_lat)
    cy = int((1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n)
    sx, sy = cx - tiles_x // 2, cy - tiles_y // 2
    big = Image.new("RGB", (tiles_x * 256, tiles_y * 256), (220, 220, 220))
    for tx in range(tiles_x):
        for ty in range(tiles_y):
            url = f"https://tile.openstreetmap.org/{zoom}/{sx+tx}/{sy+ty}.png"
            req = urllib.request.Request(url, headers={"User-Agent": "LAAA-BOV-Builder/1.0"})
            try:
                tile = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=10).read()))
                big.paste(tile, (tx * 256, ty * 256))
            except Exception:
                pass
    offset_px = (center_lng + 180) / 360 * n * 256 - width / 2
    offset_py = (1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n * 256 - height / 2
    cl = int(offset_px - sx * 256)
    ct = int(offset_py - sy * 256)
    cropped = big.crop((cl, ct, cl + width, ct + height))
    draw = ImageDraw.Draw(cropped)
    for m in markers:
        mlat, mlng, label, color = m["lat"], m["lng"], m.get("label", ""), m.get("color", "#1B3A5C")
        px = int((mlng + 180) / 360 * n * 256 - offset_px)
        py = int((1 - math.log(math.tan(math.radians(mlat)) + 1 / math.cos(math.radians(mlat))) / math.pi) / 2 * n * 256 - offset_py)
        r = 14 if label == "S" else 11
        draw.ellipse([px-r, py-r, px+r, py+r], fill=color, outline="white", width=2)
        try:
            font = ImageFont.truetype("arial.ttf", 10)
        except Exception:
            font = ImageFont.load_default()
        if label:
            bbox = draw.textbbox((0, 0), label, font=font)
            tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
            draw.text((px-tw//2, py-th//2-1), label, fill="white", font=font)
    buf = io.BytesIO()
    cropped.save(buf, format="PNG", optimize=True)
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"

def calc_zoom(markers, w=800, h=300):
    if len(markers) <= 1: return 15
    lats = [m["lat"] for m in markers]
    lngs = [m["lng"] for m in markers]
    lspan = max(max(lats)-min(lats), 0.002) * 1.25
    lnspan = max(max(lngs)-min(lngs), 0.002) * 1.25
    zl = math.log2(h / 256 * 360 / lspan) if lspan else 18
    zn = math.log2(w / 256 * 360 / lnspan) if lnspan else 18
    return max(10, min(int(min(zl, zn)), 16))

# ─────────────────────────────────────────────────────────────────────────────
# FINANCIAL CALCULATIONS
# ─────────────────────────────────────────────────────────────────────────────
def calc_loan_constant(rate, years):
    r = rate / 12
    n = years * 12
    return r * (1 + r)**n / ((1 + r)**n - 1) * 12

def calc_principal_yr1(loan, rate, years):
    r = rate / 12
    n = years * 12
    pmt = loan * r * (1 + r)**n / ((1 + r)**n - 1)
    bal = loan
    total = 0
    for _ in range(12):
        interest = bal * r
        principal = pmt - interest
        total += principal
        bal -= principal
    return total

LOAN_CONST = calc_loan_constant(INTEREST_RATE, AMORTIZATION_YRS)

def calc_metrics(price):
    taxes      = round(price * TAX_RATE)   # reassessed at actual purchase price
    cur_egi    = CURRENT_EGI
    pf_egi     = PF_EGI
    cur_exp    = taxes + NON_TAX_FIXED
    pf_exp     = taxes + NON_TAX_FIXED
    cur_noi    = cur_egi - cur_exp
    pf_noi     = pf_egi - pf_exp
    loan       = price * MAX_LTV
    down       = price - loan
    ds         = loan * LOAN_CONST
    cur_cf     = cur_noi - ds
    pf_cf      = pf_noi - ds
    prin       = calc_principal_yr1(loan, INTEREST_RATE, AMORTIZATION_YRS)
    return {
        "price": price, "per_unit": price/UNITS, "per_sf": price/SF,
        "cur_cap": cur_noi/price*100, "pf_cap": pf_noi/price*100,
        "cur_grm": price/GSR, "pf_grm": price/PF_GSR,
        "loan": loan, "down": down, "ds": ds,
        "cur_noi": cur_noi, "pf_noi": pf_noi,
        "cur_egi": cur_egi, "pf_egi": pf_egi,
        "cur_exp": cur_exp, "pf_exp": pf_exp,
        "cur_cf": cur_cf, "pf_cf": pf_cf,
        "coc_cur": cur_cf/down*100 if down else 0,
        "coc_pf": pf_cf/down*100 if down else 0,
        "dcr_cur": cur_noi/ds if ds else 0,
        "dcr_pf": pf_noi/ds if ds else 0,
        "prin": prin,
        "total_ret_cur": (cur_cf+prin)/down*100 if down else 0,
        "total_ret_pf": (pf_cf+prin)/down*100 if down else 0,
        "actual_ltv": loan/price,
    }

M = calc_metrics(LIST_PRICE)

# ─────────────────────────────────────────────────────────────────────────────
# HTML HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def fmt(n, decimals=0):
    if decimals == 0:
        return f"${n:,.0f}"
    return f"${n:,.{decimals}f}"

def pct(n, decimals=2):
    return f"{n:.{decimals}f}%"

def build_metric_card(value, label, sub=""):
    sub_html = f'<span class="metric-sub">{sub}</span>' if sub else ""
    return f'<div class="metric-card"><span class="metric-value">{value}</span><span class="metric-label">{label}</span>{sub_html}</div>'

def leaflet_marker(var, lat, lng, color, label, popup):
    return f"""var {var} = L.marker([{lat},{lng}],{{icon:L.divIcon({{className:'',html:'<div style="background:{color};color:#fff;border-radius:50%;width:26px;height:26px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;border:2px solid #fff;box-shadow:0 2px 4px rgba(0,0,0,.3);">{label}</div>',iconSize:[26,26],iconAnchor:[13,13]}})}}
).addTo({var}Map).bindPopup('{popup}');allMarkers{var}Map.push({var});"""

# ─────────────────────────────────────────────────────────────────────────────
# MAIN BUILD
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("Loading images...")
    IMG = {
        "logo_white":    load_b64("LAAA_Team_White.png"),
        "logo_blue":     load_b64("LAAA_Team_Blue.png"),
        "hero":          load_b64("picture1_street.jpg"),
        "closings_map":  load_b64("closings-map.png"),
        "glen":          load_b64("Glen_Scher.png"),
        "filip":         load_b64("Filip_Niculete.png"),
        "aida":          load_b64("Aida_Memary_Scher.png"),
        "morgan":        load_b64("Morgan_Wetmore.png"),
        "logan":         load_b64("Logan_Ward.png"),
        "luka":          load_b64("Luka_Leader.png"),
        "blake":         load_b64("Blake_Lewitt.png"),
        "alex":          load_b64("Alexandro_Tapia.png"),
        "mike":          load_b64("Mike_Palade.png"),
        "tony":          load_b64("Tony_Dang.png"),
    }

    print("Generating static maps...")
    # Location map (subject only, zoom 15)
    loc_map = generate_static_map(
        SUBJECT_LAT, SUBJECT_LNG,
        [{"lat": SUBJECT_LAT, "lng": SUBJECT_LNG, "label": "S", "color": "#C5A258"}],
        width=800, height=220, zoom=15
    )

    # Sale comps map
    sale_markers = [
        {"lat": SUBJECT_LAT, "lng": SUBJECT_LNG, "label": "S", "color": "#C5A258"},
        {"lat": COMP1_LAT,   "lng": COMP1_LNG,   "label": "1", "color": "#1B3A5C"},
        {"lat": COMP2_LAT,   "lng": COMP2_LNG,   "label": "2", "color": "#1B3A5C"},
        {"lat": COMP3_LAT,   "lng": COMP3_LNG,   "label": "3", "color": "#1B3A5C"},
    ]
    sale_map = generate_static_map(
        SUBJECT_LAT, SUBJECT_LNG, sale_markers,
        width=800, height=300, zoom=calc_zoom(sale_markers)
    )

    # Rent comps map
    rent_markers = [
        {"lat": SUBJECT_LAT, "lng": SUBJECT_LNG, "label": "S", "color": "#C5A258"},
        {"lat": RENT2_LAT,   "lng": RENT2_LNG,   "label": "2", "color": "#1B3A5C"},
        {"lat": RENT3_LAT,   "lng": RENT3_LNG,   "label": "3", "color": "#1B3A5C"},
        {"lat": RENT4_LAT,   "lng": RENT4_LNG,   "label": "4", "color": "#1B3A5C"},
    ]
    rent_map = generate_static_map(
        SUBJECT_LAT, SUBJECT_LNG, rent_markers,
        width=800, height=300, zoom=calc_zoom(rent_markers)
    )

    print("Building pricing matrix...")
    TOP    = LIST_PRICE + 5 * INCREMENT
    BOTTOM = LIST_PRICE - 5 * INCREMENT
    MATRIX_PRICES = list(range(TOP, BOTTOM - 1, -INCREMENT))
    matrix_rows = ""
    for p in MATRIX_PRICES:
        mm = calc_metrics(p)
        cls = ' class="highlight"' if p == LIST_PRICE else ""
        matrix_rows += (
            f'<tr{cls}>'
            f'<td class="num">{fmt(p)}</td>'
            f'<td class="num">{pct(mm["cur_cap"])}</td>'
            f'<td class="num">{pct(mm["pf_cap"])}</td>'
            f'<td class="num">{pct(mm["coc_cur"])}</td>'
            f'<td class="num">{fmt(mm["per_sf"], 0)}</td>'
            f'<td class="num">{fmt(mm["per_unit"])}</td>'
            f'<td class="num">{mm["pf_grm"]:.2f}x</td>'
            f'</tr>\n'
        )

    print("Building operating statement...")
    expense_lines = [
        ("Real Estate Taxes",                FIXED_TAX_CUR, FIXED_TAX_CUR, 1),
        ("Insurance",                        INS,           INS,           2),
        ("Pest Control",                     PEST,          PEST,          3),
        ("Utilities",                        UTILITIES,     UTILITIES,     4),
        ("Trash Removal",                    TRASH,         TRASH,         5),
        ("Repairs &amp; Maintenance",        REPAIRS,       REPAIRS,       6),
        ("Service Contracts",                SERVICE,       SERVICE,       7),
    ]
    os_expense_html = ""
    for label, cur_val, pf_val, nn in expense_lines:
        ref = f' <span class="note-ref">[{nn}]</span>'
        os_expense_html += (
            f'<tr><td>{label}{ref}</td>'
            f'<td class="num">{fmt(cur_val)}</td>'
            f'<td class="num">{fmt(cur_val/UNITS, 0)}</td>'
            f'<td class="num">${cur_val/SF:.2f}</td>'
            f'<td class="num">{cur_val/CURRENT_EGI*100:.1f}%</td></tr>\n'
        )

    # Summary - Financial summary expense table
    def ss_exp(label, cur_val, pf_val):
        return (
            f'<tr><td>{label}</td>'
            f'<td class="num">{fmt(cur_val)}</td>'
            f'<td class="num">{fmt(pf_val)}</td>'
            f'</tr>\n'
        )

    exp_detail_rows = (
        ss_exp("Real Estate Taxes",           FIXED_TAX_CUR, FIXED_TAX_CUR) +
        ss_exp("Insurance",                   INS,       INS) +
        ss_exp("Pest Control",                PEST,      PEST) +
        ss_exp("Utilities",                   UTILITIES, UTILITIES) +
        ss_exp("Trash Removal",               TRASH,     TRASH) +
        ss_exp("Repairs &amp; Maint.",        REPAIRS,   REPAIRS) +
        ss_exp("Service Contracts",           SERVICE,   SERVICE)
    )

    print("Assembling HTML...")

    css = r"""
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Inter', sans-serif; color: #333; line-height: 1.6; background: #fff; }
html { scroll-padding-top: 50px; }
p { margin-bottom: 16px; font-size: 14px; line-height: 1.7; }
.cover { position: relative; min-height: 100vh; display: flex; align-items: center; justify-content: center; text-align: center; color: #fff; overflow: hidden; }
.cover-bg { position: absolute; inset: 0; background-size: cover; background-position: center; filter: brightness(0.45); z-index: 0; }
.cover-content { position: relative; z-index: 2; padding: 60px 40px; max-width: 860px; }
.cover-logo { width: 320px; margin: 0 auto 30px; display: block; filter: drop-shadow(0 2px 8px rgba(0,0,0,0.3)); }
.cover-label { font-size: 13px; font-weight: 500; letter-spacing: 3px; text-transform: uppercase; color: #C5A258; margin-bottom: 18px; }
.cover-title { font-size: 46px; font-weight: 700; letter-spacing: 1px; margin-bottom: 8px; text-shadow: 0 2px 12px rgba(0,0,0,0.3); }
.cover-address { font-size: 16px; font-weight: 400; letter-spacing: 1px; color: rgba(255,255,255,0.85); margin-top: 4px; }
.cover-stats { display: flex; gap: 32px; justify-content: center; flex-wrap: wrap; margin-bottom: 32px; }
.cover-stat { text-align: center; }
.cover-stat-value { display: block; font-size: 26px; font-weight: 600; color: #fff; }
.cover-stat-label { display: block; font-size: 11px; font-weight: 500; text-transform: uppercase; letter-spacing: 1.5px; color: #C5A258; margin-top: 4px; }
.cover-headshots { display: flex; justify-content: center; gap: 40px; margin-top: 24px; margin-bottom: 16px; }
.cover-headshot-wrap { text-align: center; }
.cover-headshot { width: 80px; height: 80px; border-radius: 50%; border: 3px solid #C5A258; object-fit: cover; box-shadow: 0 4px 16px rgba(0,0,0,0.4); }
.cover-headshot-name { font-size: 12px; font-weight: 600; margin-top: 6px; color: #fff; }
.cover-headshot-title { font-size: 10px; color: #C5A258; }
.client-greeting { font-size: 14px; font-weight: 500; color: #C5A258; letter-spacing: 1px; margin-top: 16px; }
.gold-line { height: 3px; background: #C5A258; margin: 20px 0; }
.pdf-float-btn { position: fixed; bottom: 24px; right: 24px; z-index: 9999; padding: 14px 28px; background: #C5A258; color: #1B3A5C; font-size: 14px; font-weight: 700; text-decoration: none; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.35); display: flex; align-items: center; gap: 8px; }
.pdf-float-btn:hover { background: #fff; transform: translateY(-2px); }
.pdf-float-btn svg { width: 18px; height: 18px; fill: currentColor; }
.toc-nav { background: #1B3A5C; padding: 0 12px; display: flex; flex-wrap: nowrap; justify-content: center; align-items: stretch; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 8px rgba(0,0,0,0.15); overflow-x: auto; scrollbar-width: none; }
.toc-nav::-webkit-scrollbar { display: none; }
.toc-nav a { color: rgba(255,255,255,0.85); text-decoration: none; font-size: 11px; font-weight: 500; letter-spacing: 0.3px; text-transform: uppercase; padding: 12px 8px; border-bottom: 2px solid transparent; white-space: nowrap; display: flex; align-items: center; }
.toc-nav a:hover { color: #fff; background: rgba(197,162,88,0.12); border-bottom-color: rgba(197,162,88,0.4); }
.toc-nav a.toc-active { color: #C5A258; font-weight: 600; border-bottom-color: #C5A258; }
.section { padding: 50px 40px; max-width: 1100px; margin: 0 auto; }
.section-alt { background: #f8f9fa; }
.section-title { font-size: 26px; font-weight: 700; color: #1B3A5C; margin-bottom: 6px; }
.section-subtitle { font-size: 13px; color: #C5A258; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 16px; font-weight: 500; }
.section-divider { width: 60px; height: 3px; background: #C5A258; margin-bottom: 30px; }
.sub-heading { font-size: 18px; font-weight: 600; color: #1B3A5C; margin: 30px 0 16px; }
.metrics-grid, .metrics-grid-4 { display: grid; gap: 16px; margin-bottom: 30px; }
.metrics-grid { grid-template-columns: repeat(3, 1fr); }
.metrics-grid-4 { grid-template-columns: repeat(4, 1fr); }
.metric-card { background: #1B3A5C; border-radius: 12px; padding: 24px; text-align: center; color: #fff; }
.metric-value { display: block; font-size: 28px; font-weight: 700; }
.metric-label { display: block; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: rgba(255,255,255,0.6); margin-top: 6px; }
.metric-sub { display: block; font-size: 12px; color: #C5A258; margin-top: 4px; }
table { width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 13px; }
th { background: #1B3A5C; color: #fff; padding: 10px 12px; text-align: left; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
td { padding: 8px 12px; border-bottom: 1px solid #eee; }
tr:nth-child(even) { background: #f5f5f5; }
tr.highlight { background: #FFF8E7 !important; border-left: 3px solid #C5A258; }
tr.summary td { background: #1B3A5C !important; color: #fff !important; font-weight: 700; border-bottom: none; }
td.num, th.num { text-align: right; }
.table-scroll { overflow-x: auto; margin-bottom: 24px; }
.table-scroll table { min-width: 700px; margin-bottom: 0; }
.info-table td { padding: 8px 12px; border-bottom: 1px solid #eee; font-size: 13px; }
.info-table td:first-child { font-weight: 600; color: #1B3A5C; width: 40%; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 30px; }
.tr-tagline { font-size: 24px; font-weight: 600; color: #1B3A5C; text-align: center; padding: 16px 24px; margin-bottom: 20px; border-left: 4px solid #C5A258; background: #FFF8E7; border-radius: 0 4px 4px 0; font-style: italic; }
.tr-map-print { display: none; }
.tr-service-quote { margin: 24px 0; }
.tr-service-quote h3 { font-size: 18px; font-weight: 700; color: #1B3A5C; margin-bottom: 8px; }
.tr-service-quote p { font-size: 14px; line-height: 1.7; }
.bio-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin: 24px 0; }
.bio-card { display: flex; gap: 16px; align-items: flex-start; }
.bio-headshot { width: 100px; height: 100px; border-radius: 50%; border: 3px solid #C5A258; object-fit: cover; flex-shrink: 0; }
.bio-name { font-size: 16px; font-weight: 700; color: #1B3A5C; }
.bio-title { font-size: 11px; color: #C5A258; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
.bio-text { font-size: 13px; line-height: 1.6; color: #444; }
.team-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 12px 0; }
.team-card { text-align: center; padding: 8px; }
.team-headshot { width: 60px; height: 60px; border-radius: 50%; border: 2px solid #C5A258; object-fit: cover; margin: 0 auto 4px; display: block; }
.team-card-name { font-size: 13px; font-weight: 700; color: #1B3A5C; }
.team-card-title { font-size: 10px; color: #C5A258; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }
.costar-badge { text-align: center; background: #FFF8E7; border: 2px solid #C5A258; border-radius: 8px; padding: 20px 24px; margin: 30px auto 24px; max-width: 600px; }
.costar-badge-title { font-size: 22px; font-weight: 700; color: #1B3A5C; }
.costar-badge-sub { font-size: 12px; color: #C5A258; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600; margin-top: 6px; }
.condition-note { background: #FFF8E7; border-left: 4px solid #C5A258; padding: 16px 20px; margin: 24px 0; border-radius: 0 4px 4px 0; font-size: 13px; line-height: 1.6; }
.condition-note-label { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; color: #C5A258; margin-bottom: 8px; }
.achievements-list { font-size: 13px; line-height: 1.8; }
.note-ref { font-size: 9px; color: #C5A258; font-weight: 700; vertical-align: super; }
.mkt-quote { background: #FFF8E7; border-left: 4px solid #C5A258; padding: 16px 24px; margin: 20px 0; border-radius: 0 4px 4px 0; font-size: 15px; font-style: italic; line-height: 1.6; color: #1B3A5C; }
.mkt-channels { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }
.mkt-channel { background: #f0f4f8; border-radius: 8px; padding: 16px 20px; }
.mkt-channel h4 { color: #1B3A5C; font-size: 14px; margin-bottom: 8px; }
.mkt-channel li { font-size: 13px; line-height: 1.5; margin-bottom: 4px; }
.perf-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }
.perf-card { background: #f0f4f8; border-radius: 8px; padding: 16px 20px; }
.perf-card h4 { color: #1B3A5C; font-size: 14px; margin-bottom: 8px; }
.perf-card li { font-size: 13px; line-height: 1.5; margin-bottom: 4px; }
.platform-strip { display: flex; justify-content: center; align-items: center; gap: 20px; flex-wrap: wrap; margin-top: 24px; padding: 14px 20px; background: #1B3A5C; border-radius: 6px; }
.platform-strip-label { font-size: 10px; text-transform: uppercase; letter-spacing: 1.5px; color: #C5A258; font-weight: 600; }
.platform-name { font-size: 12px; font-weight: 600; color: #fff; }
.press-strip { display: flex; justify-content: center; align-items: center; gap: 28px; flex-wrap: wrap; margin: 16px 0 0; padding: 12px 20px; background: #f0f4f8; border-radius: 6px; }
.press-strip-label { font-size: 10px; text-transform: uppercase; letter-spacing: 1.5px; color: #888; font-weight: 600; }
.press-logo { font-size: 13px; font-weight: 700; color: #1B3A5C; letter-spacing: 0.5px; }
.inv-split { display: grid; grid-template-columns: 50% 50%; gap: 24px; }
.inv-left .metrics-grid-4 { grid-template-columns: repeat(2, 1fr); }
.inv-text p { font-size: 13px; line-height: 1.6; margin-bottom: 10px; }
.inv-logo { display: none; }
.inv-right { display: flex; flex-direction: column; gap: 16px; padding-top: 70px; }
.inv-photo { height: 280px; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
.inv-photo img { width: 100%; height: 100%; object-fit: cover; object-position: center; }
.inv-highlights { background: #f0f4f8; border: 1px solid #dce3eb; border-radius: 8px; padding: 16px 20px; flex: 1; }
.inv-highlights h4 { color: #1B3A5C; font-size: 13px; margin-bottom: 8px; }
.inv-highlights li { font-size: 12px; line-height: 1.5; margin-bottom: 5px; }
.loc-grid { display: grid; grid-template-columns: 58% 42%; gap: 28px; align-items: start; }
.loc-left { max-height: 480px; overflow: hidden; }
.loc-left p { font-size: 13.5px; line-height: 1.7; margin-bottom: 14px; }
.loc-right { display: block; max-height: 480px; overflow: hidden; }
.loc-wide-map { width: 100%; height: 200px; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.08); margin-top: 20px; }
.loc-wide-map img { width: 100%; height: 100%; object-fit: cover; object-position: center; }
.prop-grid-4 { display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: auto auto; gap: 20px; }
.os-two-col { display: grid; grid-template-columns: 55% 45%; gap: 24px; align-items: stretch; margin-bottom: 24px; }
.os-right { font-size: 10.5px; line-height: 1.45; color: #555; background: #f8f9fb; border: 1px solid #e0e4ea; border-radius: 6px; padding: 16px 20px; }
.os-right h3 { font-size: 13px; margin: 0 0 8px; }
.os-right p { margin-bottom: 4px; }
.summary-page { margin-top: 24px; border: 1px solid #dce3eb; border-radius: 8px; padding: 20px; background: #fff; }
.summary-banner { text-align: center; background: #1B3A5C; color: #fff; padding: 10px 16px; font-size: 14px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; border-radius: 4px; margin-bottom: 16px; }
.summary-two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start; }
.summary-table { width: 100%; border-collapse: collapse; margin-bottom: 12px; font-size: 12px; border: 1px solid #dce3eb; }
.summary-table th, .summary-table td { padding: 4px 8px; border-bottom: 1px solid #e8ecf0; }
.summary-header { background: #1B3A5C !important; color: #fff !important; padding: 5px 8px !important; font-size: 10px !important; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; }
.summary-table tr.summary td { border-top: 2px solid #1B3A5C; font-weight: 700; background: #f0f4f8; }
.summary-table tr:nth-child(even) { background: #fafbfc; }
.summary-trade-range { text-align: center; margin: 24px auto; padding: 16px 24px; border: 2px solid #1B3A5C; border-radius: 6px; max-width: 480px; }
.summary-trade-label { font-size: 11px; text-transform: uppercase; letter-spacing: 2px; color: #555; font-weight: 600; margin-bottom: 6px; }
.summary-trade-prices { font-size: 26px; font-weight: 700; color: #1B3A5C; }
.price-reveal { margin-top: 24px; }
.tr-page2 { padding: 50px 40px; max-width: 1100px; margin: 0 auto; }
.buyer-split { display: grid; grid-template-columns: 1fr 1fr; gap: 28px; align-items: start; }
.obj-item { margin-bottom: 16px; }
.obj-q { font-weight: 700; color: #1B3A5C; margin-bottom: 4px; font-size: 14px; }
.obj-a { font-size: 13px; color: #444; line-height: 1.6; }
.bp-closing { font-size: 13px; color: #444; margin-top: 12px; font-style: italic; }
.buyer-photo { width: 100%; height: 220px; border-radius: 8px; overflow: hidden; margin-top: 24px; }
.buyer-photo img { width: 100%; height: 100%; object-fit: cover; }
.narrative { font-size: 14px; line-height: 1.7; color: #444; margin-bottom: 16px; }
.leaflet-map { height: 400px; border-radius: 4px; border: 1px solid #ddd; margin-bottom: 30px; z-index: 1; }
.map-fallback { display: none; }
.comp-map-print { display: none; }
.embed-map-wrap { position: relative; width: 100%; margin-bottom: 20px; border-radius: 8px; overflow: hidden; }
.embed-map-wrap iframe { display: block; width: 100%; height: 420px; border: 0; }
.page-break-marker { height: 4px; background: repeating-linear-gradient(90deg, #ddd 0, #ddd 8px, transparent 8px, transparent 16px); }
.photo-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 30px; overflow: hidden; }
.photo-grid img { width: 100%; height: 180px; object-fit: cover; border-radius: 4px; }
.highlight-box { background: #f0f4f8; border: 1px solid #dce3eb; border-radius: 8px; padding: 20px 24px; margin: 24px 0; }
.footer { background: #1B3A5C; color: #fff; padding: 50px 40px; text-align: center; }
.footer-logo { width: 180px; margin-bottom: 30px; }
.footer-team { display: flex; justify-content: center; gap: 40px; margin-bottom: 30px; flex-wrap: wrap; }
.footer-person { text-align: center; flex: 1; min-width: 280px; }
.footer-headshot { width: 70px; height: 70px; border-radius: 50%; border: 2px solid #C5A258; object-fit: cover; }
.footer-name { font-size: 16px; font-weight: 600; }
.footer-title { font-size: 12px; color: #C5A258; margin-bottom: 8px; }
.footer-contact { font-size: 12px; color: rgba(255,255,255,0.7); line-height: 1.8; }
.footer-contact a { color: rgba(255,255,255,0.7); text-decoration: none; }
.footer-office { font-size: 12px; color: rgba(255,255,255,0.5); margin-bottom: 16px; }
.footer-disclaimer { font-size: 10px; color: rgba(255,255,255,0.35); margin-top: 20px; max-width: 800px; margin-left: auto; margin-right: auto; }
.financing-tables { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 20px; }
.rate-outlook { background: #f0f4f8; border-radius: 8px; padding: 20px 24px; margin-top: 20px; }
.rate-outlook h4 { color: #1B3A5C; font-size: 14px; margin-bottom: 10px; }
.rate-outlook li { font-size: 13px; line-height: 1.6; margin-bottom: 6px; }
@media (max-width: 768px) {
  .cover-content { padding: 30px 20px; }
  .cover-title { font-size: 32px; }
  .cover-logo { width: 220px; }
  .cover-headshots { gap: 24px; }
  .cover-headshot { width: 60px; height: 60px; }
  .section { padding: 30px 16px; }
  .two-col, .buyer-split, .inv-split, .os-two-col, .loc-grid, .financing-tables { grid-template-columns: 1fr; }
  .metrics-grid, .metrics-grid-4 { grid-template-columns: repeat(2, 1fr); gap: 12px; }
  .metric-card { padding: 14px 10px; }
  .metric-value { font-size: 22px; }
  .mkt-channels, .perf-grid { grid-template-columns: 1fr; }
  .summary-two-col, .prop-grid-4 { grid-template-columns: 1fr; }
  .pdf-float-btn { padding: 10px 18px; font-size: 12px; bottom: 16px; right: 16px; }
  .toc-nav { padding: 0 6px; }
  .toc-nav a { font-size: 10px; padding: 10px 6px; letter-spacing: 0.2px; }
  .leaflet-map { height: 300px; }
  .embed-map-wrap iframe { height: 320px; }
  .loc-wide-map { height: 180px; margin-top: 16px; }
  .table-scroll table { min-width: 560px; }
  .bio-grid { grid-template-columns: 1fr; gap: 16px; }
  .bio-headshot { width: 60px; height: 60px; }
  .footer-team { flex-direction: column; align-items: center; }
  .press-strip { gap: 16px; }
  .press-logo { font-size: 11px; }
  .costar-badge-title { font-size: 18px; }
  .inv-photo { height: 240px; }
  .team-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 420px) {
  .cover-title { font-size: 26px; }
  .cover-stat-value { font-size: 20px; }
  .metrics-grid-4 { grid-template-columns: 1fr 1fr; }
  .metric-value { font-size: 18px; }
  .section { padding: 20px 12px; }
}
@media print {
  @page { size: letter landscape; margin: 0.4in 0.5in; }
  body { font-size: 11px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  p { font-size: 11px; line-height: 1.5; margin-bottom: 8px; }
  .pdf-float-btn, .toc-nav, .leaflet-map, .embed-map-wrap, .page-break-marker, .map-fallback { display: none !important; }
  .cover { min-height: 7.5in; page-break-after: always; }
  .cover-bg { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .cover-headshots { display: flex !important; }
  .cover-headshot { width: 55px; height: 55px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .cover-logo { width: 240px; }
  .section { padding: 20px 0; page-break-before: always; }
  .section-title { font-size: 20px; margin-bottom: 4px; }
  .section-subtitle { font-size: 11px; margin-bottom: 10px; }
  .section-divider { margin-bottom: 16px; }
  .metric-card { padding: 12px 8px; border-radius: 6px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .metric-value { font-size: 20px; }
  .metric-label { font-size: 9px; }
  table { font-size: 11px; }
  th { padding: 6px 8px; font-size: 9px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  td { padding: 5px 8px; }
  tr.highlight { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  tr.summary { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .tr-tagline { font-size: 15px; padding: 8px 14px; margin-bottom: 8px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .tr-map-print { display: block; width: 100%; height: 240px; border-radius: 4px; overflow: hidden; margin-bottom: 8px; }
  .tr-map-print img { width: 100%; height: 100%; object-fit: cover; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .tr-service-quote { margin: 10px 0; }
  .tr-service-quote h3 { font-size: 13px; margin-bottom: 4px; }
  .tr-service-quote p { font-size: 11px; line-height: 1.45; }
  .tr-page2 { page-break-before: always; }
  .tr-page2 .section-title { font-size: 18px; margin-bottom: 2px; }
  .tr-page2 .section-divider { margin-bottom: 8px; }
  .bio-grid { gap: 12px; margin: 8px 0; }
  .bio-card { gap: 10px; }
  .bio-headshot { width: 75px; height: 75px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .bio-text { font-size: 11px; }
  .team-grid { gap: 6px; margin: 8px 0; grid-template-columns: repeat(4, 1fr); }
  .team-headshot { width: 45px; height: 45px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .team-card-name { font-size: 11px; }
  .team-card-title { font-size: 9px; }
  .costar-badge { padding: 8px 12px; margin: 8px auto; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .costar-badge-title { font-size: 16px; }
  .condition-note { padding: 8px 14px; margin-top: 8px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .achievements-list { font-size: 11px; line-height: 1.5; }
  .press-strip { padding: 6px 12px; gap: 16px; margin-top: 8px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .press-logo { font-size: 10px; }
  #marketing { page-break-before: always; }
  #marketing .section-title { font-size: 18px; margin-bottom: 2px; }
  #marketing .section-subtitle { font-size: 11px; margin-bottom: 4px; }
  #marketing .section-divider { margin-bottom: 6px; }
  #marketing .metrics-grid-4 { gap: 8px; margin-bottom: 8px; grid-template-columns: repeat(4, 1fr); }
  #marketing .metric-card { padding: 8px 6px; }
  #marketing .metric-value { font-size: 18px; }
  #marketing .metric-label { font-size: 8px; }
  .mkt-quote { padding: 8px 14px; margin: 8px 0; font-size: 11px; line-height: 1.4; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .mkt-channels { gap: 10px; margin-top: 8px; grid-template-columns: 1fr 1fr; }
  .mkt-channel { padding: 8px 12px; border-radius: 6px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .mkt-channel h4 { font-size: 11px; margin-bottom: 4px; }
  .mkt-channel li { font-size: 10px; line-height: 1.4; margin-bottom: 2px; }
  .perf-grid { gap: 10px; margin-top: 8px; grid-template-columns: 1fr 1fr; }
  .perf-card { padding: 8px 12px; border-radius: 6px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .perf-card h4 { font-size: 11px; margin-bottom: 4px; }
  .perf-card li { font-size: 10px; line-height: 1.4; margin-bottom: 2px; }
  .platform-strip { padding: 6px 12px; gap: 12px; margin-top: 8px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .platform-strip-label { font-size: 8px; }
  .inv-text p { font-size: 11px; line-height: 1.5; margin-bottom: 6px; }
  .inv-logo { display: none !important; }
  .inv-right { padding-top: 30px; }
  .inv-photo { height: 220px; }
  .inv-photo img { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .inv-highlights { padding: 10px 14px; }
  .inv-highlights h4 { font-size: 11px; margin-bottom: 4px; }
  .inv-highlights li { font-size: 10px; line-height: 1.4; margin-bottom: 2px; }
  .loc-grid { display: grid; grid-template-columns: 58% 42%; gap: 14px; page-break-inside: avoid; }
  .loc-left { max-height: 340px; overflow: hidden; }
  .loc-left p { font-size: 10.5px; line-height: 1.4; margin-bottom: 5px; }
  .loc-right { max-height: 340px; overflow: hidden; }
  .loc-right table { font-size: 10px; }
  .loc-right th { font-size: 9px; padding: 4px 6px; }
  .loc-right td { padding: 4px 6px; font-size: 10px; }
  .loc-wide-map { height: 220px; margin-top: 8px; }
  .loc-wide-map img { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  #prop-details { page-break-before: always; }
  .prop-grid-4 { gap: 12px; }
  .prop-grid-4 table { font-size: 10px; }
  .prop-grid-4 th { font-size: 9px; padding: 4px 6px; }
  .prop-grid-4 td { padding: 4px 6px; font-size: 10px; }
  .os-two-col { page-break-before: always; align-items: stretch; gap: 16px; }
  .os-left table { font-size: 10px; }
  .os-left th { font-size: 9px; padding: 4px 6px; }
  .os-left td { padding: 4px 6px; }
  .os-right { font-size: 9.5px; line-height: 1.3; padding: 10px 12px; }
  .os-right p { margin-bottom: 4px; font-size: 9.5px; }
  .os-right .sub-heading { font-size: 12px; margin-bottom: 6px; }
  .summary-page { page-break-before: always; padding: 12px; }
  .summary-banner { font-size: 12px; padding: 6px 12px; margin-bottom: 10px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .summary-two-col { gap: 12px; }
  .summary-table { font-size: 8px; margin-bottom: 8px; }
  .summary-table td { padding: 2px 4px; }
  .summary-table th { padding: 2px 4px; }
  .summary-header { font-size: 7px !important; padding: 3px 4px !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .obj-q { font-size: 11px; margin-bottom: 2px; }
  .obj-a { font-size: 10px; line-height: 1.4; }
  .obj-item { margin-bottom: 8px; }
  .bp-closing { font-size: 10px; }
  .buyer-photo { height: 180px; }
  .buyer-photo img { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  #sale-comps, #rent-comps, #financing { page-break-before: always; }
  .comp-narratives p.narrative { font-size: 10.5px; line-height: 1.4; margin-bottom: 6px; page-break-inside: avoid; }
  .comp-map-print { display: block !important; height: 280px; border-radius: 4px; overflow: hidden; margin-bottom: 10px; }
  .comp-map-print img { width: 100%; height: 100%; object-fit: cover; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .footer { page-break-before: always; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .footer-headshot { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .price-reveal { page-break-before: always; }
  #property-info { page-break-before: always; }
  .financing-tables { grid-template-columns: 1fr 1fr; }
  .rate-outlook { padding: 10px 14px; }
  .rate-outlook li { font-size: 10px; }
}
"""

    js = f"""
var params = new URLSearchParams(window.location.search);
var client = params.get('client');
if (client) {{
  var el = document.getElementById('client-greeting');
  if (el) el.textContent = 'Prepared Exclusively for ' + client;
}}
document.querySelectorAll('.toc-nav a').forEach(function(link) {{
  link.addEventListener('click', function(e) {{
    e.preventDefault();
    var target = document.querySelector(this.getAttribute('href'));
    if (target) {{
      var navH = document.getElementById('toc-nav').offsetHeight;
      window.scrollTo({{ top: target.getBoundingClientRect().top + window.pageYOffset - navH - 4, behavior: 'smooth' }});
    }}
  }});
}});
var tocLinks = document.querySelectorAll('.toc-nav a');
var tocSections = [];
tocLinks.forEach(function(link) {{
  var sec = document.getElementById(link.getAttribute('href').substring(1));
  if (sec) tocSections.push({{ link: link, section: sec }});
}});
function updateToc() {{
  var navH = document.getElementById('toc-nav').offsetHeight + 20;
  var pos = window.pageYOffset + navH;
  var cur = null;
  tocSections.forEach(function(item) {{ if (item.section.offsetTop <= pos) cur = item.link; }});
  tocLinks.forEach(function(l) {{ l.classList.remove('toc-active'); }});
  if (cur) cur.classList.add('toc-active');
}}
window.addEventListener('scroll', updateToc);
updateToc();

// Sale Comps Leaflet Map
var saleMap = L.map('saleMap');
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{attribution:'&copy; OpenStreetMap'}}).addTo(saleMap);
var allMarkerssaleMap = [];
var subSale = L.marker([{SUBJECT_LAT},{SUBJECT_LNG}],{{icon:L.divIcon({{className:'',html:'<div style="background:#C5A258;color:#fff;border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.3);">S</div>',iconSize:[32,32],iconAnchor:[16,16]}})}}
).addTo(saleMap).bindPopup('<b>Subject: 4503-4507 Castle Lane</b><br>3 Units | TBD');
allMarkerssaleMap.push(subSale);
var c1 = L.marker([{COMP1_LAT},{COMP1_LNG}],{{icon:L.divIcon({{className:'',html:'<div style="background:#1B3A5C;color:#fff;border-radius:50%;width:26px;height:26px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;border:2px solid #fff;box-shadow:0 2px 4px rgba(0,0,0,.3);">1</div>',iconSize:[26,26],iconAnchor:[13,13]}})}}
).addTo(saleMap).bindPopup('<b>#1: 2511 Hermosa Ave, Montrose</b><br>3 Units | $1,340,000 | Aug 2025');
allMarkerssaleMap.push(c1);
var c2 = L.marker([{COMP2_LAT},{COMP2_LNG}],{{icon:L.divIcon({{className:'',html:'<div style="background:#1B3A5C;color:#fff;border-radius:50%;width:26px;height:26px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;border:2px solid #fff;box-shadow:0 2px 4px rgba(0,0,0,.3);">2</div>',iconSize:[26,26],iconAnchor:[13,13]}})}}
).addTo(saleMap).bindPopup('<b>#2: 3357 Honolulu Ave, La Canada Flintridge</b><br>3 Units | $1,450,000 | Oct 2025');
allMarkerssaleMap.push(c2);
var c3 = L.marker([{COMP3_LAT},{COMP3_LNG}],{{icon:L.divIcon({{className:'',html:'<div style="background:#1B3A5C;color:#fff;border-radius:50%;width:26px;height:26px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;border:2px solid #fff;box-shadow:0 2px 4px rgba(0,0,0,.3);">3</div>',iconSize:[26,26],iconAnchor:[13,13]}})}})
).addTo(saleMap).bindPopup('<b>#3: 4543 Rockland Pl, La Canada Flintridge</b><br>2 Units | $1,700,000 | Oct 2025');
allMarkerssaleMap.push(c3);
saleMap.fitBounds(L.featureGroup(allMarkerssaleMap).getBounds().pad(0.15));

// Rent Comps Leaflet Map
var rentMap = L.map('rentMap');
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{attribution:'&copy; OpenStreetMap'}}).addTo(rentMap);
var allMarkersrentMap = [];
var subRent = L.marker([{SUBJECT_LAT},{SUBJECT_LNG}],{{icon:L.divIcon({{className:'',html:'<div style="background:#C5A258;color:#fff;border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.3);">S</div>',iconSize:[32,32],iconAnchor:[16,16]}})}}
).addTo(rentMap).bindPopup('<b>Subject: Castle Lane</b>');
allMarkersrentMap.push(subRent);
var r2 = L.marker([{RENT2_LAT},{RENT2_LNG}],{{icon:L.divIcon({{className:'',html:'<div style="background:#1B3A5C;color:#fff;border-radius:50%;width:26px;height:26px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;border:2px solid #fff;box-shadow:0 2px 4px rgba(0,0,0,.3);">2</div>',iconSize:[26,26],iconAnchor:[13,13]}})}}
).addTo(rentMap).bindPopup('<b>2535 Cross St, La Crescenta/LCF Area</b><br>1BR - $2,500/mo');
allMarkersrentMap.push(r2);
var r3 = L.marker([{RENT3_LAT},{RENT3_LNG}],{{icon:L.divIcon({{className:'',html:'<div style="background:#1B3A5C;color:#fff;border-radius:50%;width:26px;height:26px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;border:2px solid #fff;box-shadow:0 2px 4px rgba(0,0,0,.3);">3</div>',iconSize:[26,26],iconAnchor:[13,13]}})}}
).addTo(rentMap).bindPopup('<b>3055 Foothill Blvd, La Crescenta/LCF Area</b><br>1BR - $2,095/mo');
allMarkersrentMap.push(r3);
var r4 = L.marker([{RENT4_LAT},{RENT4_LNG}],{{icon:L.divIcon({{className:'',html:'<div style="background:#1B3A5C;color:#fff;border-radius:50%;width:26px;height:26px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;border:2px solid #fff;box-shadow:0 2px 4px rgba(0,0,0,.3);">4</div>',iconSize:[26,26],iconAnchor:[13,13]}})}}
).addTo(rentMap).bindPopup('<b>Montrose Area (Honolulu Ave)</b><br>2BR Remodeled - $2,795/mo');
allMarkersrentMap.push(r4);
rentMap.fitBounds(L.featureGroup(allMarkersrentMap).getBounds().pad(0.15));
"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Broker Opinion of Value - 4503 Castle Lane, La Canada Flintridge</title>
<meta property="og:title" content="Broker Opinion of Value - 4503 Castle Lane, La Canada Flintridge">
<meta property="og:description" content="3-Unit Multifamily Investment - La Canada Flintridge, CA 91011 | LAAA Team - Marcus &amp; Millichap">
<meta property="og:image" content="https://{CNAME}/preview.png">
<meta property="og:url" content="https://{CNAME}/">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Broker Opinion of Value - 4503 Castle Lane, La Canada Flintridge">
<meta name="twitter:description" content="3-Unit Multifamily Investment - La Canada Flintridge, CA 91011 | LAAA Team - Marcus &amp; Millichap">
<meta name="twitter:image" content="https://{CNAME}/preview.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>{css}</style>
</head>
<body>

<!-- PDF DOWNLOAD BUTTON -->
<a href="{PDF_URL}" class="pdf-float-btn" target="_blank">
  <svg viewBox="0 0 24 24"><path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20M12,19L8,15H10.5V12H13.5V15H16L12,19Z"/></svg>
  Download PDF
</a>

<!-- COVER -->
<div class="cover">
  <div class="cover-bg" style="background-image:url('{IMG["hero"]}');"></div>
  <div class="cover-content">
    <img src="{IMG['logo_white']}" class="cover-logo" alt="LAAA Team">
    <div class="cover-label">Confidential Broker Opinion of Value</div>
    <div class="cover-title">4503 Castle Lane</div>
    <div class="cover-address">La Canada Flintridge, CA 91011</div>
    <div class="gold-line" style="width:80px;margin:0 auto 24px;"></div>
    <div class="cover-stats">
      <div class="cover-stat"><span class="cover-stat-value">3</span><span class="cover-stat-label">Units</span></div>
      <div class="cover-stat"><span class="cover-stat-value">2,335</span><span class="cover-stat-label">Square Feet</span></div>
      <div class="cover-stat"><span class="cover-stat-value">1952</span><span class="cover-stat-label">Year Built</span></div>
      <div class="cover-stat"><span class="cover-stat-value">0.14</span><span class="cover-stat-label">Acres</span></div>
    </div>
    <div class="cover-headshots">
      <div class="cover-headshot-wrap">
        <img class="cover-headshot" src="{IMG['glen']}" alt="Glen Scher">
        <div class="cover-headshot-name">Glen Scher</div>
        <div class="cover-headshot-title">SMDI</div>
      </div>
      <div class="cover-headshot-wrap">
        <img class="cover-headshot" src="{IMG['filip']}" alt="Filip Niculete">
        <div class="cover-headshot-name">Filip Niculete</div>
        <div class="cover-headshot-title">SMDI</div>
      </div>
    </div>
    <p class="client-greeting" id="client-greeting">Prepared for Your Review</p>
    <p style="font-size:12px;color:rgba(255,255,255,0.5);margin-top:8px;">March 2026</p>
  </div>
</div>

<!-- TOC NAV -->
<nav class="toc-nav" id="toc-nav">
  <a href="#track-record">Track Record</a>
  <a href="#marketing">Marketing</a>
  <a href="#investment">Investment</a>
  <a href="#location">Location</a>
  <a href="#prop-details">Property</a>
  <a href="#property-info">Buyer Profile</a>
  <a href="#financing">Financing</a>
  <a href="#sale-comps">Sale Comps</a>
  <a href="#rent-comps">Rent Comps</a>
  <a href="#financials">Financials</a>
  <a href="#contact">Contact</a>
</nav>

<!-- ── TRACK RECORD P1 ── -->
<div class="section section-alt" id="track-record">
  <div class="section-title">Team Track Record</div>
  <div class="section-subtitle">LA Apartment Advisors at Marcus &amp; Millichap</div>
  <div class="section-divider"></div>

  <div class="tr-tagline">
    <span style="display:block;font-size:1.2em;font-weight:700;margin-bottom:4px;">LAAA Team of Marcus &amp; Millichap</span>
    Expertise, Execution, Excellence.
  </div>

  <div class="metrics-grid-4">
    {build_metric_card("501", "Closed Transactions")}
    {build_metric_card("$1.6B", "Total Sales Volume")}
    {build_metric_card("5,000+", "Units Sold")}
    {build_metric_card("34", "Median DOM")}
  </div>

  <div class="embed-map-wrap">
    <iframe src="https://www.google.com/maps/d/embed?mid=1ewCjzE3QX9p6m2MqK-md8b6fZitfIzU&ehbc=2E312F" loading="lazy" allowfullscreen></iframe>
  </div>
  <div class="tr-map-print"><img src="{IMG['closings_map']}" alt="LAAA Closings Map"></div>

  <div class="tr-service-quote">
    <h3>"We Didn't Invent Great Service... We Just Set the Standard."</h3>
    <p>The LAAA Team was built on one guiding principle: results matter more than relationships - but relationships make results possible. With over 501 closed transactions and $1.6 billion in sales volume, we have earned our position as one of Southern California's most active multifamily teams by delivering consistently for every client, on every deal.</p>
    <p>We approach every listing with rigorous preparation, transparent communication, and relentless execution. Our team invests the time to understand each property, its story, and its market position before we ever go to market. That discipline is what allows us to price accurately, generate genuine buyer competition, and close at or above asking price.</p>
    <p>Whether you are a first-time seller or a seasoned investor with a large portfolio, you deserve an advisor who will tell you the truth about your asset and fight for every dollar at the closing table. That is the LAAA standard, and it is why our clients return and send us everyone they know.</p>
  </div>
</div>

<!-- ── TRACK RECORD P2 - OUR TEAM ── -->
<div class="page-break-marker"></div>
<div class="tr-page2" id="our-team">
  <div style="text-align:center;margin-bottom:8px;">
    <div class="section-title" style="margin-bottom:4px;">Our Team</div>
    <div class="section-divider" style="margin:0 auto 12px;"></div>
  </div>

  <div class="costar-badge" style="margin-top:4px;margin-bottom:8px;">
    <div class="costar-badge-title">#1 Most Active Multifamily Sales Team in LA County</div>
    <div class="costar-badge-sub">CoStar &bull; 2019, 2020, 2021 &bull; #4 in California</div>
  </div>

  <div class="bio-grid">
    <div class="bio-card">
      <img class="bio-headshot" src="{IMG['glen']}" alt="Glen Scher">
      <div>
        <div class="bio-name">Glen Scher</div>
        <div class="bio-title">Senior Managing Director Investments</div>
        <div class="bio-text">Glen Scher is one of Los Angeles' top multifamily brokers, with over 450 transactions and $1.4B in closed sales across LA and the Ventura and Santa Barbara counties. Co-founder of the LAAA Team at Marcus &amp; Millichap, Glen began his career in 2014 and earned Rookie of the Year from the SFVBJ in 2016. He holds a degree in Economics from UC Santa Barbara.</div>
      </div>
    </div>
    <div class="bio-card">
      <img class="bio-headshot" src="{IMG['filip']}" alt="Filip Niculete">
      <div>
        <div class="bio-name">Filip Niculete</div>
        <div class="bio-title">Senior Managing Director Investments</div>
        <div class="bio-text">Filip Niculete is one of Southern California's top commercial real estate brokers and co-founder of the LAAA Team. Born in Romania and raised in the San Fernando Valley, Filip studied Finance at San Diego State University and began his Marcus &amp; Millichap career in 2011. He has built a reputation for execution, integrity, and relentless work ethic across $1.4B in transactions.</div>
      </div>
    </div>
  </div>

  <div class="team-grid">
    <div class="team-card"><img class="team-headshot" src="{IMG['aida']}" alt="Aida Memary Scher"><div class="team-card-name">Aida Memary Scher</div><div class="team-card-title">Senior Associate</div></div>
    <div class="team-card"><img class="team-headshot" src="{IMG['morgan']}" alt="Morgan Wetmore"><div class="team-card-name">Morgan Wetmore</div><div class="team-card-title">Associate</div></div>
    <div class="team-card"><img class="team-headshot" src="{IMG['logan']}" alt="Logan Ward"><div class="team-card-name">Logan Ward</div><div class="team-card-title">Associate</div></div>
    <div class="team-card"><img class="team-headshot" src="{IMG['luka']}" alt="Luka Leader"><div class="team-card-name">Luka Leader</div><div class="team-card-title">Associate</div></div>
    <div class="team-card"><img class="team-headshot" src="{IMG['blake']}" alt="Blake Lewitt"><div class="team-card-name">Blake Lewitt</div><div class="team-card-title">Associate Investments</div></div>
    <div class="team-card"><img class="team-headshot" src="{IMG['alex']}" alt="Alexandro Tapia"><div class="team-card-name">Alexandro Tapia</div><div class="team-card-title">Associate Investments</div></div>
    <div class="team-card"><img class="team-headshot" src="{IMG['mike']}" alt="Mike Palade"><div class="team-card-name">Mike Palade</div><div class="team-card-title">Agent Assistant</div></div>
    <div class="team-card"><img class="team-headshot" src="{IMG['tony']}" alt="Tony Dang"><div class="team-card-name">Tony H. Dang</div><div class="team-card-title">Business Operations</div></div>
  </div>

  <div class="condition-note" style="margin-top:20px;">
    <div class="condition-note-label">Key Achievements</div>
    <p class="achievements-list">
      &bull; <strong>Chairman's Club</strong> - A top-tier annual honor from Marcus &amp; Millichap (Glen 2021 &bull; Filip 2021, 2018)<br>
      &bull; <strong>National Achievement Award</strong> - Recognized annually since 2015 for top national production<br>
      &bull; <strong>Sales Recognition Award</strong> - Consecutive annual recognition: Filip since 2013, Glen since 2016<br>
      &bull; <strong>SIA Induction</strong> - Senior Investment Advisor designation (Glen 2020 &bull; Filip 2018)<br>
      &bull; <strong>#1 Most Active Multifamily Team in LA County</strong> - CoStar, 2019, 2020, 2021
    </p>
  </div>

  <div class="press-strip">
    <span class="press-strip-label">As Featured In</span>
    <span class="press-logo">BISNOW</span>
    <span class="press-logo">YAHOO FINANCE</span>
    <span class="press-logo">CONNECT CRE</span>
    <span class="press-logo">SFVBJ</span>
    <span class="press-logo">THE PINNACLE LIST</span>
  </div>
</div>

<!-- ── MARKETING & RESULTS ── -->
<div class="page-break-marker"></div>
<div class="section" id="marketing">
  <div class="section-title">Our Marketing Approach &amp; Results</div>
  <div class="section-subtitle">Data-Driven Marketing + Proven Performance</div>
  <div class="section-divider"></div>

  <div class="metrics-grid-4">
    {build_metric_card("30K+", "Emails Per Campaign")}
    {build_metric_card("10K+", "Views Per Listing")}
    {build_metric_card("3.7", "Avg Offers Received")}
    {build_metric_card("18", "Days to Escrow")}
  </div>

  <div class="mkt-quote">"We are PROACTIVE marketers, not reactive. Every listing receives a full-court press from day one - phone, email, digital, and our proprietary investor network."</div>

  <div class="mkt-channels">
    <div class="mkt-channel"><h4>Direct Phone Outreach</h4><ul>
      <li>10,000+ active buyers in proprietary database</li>
      <li>Personal calls to known active buyers at launch</li>
      <li>Follow-up cadence tracked through closing</li>
    </ul></div>
    <div class="mkt-channel"><h4>Email Campaigns</h4><ul>
      <li>30,000+ subscriber investor list</li>
      <li>Targeted by price range and submarket</li>
      <li>Performance-tracked with A/B testing</li>
    </ul></div>
    <div class="mkt-channel"><h4>Online Platforms</h4><ul>
      <li>Premium placement on LoopNet, CoStar, CREXI</li>
      <li>Zillow, Apartments.com, Realtor.com</li>
      <li>Full-color professional OM delivered digitally</li>
    </ul></div>
    <div class="mkt-channel"><h4>Additional Channels</h4><ul>
      <li>Marcus &amp; Millichap network of 1,700+ agents</li>
      <li>Local signage and targeted print</li>
      <li>Social media and digital retargeting</li>
    </ul></div>
  </div>

  <div class="metrics-grid-4" style="margin-top:16px;">
    {build_metric_card("97.6%", "Sale Price / List Price")}
    {build_metric_card("21%", "Closed Above Ask")}
    {build_metric_card("10 Days", "Avg Contingency Removal")}
    {build_metric_card("61%", "1031 Exchange Buyers")}
  </div>

  <div class="perf-grid">
    <div class="perf-card"><h4>Pricing Accuracy</h4><ul>
      <li>97.6% average SP/LP ratio across all transactions</li>
      <li>Comp-supported pricing minimizes days on market</li>
      <li>Strategic price positioning to attract multiple offers</li>
    </ul></div>
    <div class="perf-card"><h4>Marketing Speed</h4><ul>
      <li>Average 18 days from list to accepted offer</li>
      <li>Full offer package within 7 days of launch</li>
      <li>Dedicated transaction coordinator from day one</li>
    </ul></div>
    <div class="perf-card"><h4>Contract Strength</h4><ul>
      <li>21% of deals closed above the asking price</li>
      <li>10-day average contingency removal timeline</li>
      <li>Strict buyer qualification before offer acceptance</li>
    </ul></div>
    <div class="perf-card"><h4>Exchange Expertise</h4><ul>
      <li>61% of buyers in 1031 exchange</li>
      <li>Active QI referral network available</li>
      <li>Timeline management for exchange deadlines</li>
    </ul></div>
  </div>

  <div class="platform-strip">
    <span class="platform-strip-label">Advertised On</span>
    <span class="platform-name">CREXI</span>
    <span class="platform-name">LoopNet</span>
    <span class="platform-name">CoStar</span>
    <span class="platform-name">Zillow</span>
    <span class="platform-name">Apartments.com</span>
    <span class="platform-name">Marcus &amp; Millichap</span>
    <span class="platform-name">MLS</span>
    <span class="platform-name">Realtor.com</span>
    <span class="platform-name">Trulia</span>
  </div>
</div>

<!-- ── INVESTMENT OVERVIEW ── -->
<div class="page-break-marker"></div>
<div class="section section-alt" id="investment">
  <div class="section-title">Investment Overview</div>
  <div class="section-subtitle">La Canada Flintridge - 4503 Castle Lane</div>
  <div class="section-divider"></div>

  <div class="inv-split">
    <div class="inv-left">
      <div class="metrics-grid-4">
        {build_metric_card("3", "Units")}
        {build_metric_card("2,335", "Rentable SF")}
        {build_metric_card("6,098", "Lot SF")}
        {build_metric_card("1952", "Year Built")}
      </div>
      <div class="inv-text">
        <p>The LAAA Team is proud to present 4503 Castle Lane, a well-maintained triplex in La Canada Flintridge -- one of the most coveted residential communities in Los Angeles County. The property comprises three units across 2,335 rentable square feet on a 6,098 SF lot, located in the City of La Canada Flintridge, home to NASA's Jet Propulsion Laboratory (JPL) and served by the nationally ranked La Canada Unified School District.</p>
        <p>The unit mix includes one 1-bedroom/1-bath (635 SF, downstairs facing Foothill) and two 2-bedroom/1-bath units (850 SF each, one downstairs and one upstairs). All three units are occupied with stable, long-term tenants. The 2BR units represent significant below-market rents - at $500-600/month under the Rentometer median of $2,548 - creating compelling rent upside as natural turnover occurs. The 1BR is at or near market.</p>
        <p>The seller acquired the property in January 2010 for $728,000 and has self-managed since acquisition. A new hot water heater was installed in 2025. The property is subject to CA AB 1482 statewide tenant protections (annual CPI + 5% max increase). La Canada Flintridge has no local rent stabilization ordinance. The 6,098 SF lot may support an ADU under current La Canada Flintridge and state ADU law.</p>
      </div>
    </div>
    <div class="inv-right">
      <div class="inv-photo"><img src="{IMG['hero']}" alt="4503 Castle Lane"></div>
      <div class="inv-highlights">
        <h4>Investment Highlights</h4>
        <ul>
          <li><strong>Proven submarket demand</strong> - Both comparable sales closed in Aug-Oct 2025 at 103%+ of asking price, in under 11 days, confirming active buyer demand.</li>
          <li><strong>Significant rent upside</strong> - 2BR units are $500-600/month below market. Two tenants since 2002 and 2010 have not had market resets in decades.</li>
          <li><strong>Owner-user opportunity</strong> - FHA 2-4 unit financing allows 3.5% down. Occupy one unit; the other two offset a substantial portion of the mortgage.</li>
          <li><strong>ADU potential</strong> - 6,098 SF lot in the City of La Canada Flintridge. State ADU law and local ordinance may permit additional unit(s), increasing long-term NOI.</li>
          <li><strong>Top-rated school district</strong> - Served by La Canada Unified School District, consistently ranked top 5 in California. 98% of graduates enroll in post-secondary schools -- a primary driver of sustained ownership demand.</li>
          <li><strong>Lean expense structure</strong> - Owner-supplied 2025 actuals yield $26,178 total expenses (37.0% of EGI), one of the lowest expense ratios available on a small multifamily asset in this submarket.</li>
        </ul>
      </div>
    </div>
  </div>
</div>

<!-- ── LOCATION OVERVIEW ── -->
<div class="page-break-marker"></div>
<div class="section section-alt" id="location">
  <div class="section-title">Location Overview</div>
  <div class="section-subtitle">La Canada Flintridge - 91011</div>
  <div class="section-divider"></div>

  <div class="loc-grid">
    <div class="loc-left">
      <p>La Canada Flintridge is an incorporated city in the Crescenta Valley foothills of the San Gabriel Mountains, known nationally for being home to NASA's Jet Propulsion Laboratory (JPL) and the California Institute of Technology's research partner institutions. The city attracts a high-income, highly educated professional demographic -- aerospace engineers, scientists, and academics -- who sustain some of the lowest rental vacancy rates in LA County. The community's low-density character and active neighborhood associations make new multifamily development exceptionally rare.</p>
      <p>The property sits near Foothill Boulevard, the area's primary commercial corridor. Residents enjoy walkable access to dining, retail, and services along Honolulu Avenue in adjacent Montrose -- a charming village district popular for farmers markets and local businesses. The 210 Freeway provides direct access to Burbank, Pasadena, and the 5/101 interchange. Downtown Los Angeles is approximately 14 miles south, and JPL is within 3 miles.</p>
      <p>La Canada Unified School District (LCUSD) serves this neighborhood and is consistently ranked among the top 5 school districts in California -- with 98% of graduates enrolling in post-secondary institutions. School quality is the single most cited factor for family residential demand in LCF, creating a permanent, self-reinforcing driver of property values and rent stability. The submarket has no flood zone exposure and no new multifamily pipeline.</p>
    </div>
    <div class="loc-right">
      <table class="info-table">
        <thead><tr><th colspan="2">Location Details</th></tr></thead>
        <tbody>
          <tr><td>Zip Code</td><td>91011</td></tr>
          <tr><td>County</td><td>Los Angeles</td></tr>
          <tr><td>Jurisdiction</td><td>City of La Canada Flintridge (no local RSO)</td></tr>
          <tr><td>Cross Streets</td><td>Foothill Blvd / Rosemont Ave</td></tr>
          <tr><td>Elementary School</td><td>Palm Crest Elementary (LCUSD)</td></tr>
          <tr><td>Middle School</td><td>La Canada High (7-12, LCUSD)</td></tr>
          <tr><td>High School</td><td>La Canada High School (LCUSD, top 5 in CA)</td></tr>
          <tr><td>Nearest Freeway</td><td>210 Freeway (0.5 mi)</td></tr>
          <tr><td>Miles to Burbank Studios</td><td>~8 miles</td></tr>
          <tr><td>Miles to DTLA</td><td>~14 miles</td></tr>
        </tbody>
      </table>
    </div>
  </div>
  <div class="loc-wide-map"><img src="{loc_map}" alt="Location Map - 4503 Castle Lane, La Canada Flintridge"></div>
</div>

<!-- ── PROPERTY DETAILS ── -->
<div class="page-break-marker"></div>
<div class="section" id="prop-details">
  <div class="section-title">Property Details</div>
  <div class="section-subtitle">4503 / 4505 / 4507 Castle Lane</div>
  <div class="section-divider"></div>

  <div class="prop-grid-4">
    <div>
      <table class="info-table">
        <thead><tr><th colspan="2">Property Overview</th></tr></thead>
        <tbody>
          <tr><td>Address</td><td>4503-4507 Castle Lane, La Canada Flintridge, CA 91011</td></tr>
          <tr><td>Property Type</td><td>Triplex - 3 Units</td></tr>
          <tr><td>Year Built</td><td>1952</td></tr>
          <tr><td>Rentable SF</td><td>2,335 SF</td></tr>
          <tr><td>Avg Unit SF</td><td>778 SF</td></tr>
          <tr><td>Stories</td><td>2 (4507 is upstairs)</td></tr>
          <tr><td>Ownership</td><td>Fee Simple</td></tr>
          <tr><td>Current Owner Since</td><td>January 5, 2010</td></tr>
        </tbody>
      </table>
    </div>
    <div>
      <table class="info-table">
        <thead><tr><th colspan="2">Site &amp; Zoning</th></tr></thead>
        <tbody>
          <tr><td>Lot Size</td><td>6,098 SF (~0.14 acres)</td></tr>
          <tr><td>Zoning</td><td>R-3 (City of La Canada Flintridge Multifamily Residential)</td></tr>
          <tr><td>Land Type</td><td>Fee Simple</td></tr>
          <tr><td>Parking</td><td>Street / On-site</td></tr>
          <tr><td>ADU Potential</td><td>Yes - Glendale ADU ordinance applicable</td></tr>
          <tr><td>Sewer</td><td>Public Sewer</td></tr>
          <tr><td>Water</td><td>Public</td></tr>
        </tbody>
      </table>
    </div>
    <div>
      <table class="info-table">
        <thead><tr><th colspan="2">Building Systems &amp; Capital</th></tr></thead>
        <tbody>
          <tr><td>Construction</td><td>Wood frame / Stucco</td></tr>
          <tr><td>Unit 4503</td><td>1BR/1BA - 635 SF, downstairs, faces Foothill</td></tr>
          <tr><td>Unit 4505</td><td>2BR/1BA - 850 SF, downstairs</td></tr>
          <tr><td>Unit 4507</td><td>2BR/1BA - 850 SF, upstairs</td></tr>
          <tr><td>Water Heater</td><td>New 2025</td></tr>
          <tr><td>Cooling</td><td>Wall/window units</td></tr>
        </tbody>
      </table>
    </div>
    <div>
      <table class="info-table">
        <thead><tr><th colspan="2">Regulatory &amp; Compliance</th></tr></thead>
        <tbody>
          <tr><td>Rent Control</td><td>No local RSO</td></tr>
          <tr><td>CA AB 1482</td><td>Applies - annual CPI + 5% max increase</td></tr>
          <tr><td>Local RSO</td><td>None - City of La Canada Flintridge has no rent stabilization ordinance</td></tr>
          <tr><td>Seller Self-Managed</td><td>Yes - no management company</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<!-- ── BUYER PROFILE & OBJECTIONS ── -->
<div class="page-break-marker"></div>
<div class="section section-alt" id="property-info">
  <div class="section-title">Buyer Profile &amp; Anticipated Objections</div>
  <div class="section-subtitle">Target Investors &amp; Data-Backed Responses</div>
  <div class="section-divider"></div>

  <div class="buyer-split">
    <div class="buyer-split-left">
      <h3 class="sub-heading">Target Buyer Profile</h3>
      <div class="obj-item">
        <p class="obj-q">Owner-Users (Primary Target)</p>
        <p class="obj-a">FHA 2-4 unit financing allows 3.5% down with the buyer occupying one unit. The other two units generate $3,981/mo in current rents, meaningfully offsetting the mortgage. An owner-user in La Canada Flintridge also captures the city's JPL-driven demand and top-rated LCUSD schools -- lifestyle value that pure investors cannot price.</p>
      </div>
      <div class="obj-item">
        <p class="obj-q">All-Cash Investors</p>
        <p class="obj-a">Buyers seeking inflation protection and long-term appreciation in an undersupplied La Canada Flintridge submarket. Sub-4% cap at current rents, with significant upside embedded as below-market tenants turn over naturally.</p>
      </div>
      <div class="obj-item">
        <p class="obj-q">1031 Exchange Buyers</p>
        <p class="obj-a">Blue-chip La Canada Flintridge location, strong equity story, and rent upside align with exchange buyers targeting safe, appreciating LA infill over near-term cash-on-cash returns. Three comparable sales in this immediate submarket support pricing.</p>
      </div>
      <p class="bp-closing">All three comparable sales in this immediate submarket closed at or above asking price in under 11 days, confirming genuine buyer competition for well-priced La Canada Flintridge multifamily.</p>
    </div>
    <div class="buyer-split-right">
      <h3 class="sub-heading">Anticipated Buyer Objections</h3>
      <div class="obj-item">
        <p class="obj-q">"The cap rate is below 4% - why would I pay this?"</p>
        <p class="obj-a">La Canada Flintridge triplexes trade at sub-4% current caps because buyers price in rent upside and long-term appreciation in this supply-constrained, school-driven market. All three comps in this submarket sold at comparable cap rates. The pro forma cap at market rents is 4.62% at list price -- among the strongest pro forma yields in this submarket.</p>
      </div>
      <div class="obj-item">
        <p class="obj-q">"This doesn't cash-flow with conventional financing."</p>
        <p class="obj-a">Correct at investment loan rates -- and our primary buyer pool accounts for this. Owner-users at FHA rates and 3.5% down achieve very different cash flow dynamics. All-cash buyers earn $60,114 NOI at market rents (4.62% pro forma cap). This is an equity play in a top-tier school district with a credible income story at natural turnover.</p>
      </div>
      <div class="obj-item">
        <p class="obj-q">"The 2BR rents are far below market - that's a risk."</p>
        <p class="obj-a">Below-market rents are the opportunity, not the risk. At natural turnover, rents reset to the $2,548 Rentometer median - a 30% increase per unit. Tenants since 2002 and 2010 have not had market resets in decades. There is no capital requirement to capture this upside.</p>
      </div>
      <div class="obj-item">
        <p class="obj-q">"The lot is smaller than the comps."</p>
        <p class="obj-a">Reflected in our pricing: at $433K/unit, the subject is priced well below the three-comp average of $593K/unit -- a 27% discount that fully accounts for the lot differential. The 6,098 SF lot may support an ADU under state law, creating value-add optionality not available at many comp properties.</p>
      </div>
    </div>
  </div>
  <div class="buyer-photo"><img src="{IMG['hero']}" alt="4503 Castle Lane"></div>
</div>

<!-- ── FINANCING OVERVIEW (CUSTOM) ── -->
<div class="page-break-marker"></div>
<div class="section" id="financing">
  <div class="section-title">Financing in Today's Market</div>
  <div class="section-subtitle">2 to 4 Unit Investment Properties - March 2026</div>
  <div class="section-divider"></div>

  <p>As of March 2026, the 30-year fixed rate averaged 6.00% (Freddie Mac, week of March 5, 2026) - its lowest level since September 2022 after dipping to 5.98% in late February. Investment property loans on 2-4 unit properties carry a 0.50%-0.75% premium over owner-occupied rates, making borrowing conditions materially better than the 2023-2024 peak near 7.50%.</p>

  <div class="financing-tables">
    <div>
      <h3 class="sub-heading" style="margin-top:0;">Loan Products Available</h3>
      <table>
        <thead><tr><th>Loan Type</th><th>Rate Range</th><th>Max LTV</th><th>Key Notes</th></tr></thead>
        <tbody>
          <tr><td><strong>Conventional - Owner-Occupied</strong></td><td>6.00%-6.50%</td><td>85-90%</td><td>Fannie/Freddie. Borrower must occupy one unit.</td></tr>
          <tr><td><strong>FHA - Owner-Occupied</strong></td><td>5.50%-6.25%</td><td>96.5%</td><td>3.5% down. MIP required. Projects rental income for qualification.</td></tr>
          <tr><td><strong>Conventional - Investment</strong></td><td>6.50%-7.25%</td><td>75-80%</td><td>25% down minimum. Personal income + global cash flow.</td></tr>
          <tr><td><strong>DSCR Loan</strong></td><td>6.75%-7.75%</td><td>70-75%</td><td>Qualifies on property cash flow only. No income verification.</td></tr>
          <tr><td><strong>Portfolio / Bank Loan</strong></td><td>5.50%-7.50%</td><td>70-75%</td><td>Flexible underwriting. May offer interest-only periods.</td></tr>
          <tr><td><strong>Private / Hard Money</strong></td><td>8.50%-12.00%</td><td>60-70%</td><td>Short-term only. Not suitable for hold strategy.</td></tr>
        </tbody>
      </table>
    </div>
    <div>
          <h3 class="sub-heading" style="margin-top:0;">Financing Reality Check at $1,250,000</h3>
          <table>
            <thead><tr><th>Scenario</th><th>Down</th><th>Rate</th><th>Annual DS</th><th>PF NOI</th><th>Cash Flow</th></tr></thead>
            <tbody>
              <tr><td>25% Down - Inv. Conv.</td><td>$313K</td><td>6.75%</td><td>$72,981</td><td>$54,330</td><td style="color:#c0392b;">($18,651)</td></tr>
              <tr><td>35% Down - Inv. Conv.</td><td>$438K</td><td>6.75%</td><td>$63,250</td><td>$54,330</td><td style="color:#c0392b;">($8,920)</td></tr>
              <tr class="highlight"><td><strong>50% Down - Modeled</strong></td><td>$625K</td><td>6.25%</td><td>$46,181</td><td>$54,330</td><td style="color:#27ae60;"><strong>$8,149</strong></td></tr>
              <tr class="highlight"><td><strong>All Cash</strong></td><td>$1,250K</td><td>-</td><td>-</td><td>$54,330</td><td style="color:#27ae60;"><strong>$54,330 (4.35%)</strong></td></tr>
            </tbody>
          </table>
    </div>
  </div>

  <div class="condition-note">
    <div class="condition-note-label">Key Takeaway</div>
    This is a sub-4% cap rate asset in a strong residential submarket. Conventional investment financing is challenging at today's rates - the property cash-flows only with 50%+ equity. The buyer pool for this asset is: (1) all-cash investors, (2) owner-users using FHA or conventional owner-occupied financing at lower rates and higher LTV, or (3) 1031 exchange buyers seeking safe, appreciating LA infill over near-term cash-on-cash returns.
  </div>

  <div class="rate-outlook">
    <h4>Rate Trend &amp; Outlook</h4>
    <ul>
      <li>30-year fixed hit 5.98% in late February 2026 - the first time below 6.00% since September 2022. Minor improvement from 2024 highs near 7.50%.</li>
      <li>The Fed has signaled 1-2 more cuts in 2026. If realized, conventional investment rates could fall to the mid-6% range by year-end.</li>
      <li>Buyers sensitive to rates should note: today's environment is materially better than 2023-2024. Sub-6% fixed rates may return in 2026.</li>
      <li>For 2-4 unit owner-users: FHA at 3.5% down remains one of the most compelling entry points - especially with projected rental income counted toward qualification.</li>
    </ul>
  </div>
</div>

<!-- ── SALE COMPS ── -->
<div class="page-break-marker"></div>
<div class="section section-alt" id="sale-comps">
  <div class="section-title">Sale Comparables</div>
  <div class="section-subtitle">Recent Closed Sales - La Canada Flintridge / Montrose Submarket</div>
  <div class="section-divider"></div>

  <div class="leaflet-map" id="saleMap"></div>
  <div class="comp-map-print"><img src="{sale_map}" alt="Sale Comps Map"></div>

  <div class="table-scroll">
    <table>
      <thead><tr><th>#</th><th>Address</th><th class="num">Units</th><th class="num">Bldg SF</th><th class="num">Lot SF</th><th class="num">Yr Built</th><th class="num">Sold Price</th><th class="num">$/Unit</th><th class="num">$/SF</th><th class="num">DOM</th><th class="num">Sale Date</th><th class="num">SP/LP</th></tr></thead>
      <tbody>
        <tr><td>1</td><td>2511 Hermosa Ave, Montrose</td><td class="num">3</td><td class="num">2,677</td><td class="num">7,323</td><td class="num">1923</td><td class="num">$1,340,000</td><td class="num">$446,667</td><td class="num">$501</td><td class="num">11</td><td class="num">Aug 2025</td><td class="num">103.1%</td></tr>
        <tr><td>2</td><td>3357 Honolulu Ave, La Canada Flintridge</td><td class="num">3</td><td class="num">2,815</td><td class="num">7,211</td><td class="num">1947</td><td class="num">$1,450,000</td><td class="num">$483,333</td><td class="num">$515</td><td class="num">2</td><td class="num">Oct 2025</td><td class="num">103.6%</td></tr>
        <tr><td>3</td><td>4543 Rockland Pl, La Canada Flintridge</td><td class="num">2</td><td class="num">2,047</td><td class="num">6,445</td><td class="num">1953</td><td class="num">$1,700,000</td><td class="num">$850,000</td><td class="num">$830</td><td class="num">4</td><td class="num">Oct 2025</td><td class="num">100.3%</td></tr>
        <tr class="summary"><td>Avg</td><td></td><td class="num">2.7</td><td class="num">2,513</td><td class="num">6,993</td><td class="num">1941</td><td class="num">$1,496,667</td><td class="num">$593,333</td><td class="num">$615</td><td class="num">6</td><td class="num"></td><td class="num">102.3%</td></tr>
        <tr class="highlight"><td>Subject</td><td>4503 Castle Lane, La Canada Flintridge</td><td class="num">3</td><td class="num">2,335</td><td class="num">6,098</td><td class="num">1952</td><td class="num">$1,300,000</td><td class="num">$433,333</td><td class="num">$557</td><td class="num">-</td><td class="num">-</td><td class="num">-</td></tr>
      </tbody>
    </table>
  </div>

  <div class="comp-narratives">
    <p class="narrative"><strong>1. 2511 Hermosa Ave, Montrose - $1,340,000 (Aug 2025)</strong> - This Montrose triplex sold in August 2025 at 103.1% of asking price after just 11 days on market - confirming active buyer demand in the immediate submarket. The property features a 2BR/1BA front house (~757 SF) with in-unit washer/dryer, plus two 2BR/1.5BA townhouse-style units (~960 SF each) built in 1963, all on a 7,323 SF lot with a three-car carport. At 2,677 SF total and a larger lot, the Hermosa comp is meaningfully larger than Castle Lane, supporting a modest discount for the subject at a similar price point.</p>
    <p class="narrative"><strong>2. 3357 Honolulu Ave, La Canada Flintridge - $1,450,000 (Oct 2025)</strong> - This La Canada Flintridge triplex sold in October 2025 at 103.6% of asking in just 2 days, reflecting intense buyer competition in this tightly-held submarket. The property includes a standalone 3BR/2BA house (~1,300 SF) plus two 1BR/1BA units (~800 SF each, built 1980) on a 7,211 SF lot with a 5-car garage. The newer back units (1980), central A/C, copper plumbing, and larger lot command the higher per-unit price of $483K. The subject's smaller footprint supports pricing at a measured discount to this comp.</p>
    <p class="narrative"><strong>3. 4543 Rockland Pl, La Canada Flintridge - $1,700,000 (Oct 2025)</strong> - Located approximately 100 feet from the subject, this same-vintage (1953) La Canada Flintridge property sold in October 2025 at 100.3% of asking price in just 4 days on market. The property features a newly remodeled 3BR/2BA main residence (1,345 SF) and a detached 1BR/1BA guest house (702 SF) on a 6,445 SF lot -- a near-identical lot to the subject. At $1,700,000, this immediately adjacent comp provides the most direct pricing benchmark available. The subject triplex at $1,300,000 is priced at a 23.5% discount, appropriate given the subject's three-unit income profile versus the owner-occupied primary home structure of the Rockland comp.</p>
  </div>

  <div class="condition-note">
    <div class="condition-note-label">Comp Summary</div>
    The three comparable sales averaged $593,333/unit and $615/SF. The subject at $1,300,000 ($433K/unit, $557/SF) is priced at a 27% discount to the comp average on a per-unit basis -- well-supported given the triplex income structure versus the owner-occupied comp formats. Most notably, the immediately adjacent 4543 Rockland Pl sold for $1,700,000 in October 2025, providing the strongest single pricing anchor available. All three comps sold at or above asking price within 11 days, confirming deep buyer demand in this submarket.
  </div>
</div>

<!-- ── RENT COMPS ── -->
<div class="page-break-marker"></div>
<div class="section" id="rent-comps">
  <div class="section-title">Rent Comparables</div>
  <div class="section-subtitle">Rentometer Analysis &amp; Active Market Listings - La Canada Flintridge / Crescenta Valley 91011</div>
  <div class="section-divider"></div>

  <div class="leaflet-map" id="rentMap"></div>
  <div class="comp-map-print"><img src="{rent_map}" alt="Rent Comps Map"></div>

  <h3 class="sub-heading">Rentometer Analysis (2-3 Mile Radius)</h3>
  <div class="table-scroll">
    <table>
      <thead><tr><th>Bed Type</th><th class="num">Median</th><th class="num">Mean</th><th class="num">25th Pct</th><th class="num">75th Pct</th><th class="num">Samples</th></tr></thead>
      <tbody>
        <tr><td>1 Bedroom</td><td class="num">$1,900</td><td class="num">$1,915</td><td class="num">$1,586</td><td class="num">$2,244</td><td class="num">7</td></tr>
        <tr><td>2 Bedroom</td><td class="num">$2,548</td><td class="num">$2,676</td><td class="num">$2,429</td><td class="num">$2,923</td><td class="num">18</td></tr>
      </tbody>
    </table>
  </div>

  <h3 class="sub-heading">Active Market Listings</h3>
  <div class="table-scroll">
    <table>
      <thead><tr><th>#</th><th>Address</th><th>Type</th><th class="num">Rent/Mo</th><th>Notes</th></tr></thead>
      <tbody>
        <tr><td>1</td><td>3250 Fairesta St, La Crescenta</td><td>1BR</td><td class="num">$2,320+</td><td>Available now</td></tr>
        <tr><td>2</td><td>2535 Cross St, La Crescenta</td><td>1BR</td><td class="num">$2,500</td><td>Cross Apartments</td></tr>
        <tr><td>3</td><td>3055 Foothill Blvd #9, La Crescenta</td><td>1BR</td><td class="num">$2,095</td><td>730 SF comparable</td></tr>
        <tr><td>4</td><td>Montrose Area (Honolulu Ave)</td><td>2BR</td><td class="num">$2,795</td><td>Fully remodeled, in-unit W/D</td></tr>
      </tbody>
    </table>
  </div>

  <h3 class="sub-heading">Rent Upside Summary</h3>
  <div class="table-scroll">
    <table>
      <thead><tr><th>Unit</th><th class="num">Current Rent</th><th class="num">Market Median</th><th class="num">Monthly Upside</th><th class="num">Annual Upside</th></tr></thead>
      <tbody>
        <tr><td>4503 (1BR)</td><td class="num">$1,920</td><td class="num">$2,095-$2,320</td><td class="num">$175-$400</td><td class="num">$2,100-$4,800</td></tr>
        <tr><td>4505 (2BR)</td><td class="num">$1,958</td><td class="num">$2,548</td><td class="num">$590</td><td class="num">$7,080</td></tr>
        <tr><td>4507 (2BR)</td><td class="num">$2,023</td><td class="num">$2,548</td><td class="num">$525</td><td class="num">$6,300</td></tr>
        <tr class="summary"><td><strong>Total</strong></td><td class="num"><strong>$5,901/mo</strong></td><td class="num"><strong>$7,191-$7,416/mo</strong></td><td class="num"><strong>$1,290-$1,515/mo</strong></td><td class="num"><strong>$15,480-$18,180/yr</strong></td></tr>
      </tbody>
    </table>
  </div>

  <p class="narrative">Active rental listings in the La Canada Flintridge / Crescenta Valley area confirm substantial rent upside for the Castle Lane portfolio. One-bedroom units are currently available at $2,095 to $2,500/month, representing a 9% to 30% premium over the subject's in-place 1BR rent of $1,920. Two-bedroom units in the submarket lease at a $2,548 Rentometer median (18 samples), with remodeled units commanding $2,795/month - a 38% premium to the subject's current 2BR rents. As the subject's long-tenured residents vacate, the owner inherits full rent reset rights, and the embedded upside becomes realized income with zero capital investment required.</p>
</div>

<!-- ── FINANCIAL ANALYSIS ── -->
<div class="page-break-marker"></div>
<div class="section section-alt" id="financials">
  <div class="section-title">Financial Analysis</div>
  <div class="section-subtitle">Investment Underwriting</div>
  <div class="section-divider"></div>

  <h3 class="sub-heading">Unit Mix &amp; Rent Roll</h3>
  <div class="table-scroll">
    <table>
      <thead><tr>
        <th>Unit</th><th>Type</th><th class="num">SF</th>
        <th class="num">Current Rent</th><th class="num">Rent/SF</th>
        <th class="num">Market Rent</th><th class="num">Market/SF</th>
        <th>Tenant Since</th><th>Next Raise</th>
      </tr></thead>
      <tbody>
        <tr>
          <td>4503</td><td>1BR / 1BA</td><td class="num">635</td>
          <td class="num">$1,920</td><td class="num">$3.02</td>
          <td class="num">$2,095</td><td class="num">$3.30</td>
          <td>Sep 2022</td><td>1/31/2026</td>
        </tr>
        <tr>
          <td>4505</td><td>2BR / 1BA</td><td class="num">850</td>
          <td class="num">$1,958</td><td class="num">$2.30</td>
          <td class="num">$2,548</td><td class="num">$3.00</td>
          <td>Feb 2010</td><td>7/1/2026</td>
        </tr>
        <tr>
          <td>4507</td><td>2BR / 1BA</td><td class="num">850</td>
          <td class="num">$2,023</td><td class="num">$2.38</td>
          <td class="num">$2,548</td><td class="num">$3.00</td>
          <td>Feb 2002</td><td>7/1/2026</td>
        </tr>
        <tr class="summary">
          <td><strong>Total</strong></td><td></td><td class="num"><strong>2,335</strong></td>
          <td class="num"><strong>$5,901/mo</strong></td><td class="num"><strong>$2.53</strong></td>
          <td class="num"><strong>$7,191/mo</strong></td><td class="num"><strong>$3.08</strong></td>
          <td></td><td></td>
        </tr>
      </tbody>
    </table>
  </div>

  <p style="font-size:12px;color:#777;margin-top:-16px;margin-bottom:24px;">Market rents per Rentometer (March 2026): 1BR median $1,900 (7 samples, 3 mi); 2BR median $2,548 (18 samples, 2 mi). Active listing range: 1BR $2,095-$2,500; 2BR $2,548-$2,795. Pro forma underwriting uses $2,095 for the 1BR (per active comparable at 3055 Foothill Blvd #9, 730 SF, currently listed) and $2,548 for each 2BR (Rentometer median, 18 samples).</p>
</div>

<!-- FINANCIAL SCREEN 2: OPERATING STATEMENT -->
<div class="section section-alt">
  <div class="os-two-col">
    <div class="os-left">
      <h3 class="sub-heading" style="margin-top:0;">Operating Statement</h3>
      <table>
        <thead><tr><th>Income</th><th class="num">Annual</th><th class="num">Per Unit</th><th class="num">$/SF</th><th class="num">% EGI</th></tr></thead>
        <tbody>
          <tr><td>Gross Scheduled Rent</td><td class="num">{fmt(GSR)}</td><td class="num">{fmt(GSR/UNITS)}</td><td class="num">${GSR/SF:.2f}</td><td class="num"> - </td></tr>
          <tr class="summary"><td><strong>Effective Gross Income</strong></td><td class="num"><strong>{fmt(CURRENT_EGI)}</strong></td><td class="num"><strong>{fmt(CURRENT_EGI//UNITS)}</strong></td><td class="num"><strong>${CURRENT_EGI/SF:.2f}</strong></td><td class="num"><strong>100.0%</strong></td></tr>
        </tbody>
      </table>
      <table>
        <thead><tr><th>Expenses</th><th class="num">Annual</th><th class="num">Per Unit</th><th class="num">$/SF</th><th class="num">% EGI</th></tr></thead>
        <tbody>
          {os_expense_html}
          <tr class="summary"><td><strong>Total Expenses</strong></td><td class="num"><strong>{fmt(CUR_TOTAL_EXP)}</strong></td><td class="num"><strong>{fmt(CUR_TOTAL_EXP//UNITS)}</strong></td><td class="num"><strong>${CUR_TOTAL_EXP/SF:.2f}</strong></td><td class="num"><strong>{CUR_TOTAL_EXP/CURRENT_EGI*100:.1f}%</strong></td></tr>
          <tr class="summary"><td><strong>Net Operating Income</strong></td><td class="num"><strong>{fmt(CUR_NOI)}</strong></td><td class="num"><strong>{fmt(CUR_NOI//UNITS)}</strong></td><td class="num"><strong>${CUR_NOI/SF:.2f}</strong></td><td class="num"><strong>{CUR_NOI/CURRENT_EGI*100:.1f}%</strong></td></tr>
        </tbody>
      </table>
    </div>
    <div class="os-right">
      <h3 class="sub-heading">Notes to Operating Statement</h3>
      <p><strong>[1] Real Estate Taxes:</strong> Reassessed at purchase price per standard buyer underwriting. At $1,300,000 x 1.17% (LA County benchmark rate): $15,210/yr. Seller currently pays less under Prop 13; new ownership triggers full reassessment.</p>
      <p><strong>[2] Insurance:</strong> Owner's verified 2025 actual: $1,918/yr. Reflects the seller's self-managed policy for this 3-unit 1952 property.</p>
      <p><strong>[3] Pest Control:</strong> Owner's verified 2025 actual: $1,032/yr. Annual service contract.</p>
      <p><strong>[4] Utilities:</strong> Owner's verified 2025 actual: $2,772/yr. Water is owner-paid; tenants pay their own electricity and gas (individually metered).</p>
      <p><strong>[5] Trash Removal:</strong> Owner's verified 2025 actual: $1,496/yr. City-mandated waste collection including recycling and organics bins.</p>
      <p><strong>[6] Repairs &amp; Maintenance:</strong> Normalized at $2,250/yr. 1952 vintage with new hot water heater installed 2025 (CapEx credit applied). Reflects typical annual maintenance for a well-maintained 3-unit structure.</p>
      <p><strong>[7] Service Contracts:</strong> $1,500/yr. Includes gardener and ongoing maintenance service contracts.</p>
    </div>
  </div>
</div>

<!-- FINANCIAL SCREEN 3: SUMMARY -->
<div class="section section-alt">
  <div class="summary-page">
    <div class="summary-banner">Summary</div>
    <div class="summary-two-col">
      <div class="summary-left">
        <table class="summary-table">
          <thead><tr><th colspan="2" class="summary-header">OPERATING DATA</th></tr></thead>
          <tbody>
            <tr><td>Price</td><td class="num">{fmt(LIST_PRICE)}</td></tr>
            <tr><td>Down Payment (50%)</td><td class="num">{fmt(M['down'])}</td></tr>
            <tr><td>Number of Units</td><td class="num">{UNITS}</td></tr>
            <tr><td>Price / Unit</td><td class="num">{fmt(M['per_unit'])}</td></tr>
            <tr><td>Price / SF</td><td class="num">{fmt(M['per_sf'],0)}</td></tr>
            <tr><td>Gross SF</td><td class="num">{SF:,}</td></tr>
            <tr><td>Lot Size</td><td class="num">{LOT_SF:,} SF</td></tr>
            <tr><td>Year Built</td><td class="num">{YEAR_BUILT}</td></tr>
          </tbody>
        </table>
        <table class="summary-table">
          <thead><tr><th class="summary-header">Returns</th><th class="num summary-header">Current</th><th class="num summary-header">Pro Forma</th></tr></thead>
          <tbody>
            <tr><td>Cap Rate</td><td class="num">{pct(M['cur_cap'])}</td><td class="num">{pct(M['pf_cap'])}</td></tr>
            <tr><td>GRM</td><td class="num">{M['cur_grm']:.2f}x</td><td class="num">{M['pf_grm']:.2f}x</td></tr>
            <tr><td>Cash-on-Cash</td><td class="num">{pct(M['coc_cur'])}</td><td class="num">{pct(M['coc_pf'])}</td></tr>
            <tr><td>DCR</td><td class="num">{M['dcr_cur']:.2f}x</td><td class="num">{M['dcr_pf']:.2f}x</td></tr>
          </tbody>
        </table>
        <table class="summary-table">
          <thead><tr><th colspan="2" class="summary-header">FINANCING</th></tr></thead>
          <tbody>
            <tr><td>Loan Amount</td><td class="num">{fmt(M['loan'])}</td></tr>
            <tr><td>Type</td><td class="num">Conv. Investment</td></tr>
            <tr><td>Interest Rate</td><td class="num">6.25%</td></tr>
            <tr><td>Amortization</td><td class="num">30 Years</td></tr>
            <tr><td>Loan Constant</td><td class="num">{LOAN_CONST*100:.2f}%</td></tr>
            <tr><td>LTV</td><td class="num">{M['actual_ltv']*100:.1f}%</td></tr>
            <tr><td>DSCR (Current)</td><td class="num">{M['dcr_cur']:.2f}x</td></tr>
          </tbody>
        </table>
        <table class="summary-table">
          <thead><tr><th class="summary-header">Unit Summary</th><th class="num summary-header">Units</th><th class="num summary-header">Avg SF</th><th class="num summary-header">Cur. Rent</th><th class="num summary-header">Mkt Rent</th></tr></thead>
          <tbody>
            <tr><td>1BR / 1BA</td><td class="num">1</td><td class="num">635</td><td class="num">$1,920</td><td class="num">$2,095</td></tr>
            <tr><td>2BR / 1BA</td><td class="num">2</td><td class="num">850</td><td class="num">$1,991 avg</td><td class="num">$2,548</td></tr>
            <tr class="summary"><td>Total</td><td class="num">3</td><td class="num">778 avg</td><td class="num">$5,901/mo</td><td class="num">$7,191/mo</td></tr>
          </tbody>
        </table>
      </div>
      <div class="summary-right">
        <table class="summary-table">
          <thead><tr><th class="summary-header">Income</th><th class="num summary-header">Current</th><th class="num summary-header">Pro Forma</th></tr></thead>
          <tbody>
            <tr><td>Gross Scheduled Rent</td><td class="num">{fmt(GSR)}</td><td class="num">{fmt(PF_GSR)}</td></tr>
            <tr class="summary"><td>Effective Gross Income</td><td class="num">{fmt(CURRENT_EGI)}</td><td class="num">{fmt(PF_EGI)}</td></tr>
          </tbody>
        </table>
        <table class="summary-table">
          <thead><tr><th class="summary-header">Cash Flow</th><th class="num summary-header">Current</th><th class="num summary-header">Pro Forma</th></tr></thead>
          <tbody>
            <tr><td>Net Operating Income</td><td class="num">{fmt(CUR_NOI)}</td><td class="num">{fmt(PF_NOI)}</td></tr>
            <tr><td>Annual Debt Service</td><td class="num">({fmt(M['ds'])})</td><td class="num">({fmt(M['ds'])})</td></tr>
            <tr class="summary"><td>Cash Flow After DS</td><td class="num" style="color:{'#c0392b' if M['cur_cf']<0 else '#27ae60'};">{"(" + fmt(abs(M['cur_cf'])) + ")" if M['cur_cf']<0 else fmt(M['cur_cf'])}</td><td class="num" style="color:{'#27ae60' if M['pf_cf']>0 else '#c0392b'};">{fmt(M['pf_cf']) if M['pf_cf']>0 else "(" + fmt(abs(M['pf_cf'])) + ")"}</td></tr>
            <tr><td>Cash-on-Cash Return</td><td class="num">{pct(M['coc_cur'])}</td><td class="num">{pct(M['coc_pf'])}</td></tr>
            <tr><td>Principal Reduction (Yr 1)</td><td class="num">{fmt(M['prin'])}</td><td class="num">{fmt(M['prin'])}</td></tr>
            <tr class="summary"><td>Total Return</td><td class="num">{pct(M['total_ret_cur'])}</td><td class="num">{pct(M['total_ret_pf'])}</td></tr>
          </tbody>
        </table>
        <table class="summary-table">
          <thead><tr><th class="summary-header">Expenses</th><th class="num summary-header">Current</th><th class="num summary-header">Pro Forma</th></tr></thead>
          <tbody>
            {exp_detail_rows}
            <tr class="summary"><td>Total Expenses</td><td class="num">{fmt(CUR_TOTAL_EXP)}</td><td class="num">{fmt(PF_TOTAL_EXP)}</td></tr>
            <tr class="summary"><td>Net Operating Income</td><td class="num">{fmt(CUR_NOI)}</td><td class="num">{fmt(PF_NOI)}</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<!-- FINANCIAL SCREEN 4: PRICE REVEAL + MATRIX -->
<div class="section section-alt">
  <div class="price-reveal">
    <div style="text-align:center;margin-bottom:32px;">
      <div style="font-size:13px;text-transform:uppercase;letter-spacing:2px;color:#C5A258;font-weight:600;margin-bottom:8px;">Suggested List Price</div>
      <div style="font-size:56px;font-weight:700;color:#1B3A5C;line-height:1;">{fmt(LIST_PRICE)}</div>
    </div>

    <div class="metrics-grid-4">
      {build_metric_card(fmt(M['per_unit']), "Price / Unit")}
      {build_metric_card(f"${M['per_sf']:.0f}", "Price / SF")}
      {build_metric_card(pct(M['pf_cap']), "Pro Forma Cap Rate")}
      {build_metric_card(f"{M['pf_grm']:.2f}x", "Pro Forma GRM")}
    </div>

    <h3 class="sub-heading">Pricing Matrix</h3>
    <div class="table-scroll">
      <table>
        <thead><tr>
          <th class="num">Purchase Price</th>
          <th class="num">Current Cap</th>
          <th class="num">Pro Forma Cap</th>
          <th class="num">Cash-on-Cash</th>
          <th class="num">$/SF</th>
          <th class="num">$/Unit</th>
          <th class="num">PF GRM</th>
        </tr></thead>
        <tbody>{matrix_rows}</tbody>
      </table>
    </div>

    <div class="summary-trade-range">
      <div class="summary-trade-label">A TRADE PRICE IN THE CURRENT INVESTMENT ENVIRONMENT OF</div>
      <div class="summary-trade-prices">{fmt(TRADE_LOW)} &mdash; {fmt(TRADE_HIGH)}</div>
    </div>

    <h3 class="sub-heading">Pricing Rationale</h3>
    <p>The Castle Lane triplex is positioned at $1,300,000 -- $433K/unit, anchored by three comparable sales in this immediate submarket. Most significantly, 4543 Rockland Pl -- located approximately 100 feet away -- sold for $1,700,000 in October 2025, providing the strongest single pricing benchmark available. The two triplex comps (2511 Hermosa Ave at $1,340,000 and 3357 Honolulu Ave at $1,450,000) average $465K/unit; the subject's three-unit income-producing structure relative to the Rockland owner-occupied format justifies a measured discount. At $433K/unit, the subject is priced 27% below the three-comp average of $593K/unit. All three comps sold at or above asking price in under 11 days during 2025, confirming deep buyer demand in this submarket.</p>
    <p>The underwriting uses the owner's verified 2025 actual expenses -- a lower and more accurate expense base than benchmark estimates. Total annual expenses are $26,178 (37.0% of EGI), producing a current NOI of $44,634 (3.43% cap rate at $1,300,000). The primary buyer pool for this asset is owner-users who will occupy one unit and offset their mortgage with the remaining two units' $3,981/mo in current rents -- buyers who value La Canada Flintridge's JPL-driven employment base, nationally ranked LCUSD schools, and persistent supply constraints above pure investor cap rate math. At market rents, the pro forma NOI is $60,114 and the pro forma cap rate is 4.62%. Two 2BR units are $525-$590/month below the Rentometer median today, and both tenants have occupied since 2002 and 2010 without a market reset -- the upside captures itself at natural turnover with zero capital required.</p>

    <div class="condition-note"><strong>Assumptions &amp; Conditions:</strong> This Broker Opinion of Value is based on information provided by the seller and obtained from public records and market data as of March 2026. Financial projections are estimates only and do not constitute a guarantee of future performance. Actual results will depend on market conditions, financing terms, and buyer-specific circumstances at the time of sale. LAAA Team at Marcus &amp; Millichap recommends independent verification of all data by qualified professionals.</div>
  </div>
</div>

<!-- ── FOOTER ── -->
<div class="footer" id="contact">
  <img src="{IMG['logo_white']}" class="footer-logo" alt="LAAA Team">
  <div class="footer-team">
    <div class="footer-person">
      <img src="{IMG['glen']}" class="footer-headshot" alt="Glen Scher">
      <div class="footer-name">Glen Scher</div>
      <div class="footer-title">Senior Managing Director Investments</div>
      <div class="footer-contact">
        <a href="tel:8182122808">(818) 212-2808</a><br>
        <a href="mailto:Glen.Scher@marcusmillichap.com">Glen.Scher@marcusmillichap.com</a><br>
        CA License: 01962976
      </div>
    </div>
    <div class="footer-person">
      <img src="{IMG['filip']}" class="footer-headshot" alt="Filip Niculete">
      <div class="footer-name">Filip Niculete</div>
      <div class="footer-title">Senior Managing Director Investments</div>
      <div class="footer-contact">
        <a href="tel:8182122748">(818) 212-2748</a><br>
        <a href="mailto:Filip.Niculete@marcusmillichap.com">Filip.Niculete@marcusmillichap.com</a><br>
        CA License: 01905352
      </div>
    </div>
  </div>
  <div class="footer-office">16830 Ventura Blvd, Ste. 100, Encino, CA 91436 &nbsp;|&nbsp; marcusmillichap.com/laaa-team</div>
  <div class="footer-disclaimer">This information has been secured from sources we believe to be reliable, but we make no representations or warranties, expressed or implied, as to the accuracy of the information. Buyer must verify the information and bears all risk for any inaccuracies. Marcus &amp; Millichap Real Estate Investment Services, Inc. | License: CA 01930580.</div>
</div>

<script>
{js}
</script>
</body>
</html>"""

    print(f"Writing {OUT_FILE} ...")
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    size_kb = os.path.getsize(OUT_FILE) / 1024
    print(f"Done! {OUT_FILE}  ({size_kb:.0f} KB)")

if __name__ == "__main__":
    main()
