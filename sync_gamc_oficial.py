import os, json, glob, urllib.request, urllib.parse

BASE_DIR = r"C:\Users\Lenovo\Desktop\BYRAL"
OUT_JS = os.path.join(BASE_DIR, "sitio_final", "js", "datos_gamc.js")

SERVICES = {
    "emergencias": "e105a6ed-74bb-41a5-8c85-9360711ddf69",
    "cuencas":     "fb368617-f2fd-43e8-867a-4456364efb52",
    "drenaje":     "d4cea6e3-fc7f-482a-94ad-bd377df78886",
    "distritos":   "7eb13092-bf0e-493b-aae6-03c43eedda2c"
}

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

def remove_synthetic_grid(feats):
    lat_c, lng_c = {}, {}
    for f in feats:
        c = get_center(f["geometry"])
        if c:
            lat_c[round(c[1], 3)] = lat_c.get(round(c[1], 3), 0) + 1
            lng_c[round(c[0], 3)] = lng_c.get(round(c[0], 3), 0) + 1
    clean = []
    for f in feats:
        c = get_center(f["geometry"])
        if not c: continue
        if lat_c.get(round(c[1], 3), 0) >= 5 and lng_c.get(round(c[0], 3), 0) >= 5:
            continue
        clean.append(f)
    return clean

def fetch_gamc_service(cat, sid):
    hosts = [
        f"https://ide.cochabamba.bo/server/rest/services/{sid}/FeatureServer/0/query",
        f"https://ide.cochabamba.bo/arcgis/rest/services/{sid}/FeatureServer/0/query",
        f"https://ide.cochabamba.bo/arcgis/rest/services/{sid}/MapServer/0/query"
    ]
    params = urllib.parse.urlencode({"where": "1=1", "outFields": "*", "outSR": "4326", "f": "geojson"})
    for base in hosts:
        try:
            req = urllib.request.Request(f"{base}?{params}", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                gj = json.loads(resp.read().decode("utf-8"))
                if gj.get("features"):
                    print(f"Descargado oficial GAMC [{cat}]: {len(gj['features'])} elementos")
                    return gj["features"]
        except Exception:
            pass
    return []

data = {"cuencas": [], "distritos": [], "drenaje": [], "emergencias": []}

# 1. Buscar archivos GIS locales descargados en BYRAL
for fp in glob.glob(os.path.join(BASE_DIR, "**", "*.*"), recursive=True):
    if "sitio_final" in fp or "node_modules" in fp:
        continue
    ext = os.path.splitext(fp)[1].lower()
    if ext not in (".geojson", ".json", ".js"):
        continue
    try:
        raw_txt = open(fp, "r", encoding="utf-8-sig").read()
        if ext == ".js":
            idx = raw_txt.find("{")
            if idx == -1: continue
            raw_txt = raw_txt[idx:].rstrip(";\n\r ")
        obj = json.loads(raw_txt)
    except Exception:
        continue

    feats = []
    if isinstance(obj, dict):
        if obj.get("type") == "FeatureCollection":
            feats = obj.get("features", [])
        elif any(k in obj for k in data):
            for k in data:
                for ft in obj.get(k, []):
                    ft.setdefault("properties", {})["_cat"] = k
                    feats.append(ft)

    fname = os.path.basename(fp).lower()
    for ft in feats:
        geom = ft.get("geometry")
        props = ft.get("properties") or {}
        if not geom: continue
        gtype = geom.get("type", "")
        sig = (fname + " " + str(props.get("_cat", "")) + " " + " ".join(props.keys())).lower()

        cat = None
        if any(w in sig for w in ["nivel_7", "nombre_uh", "nombre uh", "cuenca", "uh_7", "uh 7"]):
            cat = "cuencas"
        elif any(w in sig for w in ["distrito", "comuna", "limite"]):
            cat = "distritos"
        elif any(w in sig for w in ["clasificación", "clasificacion", "quebrada", "torrentera", "drenaje", "rio"]):
            cat = "drenaje"
        elif any(w in sig for w in ["denunciante", "unidad responsable", "numero", "emergencia", "queja"]):
            cat = "emergencias"
        elif "LineString" in gtype:
            cat = "drenaje"
        elif "Polygon" in gtype:
            cat = "cuencas"
        elif "Point" in gtype:
            cat = "emergencias"

        if not cat: continue
        cg = clean_geom(geom, 0.00015 if cat == "drenaje" else 0.00025)
        if not cg: continue
        s_coords = json.dumps(cg["coordinates"])
        if "-66." not in s_coords and "-65." not in s_coords:
            continue
        clean_p = {k: v for k, v in props.items() if not k.startswith("_") and v is not None}
        data[cat].append({"type": "Feature", "geometry": cg, "properties": clean_p})

# 2. Intentar sincronizar directamente desde los service_id oficiales de EMERGENCIAS.docx si alguna capa tiene pocos elementos
for cat, sid in SERVICES.items():
    if len(data[cat]) < 6:
        remote_feats = fetch_gamc_service(cat, sid)
        if remote_feats:
            data[cat] = []
            for ft in remote_feats:
                cg = clean_geom(ft.get("geometry"), 0.00015 if cat == "drenaje" else 0.00025)
                if cg:
                    data[cat].append({"type": "Feature", "geometry": cg, "properties": ft.get("properties") or {}})

# 3. Eliminar puntos de grilla sintetica en todas las capas
for cat in data:
    data[cat] = remove_synthetic_grid(data[cat])

print("Resumen final cargado:", {k: len(v) for k, v in data.items()})
with open(OUT_JS, "w", encoding="utf-8") as out:
    out.write("window.BYRAL_HISTORICAL_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n")
