import requests, csv, json, html, re
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

WMS = "https://serviciosgamc.cochabamba.bo/api/gs/wms"
KEY = "15a5f168e26bd9270fc975b90aa09339b1706c9c8b290a6f"
SRV = {"em": "e105a6ed-74bb-41a5-8c85-9360711ddf69", "cu": "fb368617-f2fd-43e8-867a-4456364efb52", "dr": "d4cea6e3-fc7f-482a-94ad-bd377df78886", "di": "7eb13092-bf0e-493b-aae6-03c43eedda2c"}
MIN_X, MIN_Y, MAX_X, MAX_Y = -66.280703, -17.53119, -66.06952, -17.257306
BBOX = f"{MIN_X},{MIN_Y},{MAX_X},{MAX_Y}"
s = requests.Session()

def consultar_barrido(px, py):
    params = {"key": KEY, "service_id": SRV["em"], "SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetFeatureInfo", "LAYERS": "", "QUERY_LAYERS": "", "SRS": "EPSG:4326", "BBOX": BBOX, "WIDTH": "30", "HEIGHT": "30", "X": str(px), "Y": str(py), "INFO_FORMAT": "application/json", "FEATURE_COUNT": "200"}
    try:
        r = s.get(WMS, params=params, timeout=6)
        if r.status_code == 200: return (px, py, r.json().get("features", []))
    except Exception: pass
    return (px, py, [])

def consultar_detalle(sid, x, y):
    px = int(((x - MIN_X) / (MAX_X - MIN_X)) * 1000)
    py = int(((MAX_Y - y) / (MAX_Y - MIN_Y)) * 1000)
    params = {"key": KEY, "service_id": sid, "SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetFeatureInfo", "LAYERS": "", "QUERY_LAYERS": "", "SRS": "EPSG:4326", "BBOX": BBOX, "WIDTH": "1000", "HEIGHT": "1000", "X": str(px), "Y": str(py), "INFO_FORMAT": "application/json", "FEATURE_COUNT": "10"}
    try:
        r = s.get(WMS, params=params, timeout=5)
        if r.status_code == 200: return r.json().get("features", [])
    except Exception: pass
    return []

celdas = [(x, y) for x in range(0, 31, 3) for y in range(0, 31, 3)]
print(f"[1/3] Escaneando {len(celdas)} sectores amplios en GAMC...", flush=True)
raw = {}
with ThreadPoolExecutor(max_workers=16) as ex:
    for px, py, feats in [f.result() for f in as_completed([ex.submit(consultar_barrido, c[0], c[1]) for c in celdas])]:
        gx = MIN_X + (px / 30.0) * (MAX_X - MIN_X)
        gy = MAX_Y - (py / 30.0) * (MAX_Y - MIN_Y)
        for f in feats:
            props = f.get("properties", {})
            num = props.get("Numero")
            if num and num not in raw:
                coords = (f.get("geometry") or {}).get("coordinates")
                rx, ry = (coords[0], coords[1]) if (isinstance(coords, list) and len(coords) >= 2 and isinstance(coords[0], (int, float))) else (gx, gy)
                raw[num] = (props, rx, ry)

print(f"[2/3] {len(raw)} incidentes unicos capturados. Enriqueciendo...", flush=True)
pat = re.compile(r"INUNDA|ANEG|DESBORD|LLUVIA|RIO|TORRENT|ALCANTARILL|MAZAMORRA|AGUA|REBALS|CANAL|BOCATORMENTA", re.I)

def enriquecer(item):
    num, (p, x, y) = item
    di, cu, dr = consultar_detalle(SRV["di"], x, y), consultar_detalle(SRV["cu"], x, y), consultar_detalle(SRV["dr"], x, y)
    desc = " ".join(html.unescape(str(p.get("Descripción", ""))).split())
    return {"event_id": "GAMC-" + num.replace("/", "-"), "numero_oficial": num, "fecha_hora": p.get("Fecha"), "lat": round(y, 6), "lon": round(x, 6), "distrito": di[0]["properties"].get("Distrito", "N/D") if di else "N/D", "comuna": di[0]["properties"].get("Comuna", "N/D") if di else "N/D", "cuenca": cu[0]["properties"].get("Nombre uh", "N/D") if cu else "N/D", "cercania_drenaje": dr[0]["properties"].get("Clasificación", "Sin drenaje directo") if dr else "Sin drenaje directo", "descripcion_limpia": desc, "unidad_responsable": p.get("Unidad Responsable"), "estado_verificacion": p.get("Estado"), "es_hidrico": bool(pat.search(desc)), "fuente": "GAMC_WMS_API", "fecha_ingesta": datetime.now(timezone.utc).isoformat()}

with ThreadPoolExecutor(max_workers=16) as ex:
    rows = [f.result() for f in as_completed([ex.submit(enriquecer, it) for it in raw.items()])]
rows.sort(key=lambda r: str(r["fecha_hora"]), reverse=True)

with open("gamc_emergencias_limpio.csv", "w", newline="", encoding="utf-8-sig") as f1:
    w = csv.DictWriter(f1, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

d9, hid = [r for r in rows if r["distrito"] == "D9"], [r for r in rows if r["es_hidrico"]]
st = json.load(open("estado_alertas_mvp.json", encoding="utf-8"))
st["validacion_ground_truth_gamc"] = {"total_incidentes_ingestados": len(rows), "incidentes_en_distrito_9": len(d9), "incidentes_hidricos_confirmados": len(hid)}
json.dump(st, open("estado_alertas_mvp.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"[3/3] COMPLETADO -> Total: {len(rows)} | D9: {len(d9)} | Hidricos: {len(hid)}", flush=True)
