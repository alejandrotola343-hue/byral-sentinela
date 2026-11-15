import os, json, csv, math

base_dir = r"C:\Users\Lenovo\Desktop\BYRAL"
out_js = os.path.join(base_dir, "sitio_final", "js", "datos_gamc.js")

def utm19s_to_latlng(easting, northing):
    if abs(easting) <= 180 and abs(northing) <= 90:
        return round(northing, 6), round(easting, 6)
    a, e, e1sq, k0 = 6378137.0, 0.081819191, 0.006739497, 0.9996
    x, y = easting - 500000.0, northing - 10000000.0
    M = y / k0
    mu = M / (a * (1 - e**2/4 - 3*e**4/64 - 5*e**6/256))
    e1 = (1 - math.sqrt(1 - e**2)) / (1 + math.sqrt(1 - e**2))
    phi1 = mu + (3*e1/2 - 27*e1**3/32)*math.sin(2*mu) + (21*e1**2/16 - 55*e1**4/32)*math.sin(4*mu) + (151*e1**3/96)*math.sin(6*mu)
    N1 = a / math.sqrt(1 - (e*math.sin(phi1))**2)
    T1, C1 = math.tan(phi1)**2, e1sq * (math.cos(phi1)**2)
    R1 = a * (1 - e**2) / ((1 - (e*math.sin(phi1))**2)**1.5)
    D = x / (N1 * k0)
    lat = phi1 - (N1*math.tan(phi1)/R1)*(D**2/2 - (5 + 3*T1 + 10*C1 - 4*C1**2 - 9*e1sq)*D**4/24)
    lon = (-69.0*math.pi/180) + (D - (1 + 2*T1 + C1)*D**3/6 + (5 - 2*C1 + 28*T1 - 3*C1**2 + 8*e1sq + 24*T1**2)*D**5/120)/math.cos(phi1)
    return round(math.degrees(lat), 6), round(math.degrees(lon), 6)

def norm_coords(coords):
    if not isinstance(coords, list) or not coords: return None
    if isinstance(coords[0], (int, float)) and len(coords) >= 2:
        fx, fy = float(coords[0]), float(coords[1])
        if not (math.isfinite(fx) and math.isfinite(fy)): return None
        lat, lng = utm19s_to_latlng(fx, fy)
        return [lng, lat] if (math.isfinite(lat) and math.isfinite(lng)) else None
    out = [norm_coords(c) for c in coords]
    out = [c for c in out if c is not None]
    return out if out else None

def classify_cat(s):
    s = s.lower()
    if "cuenca" in s: return "cuencas"
    if any(k in s for k in ("dren", "rio", "hidro", "torrentera")): return "drenaje"
    if any(k in s for k in ("distrit", "comuna", "limite")): return "distritos"
    return "emergencias"

datasets = {"emergencias": [], "cuencas": [], "drenaje": [], "distritos": []}
seen = set()
skip = {".wrangler", "node_modules", ".git", "lib", "assets", "js", ".venv", "venv", "sitio_final"}

def add_feat(cat, geom, props, fn):
    if not geom or "coordinates" not in geom or "type" not in geom: return
    nc = norm_coords(geom["coordinates"])
    if not nc: return
    sig = f"{cat}|{json.dumps(nc)[:100]}|{str(props)[:60]}"
    if sig in seen: return
    seen.add(sig)
    cp = {str(k): v for k, v in (props or {}).items() if v is not None and str(v).strip() != "" and str(v).lower() != "nan"}
    cp["_fuente"] = fn
    datasets[cat].append({"type": "Feature", "geometry": {"type": geom["type"], "coordinates": nc}, "properties": cp})

def parse_obj(obj, cat, fn):
    if isinstance(obj, dict):
        if obj.get("type") == "FeatureCollection":
            for f in obj.get("features", []): add_feat(cat, f.get("geometry"), f.get("properties", {}), fn)
        elif obj.get("type") == "Feature":
            add_feat(cat, obj.get("geometry"), obj.get("properties", {}), fn)
        else:
            for k, v in obj.items(): parse_obj(v, classify_cat(f"{cat}_{k}"), fn)
    elif isinstance(obj, list):
        for it in obj:
            if not isinstance(it, dict): continue
            if it.get("type") == "Feature":
                add_feat(cat, it.get("geometry"), it.get("properties", {}), fn); continue
            rx = it.get("lng") or it.get("lon") or it.get("longitud") or it.get("Longitud") or it.get("x") or it.get("X") or it.get("ESTE")
            ry = it.get("lat") or it.get("latitud") or it.get("Latitud") or it.get("y") or it.get("Y") or it.get("NORTE")
            try:
                if rx is not None and ry is not None and float(rx) != 0 and float(ry) != 0:
                    add_feat(cat, {"type": "Point", "coordinates": [float(rx), float(ry)]}, it, fn)
            except Exception: pass

for root, dirs, files in os.walk(base_dir):
    dirs[:] = [d for d in dirs if d not in skip]
    for fn in files:
        if fn in ("datos_historicos_byral.json", "manifest_capas.json", "package.json", "package-lock.json"): continue
        fp, fl = os.path.join(root, fn), fn.lower()
        if fl.endswith((".geojson", ".json")):
            try: parse_obj(json.load(open(fp, encoding="utf-8", errors="ignore")), classify_cat(fl), fn)
            except Exception: pass
        elif fl.endswith(".csv"):
            try: parse_obj(list(csv.DictReader(open(fp, encoding="utf-8", errors="ignore"))), classify_cat(fl), fn)
            except Exception: pass

with open(out_js, "w", encoding="utf-8") as f:
    f.write("window.BYRAL_HISTORICAL_DATA = " + json.dumps(datasets, ensure_ascii=False, allow_nan=False).replace("</", "<\\/") + ";\n")

print("OK datos_gamc.js:", {k: len(v) for k, v in datasets.items()})
