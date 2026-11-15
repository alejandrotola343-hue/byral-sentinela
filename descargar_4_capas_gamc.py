import time, json, html, re, urllib3, requests
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

WMS = "https://serviciosgamc.cochabamba.bo/api/gs/wms"
KEY = "15a5f168e26bd9270fc975b90aa09339b1706c9c8b290a6f"
MIN_X, MIN_Y, MAX_X, MAX_Y = -66.280703, -17.53119, -66.06952, -17.257306
BBOX = f"{MIN_X},{MIN_Y},{MAX_X},{MAX_Y}"

SERVICIOS = {
    "emergencias": ("e105a6ed-74bb-41a5-8c85-9360711ddf69", "capa_emergencias.geojson", ["Numero", "numero"]),
    "cuencas":     ("fb368617-f2fd-43e8-867a-4456364efb52", "capa_cuencas.geojson",     ["Nivel 7", "nivel_7"]),
    "drenaje":     ("d4cea6e3-fc7f-482a-94ad-bd377df78886", "capa_drenaje.geojson",     ["OBJECTID", "FID", "Clasificación"]),
    "distritos":   ("7eb13092-bf0e-493b-aae6-03c43eedda2c", "capa_distritos.geojson",   ["Distrito", "distrito"]),
}

s = requests.Session()

def limpiar_props(props):
    out = {}
    for k, v in (props or {}).items():
        if isinstance(v, str):
            v = re.sub(r'\s+', ' ', html.unescape(v).replace("\xa0", " ")).strip()
        out[k] = v
    return out

def consultar_celda(sid, px, py):
    params = {
        "key": KEY, "service_id": sid, "SERVICE": "WMS", "VERSION": "1.1.1",
        "REQUEST": "GetFeatureInfo", "LAYERS": "", "QUERY_LAYERS": "",
        "SRS": "EPSG:4326", "BBOX": BBOX, "WIDTH": "30", "HEIGHT": "30",
        "X": str(px), "Y": str(py), "INFO_FORMAT": "application/json", "FEATURE_COUNT": "200"
    }
    for intento in range(3):
        try:
            time.sleep(0.25)  # Pausa amigable para evitar error 429
            r = s.get(WMS, params=params, timeout=10, verify=False)
            if r.status_code == 200:
                return (px, py, r.json().get("features", []))
            elif r.status_code == 429:
                print("    [!] Pausa de 15s por límite de velocidad del portal GAMC...", flush=True)
                time.sleep(15)
        except Exception:
            time.sleep(2)
    return (px, py, [])

# Cuadrícula amplia de 49 puntos (cubre todo Cochabamba sin saturar la API)
celdas = [(x, y) for x in range(0, 31, 5) for y in range(0, 31, 5)]

for nombre, (sid, archivo, id_keys) in SERVICIOS.items():
    print(f"[*] Descargando {nombre.upper()} ({len(celdas)} sectores)...", flush=True)
    unicos = {}

    with ThreadPoolExecutor(max_workers=2) as ex:
        futuros = [ex.submit(consultar_celda, sid, cx, cy) for cx, cy in celdas]
        for fut in as_completed(futuros):
            px, py, feats = fut.result()
            gx = round(MIN_X + (px / 30.0) * (MAX_X - MIN_X), 6)
            gy = round(MAX_Y - (py / 30.0) * (MAX_Y - MIN_Y), 6)

            for f in feats:
                props = limpiar_props(f.get("properties"))
                f["properties"] = props

                uid = None
                for k in id_keys:
                    if props.get(k) not in (None, ""):
                        uid = f"{k}:{props[k]}"
                        break
                if not uid or nombre == "drenaje":
                    geom_sig = json.dumps(f.get("geometry"), sort_keys=True)[:100]
                    uid = f"{uid}|{json.dumps(props, sort_keys=True)}|{geom_sig}"

                if not f.get("geometry"):
                    f["geometry"] = {"type": "Point", "coordinates": [gx, gy]}

                if uid not in unicos:
                    unicos[uid] = f

    features = list(unicos.values())
    with open(archivo, "w", encoding="utf-8") as out:
        json.dump({"type": "FeatureCollection", "features": features}, out, ensure_ascii=False)
    print(f"    [OK] {archivo} -> {len(features)} elementos guardados.", flush=True)
