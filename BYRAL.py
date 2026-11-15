import requests
import csv
import html
import re
from datetime import datetime, timezone

WMS_URL = "https://serviciosgamc.cochabamba.bo/api/gs/wms"
API_KEY = "15a5f168e26bd9270fc975b90aa09339b1706c9c8b290a6f"

SERVICES = {
    "emergencias": "e105a6ed-74bb-41a5-8c85-9360711ddf69",
    "cuencas_uh7": "fb368617-f2fd-43e8-867a-4456364efb52",
    "drenaje": "d4cea6e3-fc7f-482a-94ad-bd377df78886",
    "distritos": "7eb13092-bf0e-493b-aae6-03c43eedda2c"
}

MIN_LON, MIN_LAT = -66.280703, -17.53119
MAX_LON, MAX_LAT = -66.06952, -17.257306
BBOX_STR = f"{MIN_LON},{MIN_LAT},{MAX_LON},{MAX_LAT}"

def consultar_punto_wms(service_id, lon, lat):
    """Consulta GetFeatureInfo en una coordenada (lon, lat) usando EPSG:4326."""
    width, height = 1000, 1000
    pixel_x = int(((lon - MIN_LON) / (MAX_LON - MIN_LON)) * width)
    pixel_y = int(((MAX_LAT - lat) / (MAX_LAT - MIN_LAT)) * height)

    params = {
        "key": API_KEY,
        "service_id": service_id,
        "SERVICE": "WMS",
        "VERSION": "1.1.1",
        "REQUEST": "GetFeatureInfo",
        "LAYERS": "",
        "QUERY_LAYERS": "",
        "SRS": "EPSG:4326",
        "BBOX": BBOX_STR,
        "WIDTH": str(width),
        "HEIGHT": str(height),
        "X": str(pixel_x),
        "Y": str(pixel_y),
        "INFO_FORMAT": "application/json",
        "FEATURE_COUNT": "50"
    }
    try:
        r = requests.get(WMS_URL, params=params, timeout=10)
        if r.status_code == 200:
            return r.json().get("features", [])
    except Exception:
        pass
    return []

print("Extrayendo registros históricos desde el portal GAMC...")
registros_unicos = {}

lons = [MIN_LON + i * (MAX_LON - MIN_LON) / 15 for i in range(4, 13)]
lats = [MIN_LAT + j * (MAX_LAT - MIN_LAT) / 15 for j in range(3, 12)]
patron_hidrico = re.compile(r"INUNDA|ANEG|DESBORD|LLUVIA|RIO|TORRENT|ALCANTARILL|MAZAMORRA|AGUA", re.IGNORECASE)

for lon in lons:
    for lat in lats:
        features = consultar_punto_wms(SERVICES["emergencias"], lon, lat)
        for feat in features:
            props = feat.get("properties", {})
            num = props.get("Numero")
            if num and num not in registros_unicos:
                dist_feat = consultar_punto_wms(SERVICES["distritos"], lon, lat)
                distrito = dist_feat[0]["properties"].get("Distrito", "N/D") if dist_feat else "N/D"

                cuenca_feat = consultar_punto_wms(SERVICES["cuencas_uh7"], lon, lat)
                cuenca = cuenca_feat[0]["properties"].get("Nombre uh", "N/D") if cuenca_feat else "N/D"

                desc_limpia = html.unescape(str(props.get("Descripción", ""))).strip()
                desc_limpia = re.sub(r'\s+', ' ', desc_limpia)
                es_hidrico = bool(patron_hidrico.search(desc_limpia))

                registros_unicos[num] = {
                    "event_id": f"GAMC-{num.replace('/', '-')}",
                    "numero_oficial": num,
                    "fecha_hora": props.get("Fecha"),
                    "lat": round(lat, 6),
                    "lon": round(lon, 6),
                    "distrito": distrito,
                    "cuenca": cuenca,
                    "descripcion_limpia": desc_limpia,
                    "unidad_responsable": props.get("Unidad Responsable"),
                    "estado_verificacion": props.get("Estado"),
                    "es_hidrico": es_hidrico,
                    "fuente": "GAMC_WMS_API",
                    "fecha_ingesta": datetime.now(timezone.utc).isoformat()
                }

filas = list(registros_unicos.values())
if filas:
    archivo_salida = "gamc_emergencias_limpio.csv"
    with open(archivo_salida, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=filas[0].keys())
        writer.writeheader()
        writer.writerows(filas)

    total_hidricos = sum(1 for r in filas if r["es_hidrico"])
    print(f"Total incidentes únicos capturados: {len(filas)}")
    print(f"Incidentes hídricos/inundación detectados: {total_hidricos}")
    print(f"Archivo guardado: {archivo_salida}\n")
    print("Primeros 5 registros:")
    for r in filas[:5]:
        print(f" - {r['event_id']} | Fecha: {r['fecha_hora']} | Distrito: {r['distrito']} | Hídrico: {r['es_hidrico']}")
else:
    print("No se capturaron puntos en esta grilla; ajustaremos la resolución de búsqueda.")