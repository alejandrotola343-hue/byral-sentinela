import json
import csv
from datetime import datetime, timezone

with open("poligonos_la_maica.geojson", "r", encoding="utf-8") as f:
    geojson_data = json.load(f)

emergencias_reales = []
with open("gamc_emergencias_limpio.csv", "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        emergencias_reales.append(row)

def punto_en_poligono(lon, lat, anillo_coords):
    """Determina si un punto (lon, lat) está dentro de un polígono GeoJSON."""
    dentro = False
    n = len(anillo_coords)
    p1x, p1y = anillo_coords[0]
    for i in range(1, n + 1):
        p2x, p2y = anillo_coords[i % n]
        if lat > min(p1y, p2y):
            if lat <= max(p1y, p2y):
                if lon <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (lat - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or lon <= xinters:
                        dentro = not dentro
        p1x, p1y = p2x, p2y
    return dentro

PRIORIDAD_ZONA = {"ZONA_A": 3, "ZONA_B": 2, "ZONA_C": 1, "SIN_COBERTURA": 0}

def evaluar_usuario(usuario):
    qa = geojson_data["metadata"]["qa_gatekeeper"]
    if not all([qa["datos_recientes_ok"], qa["geometria_confiable_ok"], qa["fuente_validada_ok"]]):
        return {"estado": "BLOQUEADO_POR_QA", "mensaje": "Datos en verificación. Mantenga precaución."}

    mejor_match = None
    for feat in geojson_data["features"]:
        coords = feat["geometry"]["coordinates"][0]
        if punto_en_poligono(usuario["lon"], usuario["lat"], coords):
            props = feat["properties"]
            if (mejor_match is None or 
                PRIORIDAD_ZONA[props["clasificacion"]] > PRIORIDAD_ZONA[mejor_match["clasificacion"]]):
                mejor_match = props

    if not mejor_match:
        clasificacion = "ZONA_C"
        indice_is = 0.0
        sector = "Fuera del perímetro piloto de La Maica"
        accion = "Sin alarma activa en su ubicación actual."
    else:
        clasificacion = mejor_match["clasificacion"]
        indice_is = mejor_match["indice_susceptibilidad"]
        sector = mejor_match["sector"]
        accion = mejor_match["accion_recomendada"]

    canal = usuario["canal_preferido"]
    etiqueta_sim = "[SIMULACIÓN MVP]"

    if clasificacion == "ZONA_A":
        texto = f"{etiqueta_sim} ALERTA PRIORITARIA (Zona A - Impacto): Riesgo alto de anegamiento en {sector}. {accion}"
        voz = f"Atención. Simulación de alerta prioritaria en La Maica. {accion}"
        vibracion = {"patron_ms": [500, 200, 500, 200, 800], "intensidad": "ALTA"}
    elif clasificacion == "ZONA_B":
        texto = f"{etiqueta_sim} AVISO DE VIGILANCIA (Zona B): Precaución por cercanía a drenaje en {sector}. {accion}"
        voz = f"Aviso de vigilancia en su sector. {accion}"
        vibracion = {"patron_ms": [300, 300, 300], "intensidad": "MEDIA"}
    else:
        texto = f"{etiqueta_sim} ESTADO INFORMATIVO (Zona C): Sin impacto hídrico previsto en su sector."
        voz = "Estado informativo. Sin alerta crítica en su ubicación."
        vibracion = {"patron_ms": [150], "intensidad": "SUAVE"}

    entrega = {"texto_claro": texto}
    if canal == "voz":
        entrega["guion_audio_tts"] = voz
    elif canal == "vibracion":
        entrega["senial_haptica"] = vibracion

    return {
        "usuario_id": usuario["id"],
        "alias": usuario["alias"],
        "coordenadas": {"lat": usuario["lat"], "lon": usuario["lon"]},
        "zona_asignada": clasificacion,
        "indice_susceptibilidad": indice_is,
        "sector_detectado": sector,
        "canal_preferido": canal,
        "mensaje_accesible": entrega
    }

usuarios_piloto = [
    {"id": "USR-01", "alias": "Vecino La Maica Sur", "lat": -17.4480, "lon": -66.2000, "canal_preferido": "voz"},
    {"id": "USR-02", "alias": "Comerciante Av. Petrolera / D9", "lat": -17.4370, "lon": -66.1900, "canal_preferido": "vibracion"},
    {"id": "USR-03", "alias": "Estudiante Zona Central", "lat": -17.4200, "lon": -66.1720, "canal_preferido": "texto"}
]

resultados_usuarios = [evaluar_usuario(u) for u in usuarios_piloto]

eventos_d9 = [e for e in emergencias_reales if e["distrito"] == "D9"]
eventos_hidricos = [e for e in emergencias_reales if e["es_hidrico"] == "True"]

salida_completa = {
    "meta_sistema": {
        "proyecto": "BYRAL Sentinela",
        "modo": "SIMULACION_MVP",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "escenario_activo": geojson_data["metadata"]
    },
    "validacion_ground_truth_gamc": {
        "total_incidentes_ingestados": len(emergencias_reales),
        "incidentes_en_distrito_9": len(eventos_d9),
        "incidentes_hidricos_confirmados": len(eventos_hidricos),
        "nota_metodologica": "Registros anonimizados desde GAMC WMS usados como referencia histórica y control de falsas alarmas."
    },
    "alertas_ciudadanos": resultados_usuarios
}

with open("estado_alertas_mvp.json", "w", encoding="utf-8") as f:
    json.dump(salida_completa, f, ensure_ascii=False, indent=2)

print("=== MOTOR DE GEOFENCING Y ALERTAS ACCESIBLES (BLOQUE 3) ===\n")
for r in resultados_usuarios:
    print(f"* {r['alias']} ({r['canal_preferido'].upper()}) -> {r['zona_asignada']} (IS: {r['indice_susceptibilidad']})")
    print(f"  Mensaje: {r['mensaje_accesible']['texto_claro']}\n")

print(f"Validación GAMC vinculada: {len(emergencias_reales)} registros históricos ({len(eventos_d9)} en D9).")
print("Archivo generado para la interfaz web: estado_alertas_mvp.json")