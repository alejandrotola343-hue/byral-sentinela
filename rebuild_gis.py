import os, json, glob

BASE_DIR = r"C:\Users\Lenovo\Desktop\BYRAL"
OUT_JS = os.path.join(BASE_DIR, "sitio_final", "js", "datos_gamc.js")

def simplify_line(coords, tol=0.00025):
    if len(coords) <= 3:
        return [[round(c[0], 5), round(c[1], 5)] for c in coords]
    out = [coords[0]]
    for pt in coords[1:-1]:
        prev = out[-1]
        if abs(pt[0] - prev[0]) + abs(pt[1] - prev[1]) >= tol:
            out.append(pt)
    out.append(coords[-1])
    return [[round(c[0], 5), round(c[1], 5)] for c in out]

def clean_geom(geom, tol=0.00025):
    if not geom or "type" not in geom or "coordinates" not in geom:
        return None
    t = geom["type"]
    c = geom["coordinates"]
    if t == "Point":
        return {"type": "Point", "coordinates": [round(c[0], 5), round(c[1], 5)]}
    if t == "MultiPoint":
        return {"type": "MultiPoint", "coordinates": [[round(p[0], 5), round(p[1], 5)] for p in c]}
    if t == "LineString":
        return {"type": "LineString", "coordinates": simplify_line(c, tol)}
    if t == "MultiLineString":
        return {"type": "MultiLineString", "coordinates": [simplify_line(line, tol) for line in c if len(line) >= 2]}
    if t == "Polygon":
        return {"type": "Polygon", "coordinates": [simplify_line(ring, tol) for ring in c if len(ring) >= 4]}
    if t == "MultiPolygon":
        return {
            "type": "MultiPolygon",
            "coordinates": [[simplify_line(ring, tol) for ring in poly if len(ring) >= 4] for poly in c]
        }
    return geom

def valid_cbba(geom):
    s = json.dumps(geom["coordinates"])
    return ("-66." in s or "-65." in s) and ("-17." in s or "-18." in s)

def load_all_features():
    data = {"cuencas": [], "distritos": [], "drenaje": [], "emergencias": []}
    patterns = ["**/*.geojson", "**/*.json"]
    files = []
    for pat in patterns:
        files.extend(glob.glob(os.path.join(BASE_DIR, pat), recursive=True))

    seen_files = set()
    for fp in files:
        if "sitio_final" in fp or "node_modules" in fp or fp in seen_files:
            continue
        seen_files.add(fp)
        fname = os.path.basename(fp).lower()
        try:
            with open(fp, "r", encoding="utf-8-sig") as f:
                obj = json.load(f)
        except Exception:
            continue

        feats = []
        if isinstance(obj, dict):
            if obj.get("type") == "FeatureCollection":
                feats = obj.get("features", [])
            elif obj.get("type") == "Feature":
                feats = [obj]
            else:
                for k, v in obj.items():
                    if isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict) and "geometry" in item:
                                item.setdefault("properties", {})["_cat_hint"] = k
                                feats.append(item)
        elif isinstance(obj, list):
            feats = [x for x in obj if isinstance(x, dict) and "geometry" in x]

        for ft in feats:
            geom = ft.get("geometry")
            props = ft.get("properties") or {}
            if not geom:
                continue
            gtype = geom.get("type", "")
            hint = (fname + " " + str(props.get("_cat_hint", "")) + " " + " ".join(props.keys())).lower()

            cat = None
            if any(w in hint for w in ["cuenca", "uh_", "nombre_uh", "hidrograf", "nivel_7", "subcuenca"]):
                cat = "cuencas"
            elif any(w in hint for w in ["distrito", "comuna", "limite", "subalcaldia", "otb"]):
                cat = "distritos"
            elif any(w in hint for w in ["drenaje", "rio", "río", "torrentera", "quebrada", "cauce", "red_hidrica", "hidrica"]):
                cat = "drenaje"
            elif any(w in hint for w in ["emergencia", "queja", "accidente", "inundacion", "evento", "riesgo", "incidente"]):
                cat = "emergencias"
            else:
                if "LineString" in gtype:
                    cat = "drenaje"
                elif "Polygon" in gtype:
                    cat = "cuencas"
                elif "Point" in gtype:
                    cat = "emergencias"

            if not cat:
                continue

            tol = 0.00018 if cat == "drenaje" else 0.00035
            cg = clean_geom(geom, tol)
            if not cg or not valid_cbba(cg):
                continue

            clean_props = {k: v for k, v in props.items() if not k.startswith("_") and v is not None}
            clean_props["_fuente"] = os.path.basename(fp)
            data[cat].append({"type": "Feature", "geometry": cg, "properties": clean_props})

    return data

res = load_all_features()
print({k: len(v) for k, v in res.items()})
with open(OUT_JS, "w", encoding="utf-8") as out:
    out.write("window.BYRAL_HISTORICAL_DATA = " + json.dumps(res, ensure_ascii=False) + ";\n")
