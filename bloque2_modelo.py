import json
import csv
from datetime import datetime, timezone

ESCENARIO_EVENTO = {
    "escenario_id": "SIM-CBBA-D9-20250217",
    "modo_operacion": "SIMULACION_MVP",
    "zona_piloto": "Distrito 9 - La Maica (Microcuenca Río Rocha / Tamborada)",
    "fecha_evento": "2025-02-17",
    "fuentes": [
        "NASA GPM IMERG V07B (Precipitación acumulada 72h)",
        "NASA NISAR / Sentinel-1 SAR (Retrodispersión VV/VH)",
        "GAMC WMS (Cuencas, Drenaje e Incidentes Históricos)"
    ],
    "qa_gatekeeper": {
        "datos_recientes_ok": True,
        "geometria_confiable_ok": True,
        "fuente_validada_ok": True,
        "estado_trazabilidad": "PROCESADO_PARA_SIMULACION"
    }
}

def calcular_indice_susceptibilidad(delta_sar_db, lluvia_72h_mm, twi_normalizado):
    """
    Combina evidencia satelital SAR, lluvia acumulada IMERG y topografía local.
    - delta_sar_db: caída de retrodispersión SAR (ej. -6.0 dB indica anegamiento fuerte)
    - lluvia_72h_mm: lluvia acumulada en 72h (ej. 65 mm umbral crítico en valle)
    - twi_normalizado: índice topográfico de humedad y cercanía a drenaje [0.0 a 1.0]
    """
    score_sar = min(max(abs(delta_sar_db) / 7.0, 0.0), 1.0)
    score_lluvia = min(max(lluvia_72h_mm / 70.0, 0.0), 1.0)
    score_topo = min(max(twi_normalizado, 0.0), 1.0)

    indice = (0.40 * score_sar) + (0.35 * score_lluvia) + (0.25 * score_topo)
    indice = round(indice, 3)

    if indice >= 0.70:
        zona, nivel, accion = "ZONA_A", "IMPACTO_ALTO", "Evitar zonas bajas/canales y seguir rutas seguras."
    elif indice >= 0.40:
        zona, nivel, accion = "ZONA_B", "VIGILANCIA", "Mantener precaución y monitorear avisos oficiales."
    else:
        zona, nivel, accion = "ZONA_C", "FUERA_DE_IMPACTO", "Sin alarma crítica en tu sector."

    return {
        "indice_susceptibilidad": indice,
        "clasificacion": zona,
        "nivel_atencion": nivel,
        "accion_recomendada": accion,
        "desglose": {
            "sar_norm": round(score_sar, 2),
            "lluvia_norm": round(score_lluvia, 2),
            "topo_norm": round(score_topo, 2)
        }
    }

sectores_la_maica = [
    {
        "nombre": "Sector A - Llanura de inundación La Maica Sur (Canal Tamborada)",
        "delta_sar_db": -6.2,
        "lluvia_72h_mm": 64.5,
        "twi_norm": 0.90,
        "color": "#e63946",
        "coordenadas": [[
            [-66.2080, -17.4420],
            [-66.1920, -17.4420],
            [-66.1920, -17.4540],
            [-66.2080, -17.4540],
            [-66.2080, -17.4420]
        ]]
    },
    {
        "nombre": "Sector B - Perímetro de amortiguamiento y conectividad aguas abajo",
        "delta_sar_db": -3.1,
        "lluvia_72h_mm": 58.0,
        "twi_norm": 0.55,
        "color": "#f4a261",
        "coordenadas": [[
            [-66.2150, -17.4340],
            [-66.1850, -17.4340],
            [-66.1850, -17.4600],
            [-66.2150, -17.4600],
            [-66.2150, -17.4340]
        ]]
    },
    {
        "nombre": "Sector C - Zona urbana alta fuera de drenaje directo",
        "delta_sar_db": -0.8,
        "lluvia_72h_mm": 42.0,
        "twi_norm": 0.15,
        "color": "#2a9d8f",
        "coordenadas": [[
            [-66.1820, -17.4150],
            [-66.1650, -17.4150],
            [-66.1650, -17.4280],
            [-66.1820, -17.4280],
            [-66.1820, -17.4150]
        ]]
    }
]

features_geojson = []
print("=== RESULTADOS DEL MODELO DE SUSCEPTIBILIDAD (LA MAICA - D9) ===\n")

for sec in sectores_la_maica:
    resultado = calcular_indice_susceptibilidad(
        sec["delta_sar_db"], sec["lluvia_72h_mm"], sec["twi_norm"]
    )
    print(f"* {sec['nombre']}")
    print(f"  -> Índice IS: {resultado['indice_susceptibilidad']} | Estado: {resultado['clasificacion']} ({resultado['nivel_atencion']})")

    features_geojson.append({
        "type": "Feature",
        "properties": {
            "sector": sec["nombre"],
            "color": sec["color"],
            "escenario_id": ESCENARIO_EVENTO["escenario_id"],
            "modo": ESCENARIO_EVENTO["modo_operacion"],
            "generado_utc": datetime.now(timezone.utc).isoformat(),
            **resultado
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": sec["coordenadas"]
        }
    })

geojson_salida = {
    "type": "FeatureCollection",
    "metadata": ESCENARIO_EVENTO,
    "features": features_geojson
}

with open("poligonos_la_maica.geojson", "w", encoding="utf-8") as f:
    json.dump(geojson_salida, f, ensure_ascii=False, indent=2)

print("\nArchivo cartográfico generado: poligonos_la_maica.geojson")