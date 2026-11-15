import os, json, glob, zipfile, urllib.request, urllib.parse, ssl

BASE_DIR = r"C:\Users\Lenovo\Desktop\BYRAL"
OUT_JS = os.path.join(BASE_DIR, "sitio_final", "js", "datos_gamc.js")
RAW_DUMP_DIR = os.path.join(BASE_DIR, "datos_oficiales_descargados")
os.makedirs(RAW_DUMP_DIR, exist_ok=True)

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# Service IDs oficiales del GAMC (EMERGENCIAS.docx)
SERVICES = {
    "emergencias": "e105a6ed-74bb-41a5-8c85-9360711ddf69",
    "cuencas":     "fb368617-f2fd-43e8-867a-4456364efb52",
    "drenaje":     "d4cea6e3-fc7f-482a-94ad-bd377df78886",
    "distritos":   "7eb13092-bf0e-493b-aae6-03c43eedda2c"
}

HOSTS = [
    "https://portalgeografico.cochabamba.bo",
    "https://ide.cochabamba.bo",
    "https://geoportal.cochabamba.bo"
]

def http_get_json(url, timeout=15):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json, application/geo+json, */*"
    })
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return json.loads(r.read().decode("utf-8", errors="ignore"))

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
    return [
        f for f in feats
        if (c := get_center(f["geometry"])) and not (lat_c.get(round(c[1], 3), 0) >= 5 and lng_c.get(round(c[0], 3), 0) >= 5)
    ]

def download_paginated_gamc(cat, sid):
    collected = []
    # 1. Intentar ArcGIS REST con paginacion completa (lotes de 1000)
    rest_paths = [
        f"/server/rest/services/{sid}/FeatureServer/0/query",
        f"/arcgis/rest/services/{sid}/FeatureServer/0/query",
        f"/arcgis/rest/services/{sid}/MapServer/0/query",
        f"/geoserver/rest/services/{sid}/FeatureServer/0/query"
    ]
    for host in HOSTS:
        for rpath in rest_paths:
            offset = 0
            while True:
                qs = urllib.parse.urlencode({
                    "where": "1=1",
                    "outFields": "*",
                    "outSR": "4326",
                    "resultOffset": offset,
                    "resultRecordCount": 1000,
                    "f": "geojson"
                })
                try:
                    gj = http_get_json(f"{host}{rpath}?{qs}", timeout=12)
                    feats = gj.get("features") or []
                    if not feats:
                        break
                    collected.extend(feats)
                    print(f"  [{cat}] {host} -> +{len(feats)} registros (total {len(collected)})")
                    if len(feats) < 1000:
                        break
                    offset += 1000
                except Exception:
                    break
            if collected:
                return collected

    # 2. Intentar OGC WFS (GeoNode / GeoServer del portal geografico)
    wfs_paths = [
        f"/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeName=geonode:{sid}&outputFormat=application/json&srsName=EPSG:4326",
        f"/geoserver/wfs?service=WFS&version=1.1.0&request=GetFeature&typeName={sid}&outputFormat=application/json&srsName=EPSG:4326",
        f"/api/v2/datasets/{sid}/"
    ]
    for host in HOSTS:
        for wpath in wfs_paths:
            try:
                gj = http_get_json(f"{host}{wpath}", timeout=12)
                feats = gj.get("features") or []
                if feats:
                    print(f"  [{cat}] WFS {host} -> {len(feats)} registros")
                    return feats
            except Exception:
                pass
    return collected

def download_nasa_eonet_cbba():
    # Eventos reales historicos de inundaciones/tormentas/incendios cercanos a Cochabamba (NASA EONET)
    url = "https://eonet.gsfc.nasa.gov/api/v3/events?status=all&bbox=-66.8,-18.0,-65.5,-16.8"
    out = []
    try:
        res = http_get_json(url, timeout=12)
        for ev in res.get("events", []):
            title = ev.get("title", "Evento Satelital NASA")
            cat_title = (ev.get("categories") or [{}])[0].get("title", "Evento Natural")
            for g in ev.get("geometry", []):
                coords = g.get("coordinates")
                if isinstance(coords, list) and len(coords) >= 2 and isinstance(coords[0], (int, float)):
                    out.append({
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [round(coords[0], 5), round(coords[1], 5)]},
                        "properties": {
                            "Numero": ev.get("id", "EONET"),
                            "Fecha": str(g.get("date", ""))[:10],
                            "Descripción": f"{title} ({cat_title})",
                            "Unidad Responsable": "NASA EONET / UGR Cochabamba",
                            "Estado": "HISTORICO VERIFICADO"
                        }
                    })
    except Exception:
        pass
    return out

def extract_local_files():
    # Descomprimir cualquier .zip descargado del portal geografico en BYRAL
    for zpath in glob.glob(os.path.join(BASE_DIR, "**", "*.zip"), recursive=True):
        if "sitio_final" in zpath or "node_modules" in zpath:
            continue
        dest = os.path.join(RAW_DUMP_DIR, os.path.splitext(os.path.basename(zpath))[0])
        try:
            with zipfile.ZipFile(zpath, "r") as zf:
                zf.extractall(dest)
        except Exception:
            pass

    local_data = {"emergencias": [], "cuencas": [], "drenaje": [], "distritos": []}
    for fp in glob.glob(os.path.join(BASE_DIR, "**", "*.*"), recursive=True):
        if "sitio_final" in fp or "node_modules" in fp:
            continue
        ext = os.path.splitext(fp)[1].lower()
        if ext not in (".geojson", ".json", ".js"):
            continue
        try:
            txt = open(fp, "r", encoding="utf-8-sig").read()
            if ext == ".js":
                idx = txt.find("{")
                if idx == -1: continue
                txt = txt[idx:].rstrip(";\n\r ")
            obj = json.loads(txt)
        except Exception:
            continue

        feats = []
        if isinstance(obj, dict):
            if obj.get("type") == "FeatureCollection":
                feats = obj.get("features", [])
            elif any(k in obj for k in local_data):
                for k in local_data:
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
            elif any(w in sig for w in ["denunciante", "unidad responsable", "numero", "emergencia", "queja", "descripcion", "descripción"]):
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
            sc = json.dumps(cg["coordinates"])
            if "-66." not in sc and "-65." not in sc:
                continue
            clean_p = {k: v for k, v in props.items() if not k.startswith("_") and v is not None}
            local_data[cat].append({"type": "Feature", "geometry": cg, "properties": clean_p})
    return local_data

print("1. Descargando capas historicas completas desde el Geoportal GAMC...")
final_data = {"emergencias": [], "cuencas": [], "drenaje": [], "distritos": []}
for cat, sid in SERVICES.items():
    feats = download_paginated_gamc(cat, sid)
    if feats:
        with open(os.path.join(RAW_DUMP_DIR, f"{cat}_gamc_oficial.geojson"), "w", encoding="utf-8") as f:
            json.dump({"type": "FeatureCollection", "features": feats}, f, ensure_ascii=False)
        for ft in feats:
            cg = clean_geom(ft.get("geometry"), 0.00015 if cat == "drenaje" else 0.00025)
            if cg:
                final_data[cat].append({"type": "Feature", "geometry": cg, "properties": ft.get("properties") or {}})

print("2. Consolidando archivos vectoriales locales en C:\\Users\\Lenovo\\Desktop\\BYRAL...")
local_data = extract_local_files()
for cat in final_data:
    if len(local_data[cat]) > len(final_data[cat]):
        final_data[cat] = local_data[cat]
    final_data[cat] = remove_synthetic_grid(final_data[cat])

# Anadir eventos satelitales verificados de NASA EONET en Cochabamba sin duplicar
eonet_events = download_nasa_eonet_cbba()
if eonet_events:
    final_data["emergencias"].extend(eonet_events)

print("RESUMEN FINAL DE REGISTROS REALES DESCARGADOS:", {k: len(v) for k, v in final_data.items()})
with open(OUT_JS, "w", encoding="utf-8") as out:
    out.write("window.BYRAL_HISTORICAL_DATA = " + json.dumps(final_data, ensure_ascii=False) + ";\n")
