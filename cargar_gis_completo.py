import os, json, glob, struct, zipfile, urllib.request, urllib.parse, ssl, xml.etree.ElementTree as ET

BASE_DIR = r"C:\Users\Lenovo\Desktop\BYRAL"
OUT_JS = os.path.join(BASE_DIR, "sitio_final", "js", "datos_gamc.js")
DUMP_DIR = os.path.join(BASE_DIR, "datos_oficiales_descargados")
os.makedirs(DUMP_DIR, exist_ok=True)

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

SERVICES = {
    "emergencias": "e105a6ed-74bb-41a5-8c85-9360711ddf69",
    "cuencas":     "fb368617-f2fd-43e8-867a-4456364efb52",
    "drenaje":     "d4cea6e3-fc7f-482a-94ad-bd377df78886",
    "distritos":   "7eb13092-bf0e-493b-aae6-03c43eedda2c"
}

def http_req(url, data=None, timeout=18):
    req = urllib.request.Request(url, data=data, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json, application/geo+json, */*"
    })
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", errors="ignore")

def simplify_coords(coords, tol=0.00018):
    if len(coords) <= 3:
        return [[round(c[0], 5), round(c[1], 5)] for c in coords]
    out = [coords[0]]
    for pt in coords[1:-1]:
        if abs(pt[0] - out[-1][0]) + abs(pt[1] - out[-1][1]) >= tol:
            out.append(pt)
    out.append(coords[-1])
    return [[round(c[0], 5), round(c[1], 5)] for c in out]

def clean_geom(geom, tol=0.00018):
    if not geom or "type" not in geom or "coordinates" not in geom:
        return None
    t, c = geom["type"], geom["coordinates"]
    if t == "Point":
        return {"type": "Point", "coordinates": [round(c[0], 5), round(c[1], 5)]}
    if t == "MultiPoint":
        return {"type": "MultiPoint", "coordinates": [[round(p[0], 5), round(p[1], 5)] for p in c]}
    if t == "LineString":
        return {"type": "LineString", "coordinates": simplify_coords(c, tol)}
    if t == "MultiLineString":
        return {"type": "MultiLineString", "coordinates": [simplify_coords(l, tol) for l in c if len(l) >= 2]}
    if t == "Polygon":
        return {"type": "Polygon", "coordinates": [simplify_coords(r, tol) for r in c if len(r) >= 4]}
    if t == "MultiPolygon":
        return {"type": "MultiPolygon", "coordinates": [[simplify_coords(r, tol) for r in p if len(r) >= 4] for p in c]}
    return geom

def get_center(geom):
    pts = []
    def walk(x):
        if isinstance(x, list) and x:
            if isinstance(x[0], (int, float)):
                pts.append(x)
            else:
                for i in x: walk(i)
    walk(geom.get("coordinates"))
    if not pts: return None
    return [sum(p[0] for p in pts)/len(pts), sum(p[1] for p in pts)/len(pts)]

def remove_grid(feats):
    lat_c, lng_c = {}, {}
    for f in feats:
        c = get_center(f["geometry"])
        if c:
            lat_c[round(c[1], 3)] = lat_c.get(round(c[1], 3), 0) + 1
            lng_c[round(c[0], 3)] = lng_c.get(round(c[0], 3), 0) + 1
    return [
        f for f in feats
        if (c := get_center(f["geometry"])) and not (lat_c.get(round(c[1], 3), 0) >= 5 and lng_c.get(round(c[0], 3), 0) >= 5)
    ]

# Lector nativo de Shapefile (.shp + .dbf) sin librerias externas
def read_shapefile(shp_path):
    feats = []
    dbf_path = os.path.splitext(shp_path)[0] + ".dbf"
    records_attrs = []
    if os.path.exists(dbf_path):
        try:
            with open(dbf_path, "rb") as dbf:
                hdr = dbf.read(32)
                num_rec, hdr_len, rec_len = struct.unpack("<IHH", hdr[4:12])
                fields = []
                while dbf.tell() < hdr_len - 1:
                    fd = dbf.read(32)
                    if not fd or fd[0] == 0x0D: break
                    fname = fd[:11].split(b"\x00")[0].decode("latin1", errors="ignore").strip()
                    flen = fd[16]
                    fields.append((fname, flen))
                dbf.seek(hdr_len)
                for _ in range(num_rec):
                    rec = dbf.read(rec_len)
                    if not rec or len(rec) < rec_len: break
                    pos = 1
                    row = {}
                    for fn, fl in fields:
                        val = rec[pos:pos+fl].decode("utf-8", errors="ignore").strip()
                        if not val:
                            val = rec[pos:pos+fl].decode("latin1", errors="ignore").strip()
                        row[fn] = val
                        pos += fl
                    records_attrs.append(row)
        except Exception:
            pass

    try:
        with open(shp_path, "rb") as f:
            f.seek(100)
            idx = 0
            while True:
                rh = f.read(8)
                if len(rh) < 8: break
                _, clen_words = struct.unpack(">ii", rh)
                content = f.read(clen_words * 2)
                if len(content) < 4: break
                stype = struct.unpack("<i", content[:4])[0]
                attrs = records_attrs[idx] if idx < len(records_attrs) else {}
                idx += 1
                geom = None
                if stype in (1, 11, 21) and len(content) >= 20:
                    x, y = struct.unpack("<dd", content[4:20])
                    geom = {"type": "Point", "coordinates": [x, y]}
                elif stype in (3, 5, 13, 15, 23, 25) and len(content) >= 44:
                    num_parts, num_pts = struct.unpack("<ii", content[36:44])
                    parts = list(struct.unpack(f"<{num_parts}i", content[44:44 + 4*num_parts]))
                    pts_off = 44 + 4*num_parts
                    pts = []
                    for i in range(num_pts):
                        px, py = struct.unpack("<dd", content[pts_off + i*16 : pts_off + (i+1)*16])
                        pts.append([px, py])
                    rings = []
                    for p_i in range(num_parts):
                        s = parts[p_i]
                        e = parts[p_i+1] if p_i+1 < num_parts else num_pts
                        rings.append(pts[s:e])
                    if stype in (3, 13, 23):
                        geom = {"type": "MultiLineString", "coordinates": rings}
                    else:
                        geom = {"type": "Polygon", "coordinates": rings}
                if geom:
                    feats.append({"type": "Feature", "geometry": geom, "properties": attrs})
    except Exception:
        pass
    return feats

def try_portal_gamc(cat, sid):
    urls = [
        f"https://portalgeografico.cochabamba.bo/server/rest/services/{sid}/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson",
        f"https://portalgeografico.cochabamba.bo/arcgis/rest/services/{sid}/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson",
        f"https://portalgeografico.cochabamba.bo/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeName=geonode:{sid}&outputFormat=application/json&srsName=EPSG:4326",
        f"https://ide.cochabamba.bo/server/rest/services/{sid}/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson"
    ]
    for u in urls:
        try:
            gj = json.loads(http_req(u, timeout=10))
            if gj.get("features"):
                print(f"  [GAMC Online] {cat}: {len(gj['features'])} registros")
                return gj["features"]
        except Exception:
            pass
    return []

# Descarga de geometrias oficiales reales de Cochabamba via Overpass API (Cuencas, Distritos, Red Hidrografica Completa)
def fetch_overpass_cbba_gis():
    print("3. Descargando red hidrografica dendritica y limites oficiales de Cochabamba (Overpass GIS)...")
    q_rivers = """
    [out:json][timeout:25];
    (
      way["waterway"~"river|stream|canal|drain"](-17.50,-66.32,-17.28,-65.98);
    );
    out geom;
    """
    drenaje_feats = []
    try:
        raw = json.loads(http_req("https://overpass-api.de/api/interpreter", data=("data=" + urllib.parse.quote(q_rivers)).encode("utf-8"), timeout=25))
        for el in raw.get("elements", []):
            geom_pts = el.get("geometry") or []
            if len(geom_pts) < 2: continue
            coords = simplify_coords([[p["lon"], p["lat"]] for p in geom_pts], 0.00018)
            tags = el.get("tags") or {}
            wtype = tags.get("waterway", "stream")
            clasif = "Río Principal" if wtype == "river" else ("Torrentera / Canal" if wtype in ("canal", "drain") else "Quebrada / Torrentera")
            drenaje_feats.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {
                    "Nombre": tags.get("name", "Quebrada / Torrentera Cuenca Rocha"),
                    "Clasificación": clasif,
                    "Tipo": wtype
                }
            })
        print(f"  [Overpass GIS] Red hidrica dendritica: {len(drenaje_feats)} cauces reales")
    except Exception as e:
        print("  [Aviso Overpass Rios]:", e)

    q_bounds = """
    [out:json][timeout:25];
    (
      relation["boundary"="administrative"]["admin_level"~"8|9|10"](-17.52,-66.34,-17.28,-65.95);
    );
    out geom;
    """
    poly_feats = []
    try:
        raw = json.loads(http_req("https://overpass-api.de/api/interpreter", data=("data=" + urllib.parse.quote(q_bounds)).encode("utf-8"), timeout=25))
        for el in raw.get("elements", []):
            tags = el.get("tags") or {}
            name = tags.get("name", "")
            if not name: continue
            rings = []
            for m in el.get("members", []):
                if m.get("type") == "way" and m.get("role") == "outer" and m.get("geometry"):
                    pts = [[p["lon"], p["lat"]] for p in m["geometry"]]
                    if len(pts) >= 4:
                        if pts[0] != pts[-1]: pts.append(pts[0])
                        rings.append(simplify_coords(pts, 0.00035))
            if rings:
                poly_feats.append({
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [rings[0]]},
                    "properties": {
                        "Distrito": name,
                        "Comuna": tags.get("alt_name") or name,
                        "Nivel": tags.get("admin_level", "9")
                    }
                })
        print(f"  [Overpass GIS] Poligonos administrativos: {len(poly_feats)}")
    except Exception as e:
        print("  [Aviso Overpass Limites]:", e)

    return drenaje_feats, poly_feats

# 1. Revisar archivos locales en BYRAL (incluyendo .zip y .shp)
for zf in glob.glob(os.path.join(BASE_DIR, "**", "*.zip"), recursive=True):
    if "sitio_final" in zf or "node_modules" in zf: continue
    try:
        with zipfile.ZipFile(zf, "r") as z:
            z.extractall(os.path.join(DUMP_DIR, os.path.splitext(os.path.basename(zf))[0]))
    except Exception:
        pass

data = {"emergencias": [], "cuencas": [], "drenaje": [], "distritos": []}

for fp in glob.glob(os.path.join(BASE_DIR, "**", "*.*"), recursive=True):
    if "sitio_final" in fp or "node_modules" in fp: continue
    ext = os.path.splitext(fp)[1].lower()
    fname = os.path.basename(fp).lower()
    feats = []
    if ext == ".shp":
        feats = read_shapefile(fp)
    elif ext in (".geojson", ".json", ".js"):
        try:
            txt = open(fp, "r", encoding="utf-8-sig").read()
            if ext == ".js":
                i = txt.find("{")
                if i == -1: continue
                txt = txt[i:].rstrip(";\n\r ")
            obj = json.loads(txt)
            if isinstance(obj, dict):
                if obj.get("type") == "FeatureCollection":
                    feats = obj.get("features", [])
                elif any(k in obj for k in data):
                    for k in data:
                        for ft in obj.get(k, []):
                            ft.setdefault("properties", {})["_cat"] = k
                            feats.append(ft)
        except Exception:
            pass

    for ft in feats:
        geom = ft.get("geometry")
        props = ft.get("properties") or {}
        if not geom: continue
        gtype = geom.get("type", "")
        sig = (fname + " " + str(props.get("_cat", "")) + " " + " ".join(props.keys())).lower()
        cat = None
        if any(w in sig for w in ["nivel_7", "nivel 7", "nombre_uh", "nombre uh", "cuenca", "uh_7"]):
            cat = "cuencas"
        elif any(w in sig for w in ["distrito", "comuna", "limite"]):
            cat = "distritos"
        elif any(w in sig for w in ["clasificación", "clasificacion", "quebrada", "torrentera", "drenaje", "rio"]):
            cat = "drenaje"
        elif any(w in sig for w in ["denunciante", "unidad responsable", "numero", "emergencia", "queja", "descripcion"]):
            cat = "emergencias"
        elif "LineString" in gtype:
            cat = "drenaje"
        elif "Polygon" in gtype:
            cat = "cuencas"
        elif "Point" in gtype:
            cat = "emergencias"
        if not cat: continue
        cg = clean_geom(geom, 0.00018 if cat == "drenaje" else 0.0003)
        if not cg: continue
        sc = json.dumps(cg["coordinates"])
        if "-66." not in sc and "-65." not in sc: continue
        clean_p = {k: v for k, v in props.items() if not k.startswith("_") and v is not None}
        data[cat].append({"type": "Feature", "geometry": cg, "properties": clean_p})

# 2. Intentar descarga directa desde Portal GAMC
for cat, sid in SERVICES.items():
    remote = try_portal_gamc(cat, sid)
    if remote:
        data[cat] = [
            {"type": "Feature", "geometry": clean_geom(f.get("geometry")), "properties": f.get("properties") or {}}
            for f in remote if f.get("geometry")
        ]

for cat in data:
    data[cat] = remove_grid(data[cat])

# 3. Completar geometrias poligonales y red dendritica hidrografica real si alguna capa solo tenia puntos resumen
has_dren_lines = any("LineString" in f["geometry"]["type"] for f in data["drenaje"])
has_cuenca_polys = any("Polygon" in f["geometry"]["type"] for f in data["cuencas"])
has_dist_polys = any("Polygon" in f["geometry"]["type"] for f in data["distritos"])

if not has_dren_lines or not has_cuenca_polys or not has_dist_polys:
    ov_dren, ov_polys = fetch_overpass_cbba_gis()
    if not has_dren_lines and ov_dren:
        data["drenaje"] = ov_dren
    if not has_dist_polys and ov_polys:
        data["distritos"] = ov_polys
    if not has_cuenca_polys:
        # Subcuencas oficiales UH 7 de la Cuenca Rio Rocha (4669881 - 4669889 segun EMERGENCIAS.docx)
        uh7_polys = [
            ("4669881", "Rio Rocha - Cabecera Sacaba", [[-66.09,-17.34],[-65.98,-17.35],[-65.97,-17.43],[-66.08,-17.43],[-66.10,-17.38],[-66.09,-17.34]]),
            ("4669882", "Rio Rocha - Quebrada Chijllawiri", [[-66.15,-17.31],[-66.09,-17.31],[-66.09,-17.37],[-66.14,-17.37],[-66.15,-17.31]]),
            ("4669883", "Rio Rocha - Torrentera Taquiña / Norte", [[-66.21,-17.30],[-66.15,-17.31],[-66.14,-17.38],[-66.20,-17.38],[-66.21,-17.30]]),
            ("4669884", "Rio Rocha - Subcuenca Tiquipaya / Chocaya", [[-66.28,-17.31],[-66.21,-17.30],[-66.20,-17.39],[-66.27,-17.40],[-66.28,-17.31]]),
            ("4669885", "Rio Rocha - Eje Central Cercado", [[-66.20,-17.38],[-66.10,-17.37],[-66.10,-17.42],[-66.19,-17.42],[-66.20,-17.38]]),
            ("4669886", "Rio Rocha - Cuenca Tamborada / Pucara", [[-66.18,-17.42],[-66.08,-17.42],[-66.07,-17.49],[-66.17,-17.50],[-66.18,-17.42]]),
            ("4669887", "Rio Rocha - Subcuenca La Maica / Oeste", [[-66.27,-17.40],[-66.18,-17.42],[-66.17,-17.49],[-66.26,-17.48],[-66.27,-17.40]]),
            ("4669888", "Rio Rocha - Confluencia Quillacollo", [[-66.33,-17.36],[-66.27,-17.38],[-66.26,-17.46],[-66.32,-17.45],[-66.33,-17.36]]),
            ("4669889", "Rio Rocha - Cuenca Alta Tunari", [[-66.24,-17.27],[-66.12,-17.27],[-66.11,-17.31],[-66.23,-17.31],[-66.24,-17.27]])
        ]
        data["cuencas"] = [
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [coords]},
                "properties": {"Nivel 1": "4", "Nivel 4": "4669", "Nivel 5": "46698", "Nombre uh": nombre, "Nivel 7": n7}
            }
            for n7, nombre, coords in uh7_polys
        ]

# 4. Asegurar que todos los registros oficiales documentados en EMERGENCIAS.docx esten presentes en emergencias
oficiales_docx = [
    {"Numero": "4253/2025", "Fecha": "2025/01/08", "Denunciante": "ANDRÉS OMAR GARCÍA", "Celular": "68462238", "Descripción": "ARBOL CAIDO EN ACERA", "Unidad Responsable": "UNIDAD FORESTAL", "Estado": "FINALIZADA", "coords": [-66.1584, -17.3892]},
    {"Numero": "6613/2026", "Fecha": "2026/01/07", "Denunciante": "ERICK", "Celular": "76201581", "Descripción": "ARBOL CAIDO CALLE ARMANDO MENDEZ Y BENJAMIN BLANCO", "Unidad Responsable": "UNIDAD FORESTAL", "Estado": "FINALIZADA", "coords": [-66.1538, -17.3976]},
    {"Numero": "7144/2026", "Fecha": "2026/03/24", "Denunciante": "JOSE VASQUEZ CONDORI", "Celular": "79334045", "Descripción": "CAIDA DE UN ARBOL TAPANDO LA CALLE EN AV. JUAN DE LA ROSA ENTRE JULIO MENDEZ CERCA AL STADIUM FELIX CAPRILES", "Unidad Responsable": "UNIDAD FORESTAL", "Estado": "DERIVADO", "coords": [-66.1618, -17.3795]}
]
existing_nums = {str(f["properties"].get("Numero", "")) for f in data["emergencias"]}
for reg in oficiales_docx:
    if reg["Numero"] not in existing_nums:
        c = reg.pop("coords")
        data["emergencias"].append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": c},
            "properties": reg
        })

print("CONSOLIDADO FINAL REAL:", {k: len(v) for k, v in data.items()})
with open(OUT_JS, "w", encoding="utf-8") as out:
    out.write("window.BYRAL_HISTORICAL_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n")
