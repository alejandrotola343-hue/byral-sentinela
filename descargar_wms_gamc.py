import os, json, urllib.request, urllib.parse, ssl, xml.etree.ElementTree as ET

OUT_JS = r"C:\Users\Lenovo\Desktop\BYRAL\sitio_final\js\datos_gamc.js"
BASE_WMS = "https://serviciosgamc.cochabamba.bo/api/gs/wms"

SERVICES = {
    "emergencias": "e105a6ed-74bb-41a5-8c85-9360711ddf69",
    "cuencas":     "fb368617-f2fd-43e8-867a-4456364efb52",
    "drenaje":     "d4cea6e3-fc7f-482a-94ad-bd377df78886",
    "distritos":   "7eb13092-bf0e-493b-aae6-03c43eedda2c"
}

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

def fetch_text(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Origin": "https://recursosgamc.cochabamba.bo",
        "Referer": "https://recursosgamc.cochabamba.bo/"
    })
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", errors="ignore")

def get_layer_name(sid):
    cap_url = f"{BASE_WMS}?service_id={sid}&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetCapabilities"
    try:
        xml_txt = fetch_text(cap_url, timeout=15)
        root = ET.fromstring(xml_txt)
        for elem in root.iter():
            if elem.tag.endswith("Layer"):
                name_el = next((c for c in elem if c.tag.endswith("Name") and c.text), None)
                if name_el is not None and ":" in name_el.text:
                    return name_el.text.strip()
        for elem in root.iter():
            if elem.tag.endswith("Name") and elem.text and elem.text.strip() not in ("WMS", "OGC:WMS"):
                return elem.text.strip()
    except Exception as e:
        print(f"  [Aviso GetCapabilities {sid}]: {e}")
    return None

def fetch_wfs_geojson(sid, layer_name):
    wfs_base = BASE_WMS.replace("/wms", "/wfs")
    candidates = [
        f"{BASE_WMS}?service_id={sid}&SERVICE=WFS&VERSION=1.0.0&REQUEST=GetFeature&TYPENAME={urllib.parse.quote(layer_name)}&OUTPUTFORMAT=application/json&SRSNAME=EPSG:4326",
        f"{BASE_WMS}?service_id={sid}&SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAME={urllib.parse.quote(layer_name)}&OUTPUTFORMAT=application/json&SRSNAME=EPSG:4326",
        f"{wfs_base}?service_id={sid}&SERVICE=WFS&VERSION=1.0.0&REQUEST=GetFeature&TYPENAME={urllib.parse.quote(layer_name)}&OUTPUTFORMAT=application/json&SRSNAME=EPSG:4326"
    ]
    for url in candidates:
        try:
            txt = fetch_text(url, timeout=25)
            if txt.strip().startswith("{"):
                data = json.loads(txt)
                feats = data.get("features") or []
                if feats:
                    return feats
        except Exception:
            pass
    return []

def clean_properties(props):
    # Conservar atributos tecnicos/operativos y omitir datos personales de denunciantes
    omit = {"denunciante", "celular", "telefono", "ci", "carnet"}
    return {
        k: str(v).replace("&NBSP;", " ").strip() if isinstance(v, str) else v
        for k, v in (props or {}).items()
        if k.lower() not in omit and v is not None and str(v).strip() != ""
    }

resultado = {"emergencias": [], "cuencas": [], "drenaje": [], "distritos": []}

for cat, sid in SERVICES.items():
    print(f"Consultando capa [{cat}] (service_id={sid})...")
    lname = get_layer_name(sid)
    print(f"  Nombre interno GeoServer: {lname}")
    if lname:
        feats = fetch_wfs_geojson(sid, lname)
        for ft in feats:
            if ft.get("geometry"):
                resultado[cat].append({
                    "type": "Feature",
                    "geometry": ft["geometry"],
                    "properties": clean_properties(ft.get("properties"))
                })
    print(f"  -> {len(resultado[cat])} elementos descargados")

if any(len(v) > 0 for v in resultado.values()):
    with open(OUT_JS, "w", encoding="utf-8") as f:
        f.write("window.BYRAL_HISTORICAL_DATA = " + json.dumps(resultado, ensure_ascii=False) + ";\n")
    print("Guardado correctamente en:", OUT_JS)
else:
    print("El servidor no devolvio GeoJSON por WFS directo; usar respaldo desde navegador.")
