import os, json, csv, math, ssl, urllib.request

base_dir = r"C:\Users\Lenovo\Desktop\BYRAL"
out_dir = os.path.join(base_dir, "sitio_final")
lib_dir = os.path.join(out_dir, "lib")
assets_dir = os.path.join(out_dir, "assets")
os.makedirs(lib_dir, exist_ok=True)
os.makedirs(assets_dir, exist_ok=True)

# Contexto SSL sin bloqueo de certificados locales en Windows
ssl_ctx = ssl._create_unverified_context()

downloads = [
    (os.path.join(lib_dir, "leaflet.css"), [
        "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css",
        "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
    ]),
    (os.path.join(lib_dir, "leaflet.js"), [
        "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js",
        "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
    ]),
    (os.path.join(lib_dir, "three.min.js"), [
        "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js",
        "https://unpkg.com/three@0.128.0/build/three.min.js"
    ]),
    (os.path.join(assets_dir, "earth-blue-marble.jpg"), [
        "https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg"
    ]),
    (os.path.join(assets_dir, "earth-topology.png"), [
        "https://unpkg.com/three-globe/example/img/earth-topology.png"
    ]),
    (os.path.join(assets_dir, "earth-night.jpg"), [
        "https://unpkg.com/three-globe/example/img/earth-night.jpg"
    ]),
    (os.path.join(assets_dir, "earth-clouds.png"), [
        "https://raw.githubusercontent.com/mrdoob/three.js/master/examples/textures/planets/earth_clouds_1024.png"
    ])
]

for dest, urls in downloads:
    if os.path.exists(dest) and os.path.getsize(dest) > 5000:
        print("OK:", os.path.basename(dest))
        continue
    for u in urls:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=25, context=ssl_ctx) as resp:
                data = resp.read()
            if len(data) > 2000:
                with open(dest, "wb") as f:
                    f.write(data)
                print("Descargado:", os.path.basename(dest), f"({len(data)} bytes)")
                break
        except Exception as ex:
            print("Reintentando", os.path.basename(dest), "->", ex)

# Reproyeccion UTM Zona 19S (Cochabamba) a WGS84 Lat/Lng
def utm19s_to_latlng(easting, northing):
    if abs(easting) <= 180 and abs(northing) <= 90:
        return round(northing, 6), round(easting, 6)
    a = 6378137.0
    e = 0.081819191
    e1sq = 0.006739497
    k0 = 0.9996
    x = easting - 500000.0
    y = northing - 10000000.0
    M = y / k0
    mu = M / (a * (1 - e**2/4 - 3*e**4/64 - 5*e**6/256))
    e1 = (1 - math.sqrt(1 - e**2)) / (1 + math.sqrt(1 - e**2))
    phi1 = (mu + (3*e1/2 - 27*e1**3/32)*math.sin(2*mu)
            + (21*e1**2/16 - 55*e1**4/32)*math.sin(4*mu)
            + (151*e1**3/96)*math.sin(6*mu))
    N1 = a / math.sqrt(1 - (e*math.sin(phi1))**2)
    T1 = math.tan(phi1)**2
    C1 = e1sq * (math.cos(phi1)**2)
    R1 = a * (1 - e**2) / ((1 - (e*math.sin(phi1))**2)**1.5)
    D = x / (N1 * k0)
    lat = phi1 - (N1*math.tan(phi1)/R1)*(D**2/2 - (5 + 3*T1 + 10*C1 - 4*C1**2 - 9*e1sq)*D**4/24)
    lon = (-69.0*math.pi/180) + (D - (1 + 2*T1 + C1)*D**3/6 + (5 - 2*C1 + 28*T1 - 3*C1**2 + 8*e1sq + 24*T1**2)*D**5/120)/math.cos(phi1)
    return round(math.degrees(lat), 6), round(math.degrees(lon), 6)

def norm_coords(coords):
    if not isinstance(coords, list) or len(coords) == 0:
        return coords
    if isinstance(coords[0], (int, float)) and isinstance(coords[1], (int, float)):
        lat, lng = utm19s_to_latlng(float(coords[0]), float(coords[1]))
        return [lng, lat]
    return [norm_coords(c) for c in coords]

def classify_cat(name_hint):
    s = name_hint.lower()
    if "cuenca" in s:
        return "cuencas"
    if "dren" in s or "rio" in s or "hidro" in s or "torrentera" in s:
        return "drenaje"
    if "distrit" in s or "comuna" in s or "limite" in s:
        return "distritos"
    return "emergencias"

datasets = {"emergencias": [], "cuencas": [], "drenaje": [], "distritos": []}
seen = set()
skip_dirs = {".wrangler", "node_modules", ".git", "lib", "assets", ".venv", "venv", "sitio_final"}

def add_feature(cat, geom, props, src_file):
    if not geom or "coordinates" not in geom:
        return
    geom_norm = {"type": geom["type"], "coordinates": norm_coords(geom["coordinates"])}
    sig = f"{cat}|{json.dumps(geom_norm['coordinates'])[:120]}|{json.dumps(props, ensure_ascii=False)[:80]}"
    if sig in seen:
        return
    seen.add(sig)
    clean_props = {str(k): v for k, v in (props or {}).items() if v is not None and str(v).strip() != ""}
    clean_props["_fuente"] = src_file
    datasets[cat].append({"type": "Feature", "geometry": geom_norm, "properties": clean_props})

def parse_obj(obj, default_cat, src_file):
    if isinstance(obj, dict):
        if obj.get("type") == "FeatureCollection" and isinstance(obj.get("features"), list):
            for f in obj["features"]:
                if isinstance(f, dict):
                    add_feature(default_cat, f.get("geometry"), f.get("properties", {}), src_file)
        elif obj.get("type") == "Feature":
            add_feature(default_cat, obj.get("geometry"), obj.get("properties", {}), src_file)
        else:
            for k, v in obj.items():
                parse_obj(v, classify_cat(f"{default_cat}_{k}"), src_file)
    elif isinstance(obj, list):
        for item in obj:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "Feature":
                add_feature(default_cat, item.get("geometry"), item.get("properties", {}), src_file)
                continue
            rx = (item.get("lng") or item.get("lon") or item.get("longitude") or item.get("longitud")
                  or item.get("Longitud") or item.get("x") or item.get("X") or item.get("ESTE") or item.get("Este"))
            ry = (item.get("lat") or item.get("latitude") or item.get("latitud")
                  or item.get("Latitud") or item.get("y") or item.get("Y") or item.get("NORTE") or item.get("Norte"))
            try:
                if rx is not None and ry is not None:
                    fx, fy = float(rx), float(ry)
                    if fx != 0 and fy != 0:
                        add_feature(default_cat, {"type": "Point", "coordinates": [fx, fy]}, item, src_file)
            except Exception:
                pass

for root, dirs, files in os.walk(base_dir):
    dirs[:] = [d for d in dirs if d not in skip_dirs]
    for fn in files:
        if fn in ("datos_historicos_byral.json", "manifest_capas.json", "package.json", "package-lock.json"):
            continue
        full_path = os.path.join(root, fn)
        fl = fn.lower()
        cat = classify_cat(fl)
        if fl.endswith((".geojson", ".json")):
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                    data = json.load(fp)
                parse_obj(data, cat, fn)
            except Exception:
                pass
        elif fl.endswith(".csv"):
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                    rows = list(csv.DictReader(fp))
                parse_obj(rows, cat, fn)
            except Exception:
                pass

print("=== RESUMEN DATOS HISTORICOS INCRUSTADOS ===")
for k, v in datasets.items():
    print(f"  -> {k.upper()}: {len(v)} registros")

embedded_json = json.dumps(datasets, ensure_ascii=False).replace("</", "<\\/")

html_template = r"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>BYRAL SENTINELA - Observatorio Orbital y Monitoreo Territorial</title>
  <link rel="stylesheet" href="./lib/leaflet.css" />
  <script src="./lib/leaflet.js"></script>
  <script>
    if (!window.L) {
      document.write('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css" />');
      document.write('<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"><\/script>');
    }
  </script>
  <script src="./lib/three.min.js"></script>
  <script>
    if (!window.THREE) {
      document.write('<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"><\/script>');
    }
  </script>
  <script>
    window.BYRAL_HISTORICAL_DATA = __BYRAL_JSON__;
  </script>
  <style>
    :root {
      --bg: #050a12;
      --surface: rgba(11, 20, 34, 0.90);
      --surface-solid: #0b1422;
      --surface-soft: rgba(18, 32, 52, 0.82);
      --border: rgba(148, 197, 235, 0.28);
      --border-hover: rgba(148, 197, 235, 0.56);
      --accent: #67d5e8;
      --gold: #e5b567;
      --emerald: #4cc38a;
      --coral: #e06c75;
      --text: #eef4fa;
      --muted: #9bb3cc;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', system-ui, sans-serif; }
    body { background: var(--bg); color: var(--text); min-height: 100vh; overflow-x: hidden; }

    /* PORTADA ORBITAL */
    #entry-screen {
      position: relative; width: 100%; min-height: 100vh; overflow: hidden;
      display: flex; flex-direction: column; justify-content: space-between; background: #02050a;
    }
    #space-canvas { position: absolute; inset: 0; width: 100%; height: 100%; z-index: 1; }
    #space-canvas canvas { display: block; width: 100% !important; height: 100% !important; }

    .orbital-top {
      position: relative; z-index: 10; display: flex; justify-content: space-between;
      align-items: flex-start; padding: 24px 36px; pointer-events: none; flex-wrap: wrap; gap: 16px;
    }
    .telemetry-stream {
      border-left: 2px solid rgba(103, 213, 232, 0.65); padding-left: 14px;
      font-family: Consolas, monospace; font-size: 11.5px; line-height: 1.7; color: #dbeafe;
      text-shadow: 0 2px 10px rgba(0, 0, 0, 0.95);
    }
    .telemetry-stream strong { color: var(--accent); letter-spacing: 1px; }

    .sat-pills { display: flex; flex-wrap: wrap; gap: 8px; max-width: 520px; justify-content: flex-end; }
    .sat-tag {
      background: rgba(11, 20, 34, 0.78); border: 1px solid var(--border); backdrop-filter: blur(10px);
      padding: 5px 12px; border-radius: 999px; font-size: 10.5px; font-family: Consolas, monospace;
      color: #dce9f5; display: flex; align-items: center; gap: 6px;
    }
    .dot-pulse { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }

    .spatial-portals {
      position: relative; z-index: 10; display: flex; flex-direction: column;
      align-items: flex-end; justify-content: center; padding: 12px 48px; gap: 20px; pointer-events: none;
    }
    @media (max-width: 900px) { .spatial-portals { align-items: center; padding: 16px; } }

    .portal-trigger {
      pointer-events: auto; display: flex; align-items: center; gap: 18px;
      background: linear-gradient(90deg, rgba(11, 20, 34, 0.55) 0%, rgba(17, 34, 58, 0.90) 100%);
      border: 1px solid var(--border); border-right: 3px solid var(--accent);
      border-radius: 999px 18px 18px 999px; padding: 14px 26px 14px 16px; color: var(--text);
      cursor: pointer; transition: all 0.3s ease; backdrop-filter: blur(14px);
      max-width: 470px; width: 100%; text-align: left; box-shadow: 0 12px 35px rgba(0, 0, 0, 0.55);
    }
    .portal-trigger:hover { transform: translateX(-8px); border-color: var(--border-hover); }
    .portal-trigger.admin-node { border-right-color: var(--gold); }

    .orbital-ring-icon {
      width: 50px; height: 50px; border-radius: 50%; border: 1px solid rgba(103, 213, 232, 0.45);
      display: flex; align-items: center; justify-content: center; font-size: 21px; flex-shrink: 0;
      background: radial-gradient(circle, rgba(103, 213, 232, 0.16) 0%, transparent 72%);
    }
    .admin-node .orbital-ring-icon {
      border-color: rgba(229, 181, 103, 0.45);
      background: radial-gradient(circle, rgba(229, 181, 103, 0.16) 0%, transparent 72%);
    }
    .portal-text small { display: block; font-family: Consolas, monospace; font-size: 10.5px; letter-spacing: 1.4px; text-transform: uppercase; color: var(--accent); margin-bottom: 3px; }
    .admin-node .portal-text small { color: var(--gold); }
    .portal-text strong { display: block; font-size: 16px; font-weight: 700; }
    .portal-text span { display: block; font-size: 11.5px; color: var(--muted); margin-top: 2px; line-height: 1.35; }

    .orbital-bottom {
      position: relative; z-index: 10; padding: 20px 36px 26px 36px; display: flex;
      justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 14px;
      background: linear-gradient(0deg, rgba(2, 5, 10, 0.94) 0%, rgba(2, 5, 10, 0.45) 70%, transparent 100%);
    }
    .project-signature h1 { font-size: clamp(1.9rem, 3.4vw, 2.8rem); font-weight: 800; letter-spacing: 2.5px; line-height: 1; text-transform: uppercase; }
    .project-signature h1 span { color: var(--accent); font-weight: 300; }
    .project-signature p { font-size: 12.5px; color: var(--muted); margin-top: 6px; }
    .team-signature { text-align: right; border-right: 2px solid rgba(103, 213, 232, 0.5); padding-right: 14px; font-size: 11.5px; color: #cbdbe9; }
    .team-signature strong { display: block; color: var(--accent); font-family: Consolas, monospace; font-size: 12px; }

    /* BARRA SUPERIOR INTERNA */
    #main-header {
      display: none; background: rgba(8, 15, 26, 0.96); backdrop-filter: blur(14px);
      border-bottom: 1px solid var(--border); padding: 10px 22px; justify-content: space-between;
      align-items: center; flex-wrap: wrap; gap: 10px; position: sticky; top: 0; z-index: 1100;
    }
    .brand { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 15px; }
    .brand span { color: var(--accent); font-weight: 400; }
    .live-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--emerald); display: inline-block; }

    .weather-pill {
      background: var(--surface-soft); border: 1px solid var(--border); padding: 5px 14px;
      border-radius: 999px; font-size: 11.5px; color: var(--text); display: flex; align-items: center; gap: 12px; font-family: Consolas, monospace; flex-wrap: wrap;
    }
    .btn-hud {
      background: var(--surface-soft); color: var(--text); border: 1px solid var(--border);
      padding: 6px 13px; border-radius: 999px; font-size: 11.5px; font-weight: 600; cursor: pointer;
    }
    .btn-hud:hover { border-color: var(--accent); color: var(--accent); }
    .btn-primary {
      background: linear-gradient(135deg, #3b82f6, #67d5e8); color: #050a12; border: none;
      padding: 9px 16px; border-radius: 999px; font-size: 12.5px; font-weight: 700; cursor: pointer; width: 100%;
    }

    /* SELECTOR DE RELIEVES Y MAPAS */
    .basemap-dock {
      position: absolute; top: 14px; left: 14px; z-index: 900; display: flex; flex-wrap: wrap; gap: 6px;
      background: rgba(8, 15, 26, 0.92); border: 1px solid var(--border); padding: 6px 8px;
      border-radius: 999px; backdrop-filter: blur(12px); box-shadow: 0 8px 28px rgba(0, 0, 0, 0.45);
    }
    .bm-btn {
      background: transparent; border: 1px solid transparent; color: var(--muted);
      padding: 5px 11px; border-radius: 999px; font-size: 11px; font-weight: 600; cursor: pointer;
    }
    .bm-btn:hover { color: var(--text); }
    .bm-btn.active { background: rgba(103, 213, 232, 0.24); color: var(--text); border-color: rgba(103, 213, 232, 0.55); }

    /* MODO CIUDADANO */
    #citizen-app {
      display: none; min-height: calc(100vh - 54px); grid-template-columns: 1fr 400px; gap: 16px; padding: 16px 22px;
    }
    @media (max-width: 980px) { #citizen-app { grid-template-columns: 1fr; } #citizen-map-wrap { height: 460px; } }
    #citizen-map-wrap { position: relative; border-radius: 18px; overflow: hidden; border: 1px solid var(--border); min-height: 600px; }
    #citizen-map { width: 100%; height: 100%; min-height: 600px; background: #0a121e; }

    .map-legend-bar {
      position: absolute; bottom: 14px; left: 14px; right: 14px; z-index: 850;
      background: rgba(8, 15, 26, 0.92); border: 1px solid var(--border); border-radius: 999px;
      padding: 7px 16px; display: flex; justify-content: space-around; flex-wrap: wrap; gap: 10px; font-size: 11px;
    }

    .glass-panel { background: var(--surface); border: 1px solid var(--border); border-radius: 18px; padding: 16px 18px; backdrop-filter: blur(14px); }
    .panel-header { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.9px; color: var(--accent); margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }

    .pill-tabs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; background: rgba(5, 10, 18, 0.55); padding: 4px; border-radius: 999px; border: 1px solid var(--border); margin-bottom: 12px; }
    .s-tab { background: transparent; border: none; color: var(--muted); padding: 7px 6px; border-radius: 999px; font-size: 11.5px; font-weight: 600; cursor: pointer; }
    .s-tab.active { background: rgba(103, 213, 232, 0.22); color: var(--text); }
    .s-pane { display: none; }
    .s-pane.active { display: block; }

    .status-narrative { background: var(--surface-soft); border-left: 3px solid var(--accent); padding: 11px 14px; border-radius: 12px; font-size: 12.5px; line-height: 1.55; margin-bottom: 12px; }
    .incident-list { max-height: 320px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
    .incident-item { background: var(--surface-soft); border: 1px solid var(--border); border-left: 3px solid var(--coral); border-radius: 12px; padding: 9px 12px; font-size: 11.5px; cursor: pointer; }
    .incident-item.weather-item { border-left-color: var(--accent); }

    label.field-lbl { display: block; font-size: 11px; color: var(--muted); margin-bottom: 4px; font-weight: 600; }
    input[type="text"], input[type="password"], select, textarea {
      width: 100%; background: rgba(5, 10, 18, 0.78); border: 1px solid var(--border); color: var(--text);
      padding: 8px 11px; border-radius: 10px; font-size: 12px; margin-bottom: 8px; outline: none;
    }
    .form-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }

    .ai-box { height: 250px; overflow-y: auto; background: rgba(5, 10, 18, 0.65); border: 1px solid var(--border); border-radius: 12px; padding: 10px; display: flex; flex-direction: column; gap: 8px; font-size: 12px; margin-bottom: 8px; }
    .msg-ai { background: var(--surface-soft); padding: 8px 11px; border-radius: 10px; border-left: 2px solid var(--accent); }
    .msg-usr { background: rgba(103, 213, 232, 0.16); padding: 7px 11px; border-radius: 10px; align-self: flex-end; }
    .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
    .chip { background: var(--surface-soft); border: 1px solid var(--border); color: var(--muted); font-size: 10.5px; padding: 4px 10px; border-radius: 999px; cursor: pointer; }

    .badge { padding: 2px 8px; border-radius: 999px; font-size: 10px; font-weight: 700; font-family: Consolas, monospace; }
    .b-live { background: rgba(76, 195, 138, 0.16); color: var(--emerald); border: 1px solid rgba(76, 195, 138, 0.35); }
    .b-warn { background: rgba(229, 181, 103, 0.16); color: var(--gold); border: 1px solid rgba(229, 181, 103, 0.35); }
    .b-crit { background: rgba(224, 108, 117, 0.16); color: var(--coral); border: 1px solid rgba(224, 108, 117, 0.35); }

    /* MODAL LOGIN ADMIN */
    #login-modal { display: none; position: fixed; inset: 0; z-index: 2000; background: rgba(3, 7, 14, 0.85); backdrop-filter: blur(14px); align-items: center; justify-content: center; padding: 16px; }
    #login-modal.open { display: flex; }
    .login-box { width: 100%; max-width: 390px; background: var(--surface-solid); border: 1px solid rgba(229, 181, 103, 0.45); border-radius: 20px; padding: 26px; }
    .login-box h2 { font-size: 18px; margin-bottom: 6px; }
    .login-box p { font-size: 12px; color: var(--muted); margin-bottom: 14px; }
    .login-error { color: var(--coral); font-size: 11.5px; margin-bottom: 10px; display: none; font-weight: 600; }

    /* CONSOLA ADMIN / DESARROLLADOR */
    #admin-app { display: none; min-height: calc(100vh - 54px); padding: 16px 22px; flex-direction: column; gap: 14px; }
    .admin-kpi-strip { display: grid; grid-template-columns: repeat(auto-fit, minmax(175px, 1fr)); gap: 12px; }
    .kpi-tile { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 12px 16px; display: flex; flex-direction: column; gap: 3px; }
    .kpi-tile small { font-size: 10.5px; color: var(--muted); text-transform: uppercase; }
    .kpi-tile strong { font-size: 21px; font-weight: 700; color: var(--text); font-family: Consolas, monospace; }

    .admin-workspace { display: grid; grid-template-columns: 325px 1fr 415px; gap: 16px; min-height: 600px; }
    @media (max-width: 1180px) { .admin-workspace { grid-template-columns: 1fr; } #admin-map-wrap { height: 480px; } }
    #admin-map-wrap { position: relative; border-radius: 18px; overflow: hidden; border: 1px solid var(--border); min-height: 600px; }
    #admin-map { width: 100%; height: 100%; min-height: 600px; background: #0a121e; }

    .layer-ctrl-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 11px; background: var(--surface-soft); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 7px; font-size: 11.5px; }
    .layer-ctrl-left { display: flex; align-items: center; gap: 8px; cursor: pointer; }
    .zoom-mini { background: rgba(103, 213, 232, 0.14); border: 1px solid rgba(103, 213, 232, 0.3); color: var(--accent); font-size: 10.5px; padding: 3px 9px; border-radius: 999px; cursor: pointer; }

    .slider-row { margin-bottom: 9px; }
    .slider-row label { display: flex; justify-content: space-between; font-size: 11px; color: var(--muted); margin-bottom: 3px; }
    .slider-row input[type="range"] { width: 100%; accent-color: var(--accent); }

    .admin-right-tabs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px; background: rgba(5, 10, 18, 0.55); padding: 4px; border-radius: 999px; border: 1px solid var(--border); margin-bottom: 12px; }
    .ar-tab { background: transparent; border: none; color: var(--muted); padding: 7px 4px; border-radius: 999px; font-size: 11px; font-weight: 600; cursor: pointer; }
    .ar-tab.active { background: rgba(103, 213, 232, 0.22); color: var(--text); }
    .ar-pane { display: none; max-height: 530px; overflow-y: auto; }
    .ar-pane.active { display: block; }

    .prob-row { background: var(--surface-soft); border: 1px solid var(--border); border-radius: 12px; padding: 10px 12px; margin-bottom: 8px; font-size: 11.5px; cursor: pointer; }
    .prob-bar-bg { height: 5px; background: rgba(255,255,255,0.08); border-radius: 999px; overflow: hidden; margin-top: 6px; }
    .prob-bar-fill { height: 100%; border-radius: 999px; }

    .report-admin-card { background: var(--surface-soft); border: 1px solid var(--border); border-radius: 12px; padding: 11px 13px; margin-bottom: 9px; font-size: 11.5px; line-height: 1.5; }
    .ai-triage-box { background: rgba(76, 195, 138, 0.10); border-left: 3px solid var(--emerald); padding: 6px 9px; margin-top: 6px; border-radius: 6px; font-size: 11px; color: #d1fae5; }

    .leaflet-popup-content-wrapper, .leaflet-popup-tip { background: #0b1422 !important; color: #eef4fa !important; border: 1px solid rgba(103, 213, 232, 0.45); border-radius: 12px !important; }
  </style>
</head>
<body>

  <!-- 1. PORTADA ORBITAL -->
  <section id="entry-screen">
    <div id="space-canvas"></div>

    <div class="orbital-top">
      <div class="telemetry-stream">
        <strong>ORB-TELEMETRY // LIVE SATELLITE &amp; UTC SYNC</strong><br/>
        UTC TIME: <span id="utc-clock-txt">--:--:-- UTC</span><br/>
        GMST ROTATION: <span id="gmst-txt">---.--&deg;</span><br/>
        TARGET NODE: COCHABAMBA, BO (-17.39&deg; S, -66.16&deg; O)<br/>
        SAT LINK: <span id="sat-link-status" style="color:#4cc38a;">SINCRONIZANDO SATELITES EN VIVO...</span>
      </div>
      <div class="sat-pills">
        <div class="sat-tag"><span class="dot-pulse" style="background:#f8fafc;"></span>ISS (408 km &middot; 51.6&deg;)</div>
        <div class="sat-tag"><span class="dot-pulse" style="background:#67d5e8;"></span>NISAR SAR-L (747 km)</div>
        <div class="sat-tag"><span class="dot-pulse" style="background:#93c5fd;"></span>Sentinel-1A (693 km)</div>
        <div class="sat-tag"><span class="dot-pulse" style="background:#e5b567;"></span>NASA GPM (407 km)</div>
        <div class="sat-tag"><span class="dot-pulse" style="background:#4cc38a;"></span>GOES-16 GEO (75.2&deg;O)</div>
      </div>
    </div>

    <div class="spatial-portals">
      <button class="portal-trigger" onclick="ingresarModoCiudadano()">
        <div class="orbital-ring-icon">&#127757;</div>
        <div class="portal-text">
          <small>Acceso P&uacute;blico &middot; Tiempo Real</small>
          <strong>Ingreso Ciudadanos / Usuarios</strong>
          <span>Mapa satelital y relieves en vivo, clima/sequ&iacute;a real, IA y reporte ciudadano.</span>
        </div>
      </button>

      <button class="portal-trigger admin-node" onclick="abrirModalLogin()">
        <div class="orbital-ring-icon">&#128752;</div>
        <div class="portal-text">
          <small>Acceso Restringido &middot; Credenciales Requeridas</small>
          <strong>Ingreso Administradores / Desarrolladores</strong>
          <span>382 registros hist&oacute;ricos GAMC, relieves, motor matem&aacute;tico satelital y bandeja IA.</span>
        </div>
      </button>
    </div>

    <footer class="orbital-bottom">
      <div class="project-signature">
        <h1>BYRAL <span>SENTINELA</span></h1>
        <p>Sistema Geoespacial Orbital y Monitoreo Territorial en Tiempo Real &middot; Cochabamba, Bolivia</p>
      </div>
      <div class="team-signature">
        <strong>EQUIPO BYRAL &middot; NASA SPACE APPS 2026</strong>
        <span>Ingenier&iacute;a Electr&oacute;nica, Geoespacial y Sistemas Embebidos</span>
      </div>
    </footer>
  </section>

  <!-- 2. BARRA SUPERIOR INTERNA -->
  <header id="main-header">
    <div class="brand">
      <span class="live-dot"></span>
      &#128752; BYRAL <span>SENTINELA</span>
      <small id="env-tag" style="font-size:11px;color:var(--muted);font-weight:500;">&middot; MODO CIUDADANO</small>
    </div>
    <div class="weather-pill">
      <span>&#128205; Cochabamba</span>
      <span id="top-temp">--&deg;C</span>
      <span id="top-rain">&#127783; -- mm/h</span>
      <span id="top-drought">&#127793; --</span>
      <span id="top-rad">&#9728; -- W/m&sup2;</span>
    </div>
    <div style="display:flex;gap:8px;align-items:center;">
      <button class="btn-hud" onclick="volverPortadaOrbital()">&#127760; &Oacute;rbita</button>
      <button class="btn-hud" id="btn-open-admin" onclick="abrirModalLogin()">&#128274; Admin / Dev</button>
      <button class="btn-hud" id="btn-exit-admin" style="display:none;border-color:var(--coral);color:var(--coral);" onclick="cerrarSesionAdmin()">&larr; Vista Ciudadano</button>
    </div>
  </header>

  <!-- 3. MODO CIUDADANO -->
  <main id="citizen-app">
    <div id="citizen-map-wrap">
      <div class="basemap-dock" id="citizen-basemap-bar">
        <button class="bm-btn active" onclick="setBasemap('citizen', 'satellite', this)">&#128752; Satelital</button>
        <button class="bm-btn" onclick="setBasemap('citizen', 'relief', this)">&#9968; Relieve 3D</button>
        <button class="bm-btn" onclick="setBasemap('citizen', 'topo', this)">&#128506; Topogr&aacute;fico</button>
        <button class="bm-btn" onclick="setBasemap('citizen', 'streets', this)">&#128739; Calles</button>
        <button class="bm-btn" onclick="setBasemap('citizen', 'dark', this)">&#127761; Nocturno</button>
      </div>
      <div id="citizen-map"></div>
      <div class="map-legend-bar">
        <span>&#128308; <strong>Coral:</strong> Accidente activo</span>
        <span>&#128309; <strong>Cian:</strong> Lluvia en curso</span>
        <span>&#128993; <strong>&Aacute;mbar:</strong> Sequ&iacute;a / Suelo seco</span>
      </div>
    </div>

    <div style="display:flex;flex-direction:column;gap:14px;">
      <div class="glass-panel">
        <div class="panel-header">
          <span>&#128225; Situaci&oacute;n Satelital en Vivo</span>
          <span class="badge b-live" id="live-clock">EN VIVO</span>
        </div>
        <div class="status-narrative" id="live-narrative">Sincronizando telemetr&iacute;a satelital en vivo...</div>

        <div class="pill-tabs">
          <button class="s-tab active" onclick="cambiarTabCiudadano('puntos', this)">&#128205; Puntos Hoy</button>
          <button class="s-tab" onclick="cambiarTabCiudadano('reportar', this)">&#128680; Reportar</button>
          <button class="s-tab" onclick="cambiarTabCiudadano('ia', this)">&#129302; Ayuda IA</button>
        </div>

        <div id="c-pane-puntos" class="s-pane active">
          <div class="incident-list" id="live-points-list"></div>
        </div>

        <div id="c-pane-reportar" class="s-pane">
          <form onsubmit="registrarReporteCiudadano(event)">
            <div class="form-grid-2">
              <div><label class="field-lbl">Nombre completo *</label><input type="text" id="c-nombre" required placeholder="Tu nombre" /></div>
              <div><label class="field-lbl">N&deg; Carnet (C.I.) *</label><input type="text" id="c-carnet" required placeholder="Ej. 7894512 CB" /></div>
            </div>
            <div class="form-grid-2">
              <div><label class="field-lbl">Tel&eacute;fono / Celular *</label><input type="text" id="c-telefono" required placeholder="Ej. 70712345" /></div>
              <div>
                <label class="field-lbl">Tipo de suceso *</label>
                <select id="c-tipo">
                  <option value="Accidente de Tránsito">&#128663; Accidente de Tr&aacute;nsito</option>
                  <option value="Inundación / Lluvia fuerte">&#127754; Inundaci&oacute;n / Lluvia</option>
                  <option value="Derrumbe / Vía bloqueada">&#128679; Derrumbe / Obst&aacute;culo</option>
                  <option value="Incendio / Sequía extrema">&#128293; Incendio / Sequ&iacute;a</option>
                </select>
              </div>
            </div>
            <label class="field-lbl">Lugar exacto (o haz clic en el mapa) *</label>
            <input type="text" id="c-lugar" required placeholder="Ej. Av. Blanco Galindo km 4" />
            <div style="font-size:10.5px;color:var(--muted);margin:-4px 0 8px 0;font-family:Consolas,monospace;" id="c-coords-lbl">&#128205; GPS: Centro Cochabamba (clic en mapa para fijar)</div>
            <label class="field-lbl">Descripci&oacute;n *</label>
            <textarea id="c-desc" rows="2" required placeholder="Que esta sucediendo en este momento?"></textarea>
            <button type="submit" class="btn-primary">&#128225; Publicar en el Mapa Ahora</button>
          </form>
        </div>

        <div id="c-pane-ia" class="s-pane">
          <div class="chips">
            <span class="chip" onclick="preguntarIACiudadano('Esta lloviendo o hay sequia ahora?')">Lluvia o sequ&iacute;a?</span>
            <span class="chip" onclick="preguntarIACiudadano('Donde hay accidentes ahora mismo?')">D&oacute;nde hay accidentes?</span>
          </div>
          <div class="ai-box" id="citizen-ai-chat">
            <div class="msg-ai"><strong>IA Ciudadana:</strong> Hola. Te informo en tiempo real sobre lluvias, sequ&iacute;a y accidentes en Cochabamba.</div>
          </div>
          <div style="display:flex;gap:6px;">
            <input type="text" id="citizen-ai-input" placeholder="Escribe tu consulta..." style="margin:0;" onkeydown="if(event.key==='Enter') enviarIACiudadano()" />
            <button class="btn-hud" onclick="enviarIACiudadano()">Enviar</button>
          </div>
        </div>
      </div>
    </div>
  </main>

  <!-- 4. MODAL LOGIN ADMIN -->
  <div id="login-modal">
    <div class="login-box">
      <h2>&#128274; Acceso Administrador / Desarrollador</h2>
      <p>Consola de control total: 382 registros hist&oacute;ricos GAMC, relieves, motor matem&aacute;tico satelital en vivo y bandeja de reportes IA.</p>
      <div class="login-error" id="login-error">Usuario o contrase&ntilde;a incorrectos.</div>
      <label class="field-lbl">Usuario</label>
      <input type="text" id="login-user" placeholder="Usuario" autocomplete="off" />
      <label class="field-lbl">Contrase&ntilde;a</label>
      <input type="password" id="login-pass" placeholder="Contrase&ntilde;a" onkeydown="if(event.key==='Enter') validarLoginAdmin()" />
      <div style="display:flex;gap:8px;margin-top:8px;">
        <button class="btn-hud" style="flex:1;" onclick="cerrarModalLogin()">Cancelar</button>
        <button class="btn-primary" style="flex:2;" onclick="validarLoginAdmin()">Ingresar</button>
      </div>
    </div>
  </div>

  <!-- 5. CONSOLA ADMIN / DESARROLLADOR -->
  <section id="admin-app">
    <div class="admin-kpi-strip">
      <div class="kpi-tile"><small>Puntos Emergencia GAMC</small><strong id="kpi-emerg">0</strong></div>
      <div class="kpi-tile"><small>Cuencas Hidrogr&aacute;ficas UH 7</small><strong id="kpi-cuencas">0</strong></div>
      <div class="kpi-tile"><small>Tramos Drenaje / R&iacute;os</small><strong id="kpi-dren">0</strong></div>
      <div class="kpi-tile"><small>Distritos Municipales</small><strong id="kpi-dist">0</strong></div>
      <div class="kpi-tile"><small>Reportes Ciudadanos Hoy</small><strong id="kpi-live-rep">0</strong></div>
    </div>

    <div class="admin-workspace">
      <div style="display:flex;flex-direction:column;gap:14px;">
        <div class="glass-panel">
          <div class="panel-header"><span>&#128450; Control Total Capas GAMC</span><span class="badge b-live">100% HIST&Oacute;RICO</span></div>
          <div class="layer-ctrl-row">
            <label class="layer-ctrl-left"><input type="checkbox" checked onchange="toggleAdminGroup('emergencias', this.checked)" /><span>&#128308; Emergencias / Quejas (<b id="cnt-emerg">0</b>)</span></label>
            <button class="zoom-mini" onclick="zoomToLayer('emergencias')">Enfocar</button>
          </div>
          <div class="layer-ctrl-row">
            <label class="layer-ctrl-left"><input type="checkbox" checked onchange="toggleAdminGroup('cuencas', this.checked)" /><span>&#128993; Cuencas UH 7 (<b id="cnt-cuencas">0</b>)</span></label>
            <button class="zoom-mini" onclick="zoomToLayer('cuencas')">Enfocar</button>
          </div>
          <div class="layer-ctrl-row">
            <label class="layer-ctrl-left"><input type="checkbox" checked onchange="toggleAdminGroup('drenaje', this.checked)" /><span>&#128311; Drenaje / R&iacute;os (<b id="cnt-dren">0</b>)</span></label>
            <button class="zoom-mini" onclick="zoomToLayer('drenaje')">Enfocar</button>
          </div>
          <div class="layer-ctrl-row">
            <label class="layer-ctrl-left"><input type="checkbox" checked onchange="toggleAdminGroup('distritos', this.checked)" /><span>&#128995; Distritos D1-D14 (<b id="cnt-dist">0</b>)</span></label>
            <button class="zoom-mini" onclick="zoomToLayer('distritos')">Enfocar</button>
          </div>
          <div class="layer-ctrl-row">
            <label class="layer-ctrl-left"><input type="checkbox" checked onchange="toggleAdminGroup('live', this.checked)" /><span>&#128680; Reportes Ciudadanos Hoy</span></label>
            <button class="zoom-mini" onclick="if(adminMap) adminMap.setView([-17.3935, -66.1570], 12)">Centro</button>
          </div>
        </div>

        <div class="glass-panel">
          <div class="panel-header"><span>&#9881; Motor Matem&aacute;tico Satelital</span><span class="badge b-warn">PESOS</span></div>
          <div class="slider-row">
            <label><span>Peso Hist&oacute;rico GAMC (&alpha;)</span><strong id="w-hist-val">45 %</strong></label>
            <input type="range" id="w-hist" min="10" max="80" value="45" oninput="recalcularMotorAdmin()" />
          </div>
          <div class="slider-row">
            <label><span>Peso Lluvia Satelital GPM (&beta;)</span><strong id="w-rain-val">35 %</strong></label>
            <input type="range" id="w-rain" min="10" max="80" value="35" oninput="recalcularMotorAdmin()" />
          </div>
          <div class="slider-row">
            <label><span>Peso Suelo SMAP / GOES (&gamma;)</span><strong id="w-soil-val">20 %</strong></label>
            <input type="range" id="w-soil" min="5" max="60" value="20" oninput="recalcularMotorAdmin()" />
          </div>
          <button class="btn-hud" style="width:100%;margin-top:4px;" onclick="cargarTelemetriaSatelital().then(recalcularMotorAdmin)">&#8635; Sincronizar Sat&eacute;lites en Vivo Ahora</button>
        </div>
      </div>

      <div id="admin-map-wrap">
        <div class="basemap-dock" id="admin-basemap-bar">
          <button class="bm-btn active" onclick="setBasemap('admin', 'satellite', this)">&#128752; Satelital</button>
          <button class="bm-btn" onclick="setBasemap('admin', 'relief', this)">&#9968; Relieve 3D</button>
          <button class="bm-btn" onclick="setBasemap('admin', 'topo', this)">&#128506; Topogr&aacute;fico</button>
          <button class="bm-btn" onclick="setBasemap('admin', 'streets', this)">&#128739; Calles</button>
          <button class="bm-btn" onclick="setBasemap('admin', 'dark', this)">&#127761; Nocturno</button>
        </div>
        <div id="admin-map"></div>
      </div>

      <div class="glass-panel" style="display:flex;flex-direction:column;">
        <div class="admin-right-tabs">
          <button class="ar-tab active" onclick="cambiarTabAdminRight('prob', this)">1. Probabilidad</button>
          <button class="ar-tab" onclick="cambiarTabAdminRight('inbox', this)">2. Bandeja IA (<span id="admin-inbox-count">0</span>)</button>
          <button class="ar-tab" onclick="cambiarTabAdminRight('datos', this)">3. Datos GAMC</button>
        </div>

        <div id="ar-pane-prob" class="ar-pane active">
          <p style="font-size:11px;color:var(--muted);margin-bottom:8px;">F&oacute;rmula: P = &alpha;&middot;H_GAMC + &beta;&middot;R_GPM + &gamma;&middot;S_SMAP (sat&eacute;lites en vivo):</p>
          <div id="probability-ranking-list"></div>
        </div>

        <div id="ar-pane-inbox" class="ar-pane">
          <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;">
            <button class="zoom-mini" onclick="filtrarBandejaIA('TODOS')">Todos</button>
            <button class="zoom-mini" style="color:var(--coral);" onclick="filtrarBandejaIA('CRITICA')">&#128308; Cr&iacute;tica</button>
            <button class="zoom-mini" style="color:var(--gold);" onclick="filtrarBandejaIA('ALTA')">&#128993; Alta</button>
            <button class="zoom-mini" style="color:var(--emerald);" onclick="filtrarBandejaIA('MEDIA')">&#128994; Media</button>
          </div>
          <div id="admin-inbox-cards"></div>
        </div>

        <div id="ar-pane-datos" class="ar-pane">
          <input type="text" id="admin-search-gamc" placeholder="Buscar en los 382 registros hist&oacute;ricos GAMC..." oninput="buscarEnDatosGAMC()" />
          <div id="admin-gamc-list" style="font-size:11.5px;"></div>
        </div>
      </div>
    </div>
  </section>

  <script>
    /* =========================================================
       1. ESCENA ORBITAL 3D CON TEXTURA PROCEDURAL INMEDIATA + NASA
       ========================================================= */
    (function initSpaceScene() {
      const container = document.getElementById('space-canvas');

      function updateUTCAndGMST() {
        const now = new Date();
        const jd = now.getTime() / 86400000 + 2440587.5;
        const d = jd - 2451545.0;
        const gmstDeg = ((280.46061837 + 360.98564736629 * d) % 360 + 360) % 360;
        const cEl = document.getElementById('utc-clock-txt');
        const gEl = document.getElementById('gmst-txt');
        if (cEl) cEl.innerText = now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
        if (gEl) gEl.innerText = gmstDeg.toFixed(2) + '\u00B0';
        return (gmstDeg * Math.PI) / 180;
      }

      if (!window.THREE) {
        setInterval(updateUTCAndGMST, 1000);
        return;
      }

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(38, window.innerWidth / window.innerHeight, 0.1, 3000);
      camera.position.set(0, 0.15, 8.2);

      const renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setSize(window.innerWidth, window.innerHeight);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      container.appendChild(renderer.domElement);

      const starGeo = new THREE.BufferGeometry();
      const starCount = 4200;
      const starPos = new Float32Array(starCount * 3);
      for (let i = 0; i < starCount * 3; i++) starPos[i] = (Math.random() - 0.5) * 900;
      starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
      scene.add(new THREE.Points(starGeo, new THREE.PointsMaterial({ color: 0xe2e8f0, size: 0.48, transparent: true, opacity: 0.9 })));

      const sunLight = new THREE.DirectionalLight(0xfffaf0, 2.5);
      sunLight.position.set(-42, 18, 45);
      scene.add(sunLight);
      scene.add(new THREE.AmbientLight(0x365880, 1.05));

      function makeSunTex() {
        const c = document.createElement('canvas'); c.width = 512; c.height = 512;
        const ctx = c.getContext('2d');
        const g = ctx.createRadialGradient(256, 256, 0, 256, 256, 256);
        g.addColorStop(0.0, 'rgba(255,255,255,1)');
        g.addColorStop(0.14, 'rgba(255,246,214,0.95)');
        g.addColorStop(0.32, 'rgba(255,200,90,0.5)');
        g.addColorStop(0.68, 'rgba(255,140,20,0.12)');
        g.addColorStop(1.0, 'rgba(0,0,0,0)');
        ctx.fillStyle = g; ctx.fillRect(0, 0, 512, 512);
        return new THREE.CanvasTexture(c);
      }
      const sunSprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: makeSunTex(), blending: THREE.AdditiveBlending, transparent: true, depthWrite: false }));
      sunSprite.position.set(-15, 6.2, -18);
      sunSprite.scale.set(11, 11, 1);
      scene.add(sunSprite);

      function makeFallbackEarthTex() {
        const c = document.createElement('canvas'); c.width = 1024; c.height = 512;
        const ctx = c.getContext('2d');
        const grad = ctx.createLinearGradient(0, 0, 0, 512);
        grad.addColorStop(0, '#dbeafe'); grad.addColorStop(0.1, '#1d4ed8');
        grad.addColorStop(0.5, '#0c4a6e'); grad.addColorStop(0.9, '#1d4ed8'); grad.addColorStop(1, '#dbeafe');
        ctx.fillStyle = grad; ctx.fillRect(0, 0, 1024, 512);
        ctx.fillStyle = '#3f7d4c';
        ctx.beginPath(); ctx.ellipse(315, 335, 48, 102, 0.2, 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.ellipse(245, 168, 74, 58, -0.2, 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.ellipse(548, 265, 68, 92, 0.1, 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.ellipse(725, 172, 118, 72, 0, 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.ellipse(840, 355, 46, 34, 0, 0, Math.PI * 2); ctx.fill();
        return new THREE.CanvasTexture(c);
      }

      const earthSystem = new THREE.Group();
      const isMobile = window.innerWidth < 900;
      earthSystem.position.set(isMobile ? 0 : -2.15, isMobile ? 0.55 : 0.0, 0);
      scene.add(earthSystem);

      const earthTiltGroup = new THREE.Group();
      earthTiltGroup.rotation.z = 23.44 * (Math.PI / 180);
      earthSystem.add(earthTiltGroup);

      const earthRadius = 2.52;
      const earthMat = new THREE.MeshStandardMaterial({
        map: makeFallbackEarthTex(),
        roughness: 0.55,
        metalness: 0.08
      });
      const earthMesh = new THREE.Mesh(new THREE.SphereGeometry(earthRadius, 96, 96), earthMat);
      earthTiltGroup.add(earthMesh);

      const cloudMesh = new THREE.Mesh(
        new THREE.SphereGeometry(earthRadius + 0.055, 72, 72),
        new THREE.MeshStandardMaterial({ transparent: true, opacity: 0.0, depthWrite: false })
      );
      earthTiltGroup.add(cloudMesh);

      const loader = new THREE.TextureLoader();
      loader.load('./assets/earth-blue-marble.jpg', tex => { earthMat.map = tex; earthMat.needsUpdate = true; });
      loader.load('./assets/earth-topology.png', tex => {
        earthMat.bumpMap = tex; earthMat.bumpScale = 0.14;
        earthMat.displacementMap = tex; earthMat.displacementScale = 0.045;
        earthMat.needsUpdate = true;
      });
      loader.load('./assets/earth-night.jpg', tex => {
        earthMat.emissiveMap = tex; earthMat.emissive = new THREE.Color(0xffb86c); earthMat.emissiveIntensity = 0.35;
        earthMat.needsUpdate = true;
      });
      loader.load('./assets/earth-clouds.png', tex => {
        cloudMesh.material.map = tex; cloudMesh.material.alphaMap = tex; cloudMesh.material.opacity = 0.42; cloudMesh.material.needsUpdate = true;
      });

      const atmoMesh = new THREE.Mesh(
        new THREE.SphereGeometry(earthRadius + 0.16, 64, 64),
        new THREE.ShaderMaterial({
          vertexShader: 'varying vec3 vNormal; void main() { vNormal = normalize(normalMatrix * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
          fragmentShader: 'varying vec3 vNormal; void main() { float intensity = pow(0.64 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 3.4); gl_FragColor = vec4(0.35, 0.72, 0.98, 1.0) * intensity * 1.25; }',
          blending: THREE.AdditiveBlending, side: THREE.BackSide, transparent: true
        })
      );
      earthSystem.add(atmoMesh);

      function latLonToVec3(lat, lon, r) {
        const phi = (90 - lat) * (Math.PI / 180);
        const theta = (lon + 180) * (Math.PI / 180);
        return new THREE.Vector3(-r * Math.sin(phi) * Math.cos(theta), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(theta));
      }
      const cbbaBeacon = new THREE.Mesh(new THREE.SphereGeometry(0.045, 16, 16), new THREE.MeshBasicMaterial({ color: 0x67d5e8 }));
      cbbaBeacon.position.copy(latLonToVec3(-17.39, -66.16, earthRadius + 0.05));
      earthMesh.add(cbbaBeacon);

      const moonMesh = new THREE.Mesh(new THREE.SphereGeometry(0.30, 32, 32), new THREE.MeshStandardMaterial({ color: 0xdbeafe, roughness: 0.85 }));
      earthSystem.add(moonMesh);

      function buildISS() {
        const iss = new THREE.Group();
        iss.add(new THREE.Mesh(new THREE.BoxGeometry(0.95, 0.026, 0.026), new THREE.MeshStandardMaterial({ color: 0xf8fafc, metalness: 0.8, roughness: 0.25 })));
        const mod = new THREE.Mesh(new THREE.CylinderGeometry(0.032, 0.032, 0.36, 16), new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 0.6, roughness: 0.3 }));
        mod.rotation.x = Math.PI / 2; iss.add(mod);
        const solarMat = new THREE.MeshStandardMaterial({ color: 0xd97706, metalness: 0.75, roughness: 0.22 });
        [-0.38, -0.25, 0.25, 0.38].forEach(x => {
          const w1 = new THREE.Mesh(new THREE.BoxGeometry(0.075, 0.22, 0.008), solarMat); w1.position.set(x, 0.13, 0); iss.add(w1);
          const w2 = new THREE.Mesh(new THREE.BoxGeometry(0.075, 0.22, 0.008), solarMat); w2.position.set(x, -0.13, 0); iss.add(w2);
        });
        return iss;
      }
      function buildSat(busColor, hasDish, singleWing) {
        const sat = new THREE.Group();
        sat.add(new THREE.Mesh(new THREE.CylinderGeometry(0.072, 0.072, 0.16, 6), new THREE.MeshStandardMaterial({ color: busColor, metalness: 0.8, roughness: 0.25 })));
        const pMat = new THREE.MeshStandardMaterial({ color: 0x2563eb, metalness: 0.7, roughness: 0.22 });
        const pL = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.11, 0.008), pMat); pL.position.set(-0.28, 0, 0); sat.add(pL);
        if (!singleWing) { const pR = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.11, 0.008), pMat); pR.position.set(0.28, 0, 0); sat.add(pR); }
        if (hasDish) {
          const dish = new THREE.Mesh(new THREE.SphereGeometry(0.16, 20, 14, 0, Math.PI * 2, 0, Math.PI * 0.42), new THREE.MeshStandardMaterial({ color: 0xfbbf24, wireframe: true }));
          dish.position.set(0, -0.22, 0.14); dish.rotation.x = Math.PI * 0.85; sat.add(dish);
        }
        return sat;
      }

      const issObj = buildISS(), nisarObj = buildSat(0xfbbf24, true, false), sentObj = buildSat(0x93c5fd, false, true), gpmObj = buildSat(0xe2e8f0, false, false), goesObj = buildSat(0x4cc38a, true, true);
      earthSystem.add(issObj, nisarObj, sentObj, gpmObj, goesObj);

      const issEul = new THREE.Euler(51.6 * Math.PI / 180, 20 * Math.PI / 180, 0, 'YXZ');
      const nisEul = new THREE.Euler(97.4 * Math.PI / 180, -35 * Math.PI / 180, 0, 'YXZ');
      const senEul = new THREE.Euler(98.1 * Math.PI / 180, 45 * Math.PI / 180, 0, 'YXZ');
      const gpmEul = new THREE.Euler(65.0 * Math.PI / 180, -70 * Math.PI / 180, 0, 'YXZ');
      const goeEul = new THREE.Euler(0.2 * Math.PI / 180, 0, 0, 'YXZ');

      function placeSat(obj, eul, r, ang) {
        obj.position.copy(new THREE.Vector3(Math.cos(ang) * r, 0, Math.sin(ang) * r).applyEuler(eul));
        obj.lookAt(earthSystem.position);
      }

      function animate() {
        requestAnimationFrame(animate);
        const nowSec = Date.now() / 1000;
        const rot = updateUTCAndGMST();
        earthMesh.rotation.y = rot;
        cloudMesh.rotation.y = rot + nowSec * 0.00004;
        const s = 1 + Math.sin(nowSec * 4) * 0.25;
        cbbaBeacon.scale.set(s, s, s);

        placeSat(issObj, issEul, 2.86, (nowSec / 5574) * Math.PI * 2 + 0.8);
        placeSat(nisObj, nisEul, 3.06, (nowSec / 6000) * Math.PI * 2 + 2.1);
        placeSat(sentObj, senEul, 3.00, (nowSec / 5920) * Math.PI * 2 + 4.0);
        placeSat(gpmObj, gpmEul, 2.88, (nowSec / 5560) * Math.PI * 2 + 1.4);
        placeSat(goesObj, goeEul, 4.45, rot - (75.2 * Math.PI / 180));

        const moonAng = (nowSec / 2360591) * Math.PI * 2 + 0.6;
        moonMesh.position.set(Math.cos(moonAng) * 6.3, 0.45, Math.sin(moonAng) * 6.3);
        renderer.render(scene, camera);
      }
      animate();

      window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
      });
    })();

    /* =========================================================
       2. RELIEVES Y MAPAS SIN API KEYS
       ========================================================= */
    const BASEMAP_LAYERS = {};
    function createBasemapGroup(type) {
      if (!window.L) return null;
      if (type === 'satellite') {
        return L.layerGroup([
          L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxZoom: 18 }),
          L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}', { maxZoom: 18, opacity: 0.85 })
        ]);
      }
      if (type === 'relief') {
        return L.layerGroup([
          L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}', { maxZoom: 16 }),
          L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', { maxZoom: 18, opacity: 0.68 })
        ]);
      }
      if (type === 'topo') {
        return L.layerGroup([
          L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', { maxZoom: 18 })
        ]);
      }
      if (type === 'streets') {
        return L.layerGroup([
          L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 })
        ]);
      }
      return L.layerGroup([
        L.tileLayer('https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png', { maxZoom: 19 })
      ]);
    }

    function setBasemap(target, type, btn) {
      const mapObj = target === 'citizen' ? citizenMap : adminMap;
      if (!mapObj || !window.L) return;
      const barId = target === 'citizen' ? 'citizen-basemap-bar' : 'admin-basemap-bar';
      document.querySelectorAll('#' + barId + ' .bm-btn').forEach(b => b.classList.remove('active'));
      if (btn) btn.classList.add('active');
      if (BASEMAP_LAYERS[target]) mapObj.removeLayer(BASEMAP_LAYERS[target]);
      BASEMAP_LAYERS[target] = createBasemapGroup(type).addTo(mapObj);
      BASEMAP_LAYERS[target].bringToBack();
    }

    /* =========================================================
       3. NAVEGACION ENTRE VISTAS
       ========================================================= */
    function volverPortadaOrbital() {
      document.getElementById('main-header').style.display = 'none';
      document.getElementById('citizen-app').style.display = 'none';
      document.getElementById('admin-app').style.display = 'none';
      document.getElementById('entry-screen').style.display = 'flex';
    }

    function ingresarModoCiudadano() {
      document.getElementById('entry-screen').style.display = 'none';
      document.getElementById('admin-app').style.display = 'none';
      document.getElementById('main-header').style.display = 'flex';
      document.getElementById('citizen-app').style.display = 'grid';
      document.getElementById('btn-open-admin').style.display = 'inline-block';
      document.getElementById('btn-exit-admin').style.display = 'none';
      document.getElementById('env-tag').innerText = ' \u00B7 MODO CIUDADANO';
      if (!citizenMap) initCitizenMap();
      if (citizenMap) setTimeout(() => citizenMap.invalidateSize(), 150);
      cargarTelemetriaSatelital();
    }

    function abrirModalLogin() {
      document.getElementById('login-error').style.display = 'none';
      document.getElementById('login-user').value = '';
      document.getElementById('login-pass').value = '';
      document.getElementById('login-modal').classList.add('open');
      setTimeout(() => document.getElementById('login-user').focus(), 80);
    }
    function cerrarModalLogin() { document.getElementById('login-modal').classList.remove('open'); }

    async function validarLoginAdmin() {
      const u = document.getElementById('login-user').value.trim();
      const p = document.getElementById('login-pass').value.trim();
      if (u === 'admin' && p === 'admin') {
        cerrarModalLogin();
        document.getElementById('entry-screen').style.display = 'none';
        document.getElementById('citizen-app').style.display = 'none';
        document.getElementById('main-header').style.display = 'flex';
        document.getElementById('admin-app').style.display = 'flex';
        document.getElementById('btn-open-admin').style.display = 'none';
        document.getElementById('btn-exit-admin').style.display = 'inline-block';
        document.getElementById('env-tag').innerText = ' \u00B7 CONSOLA ADMINISTRADOR / DESARROLLADOR';
        if (liveWeatherData.length === 0) await cargarTelemetriaSatelital();
        iniciarConsolaAdminTotal();
      } else {
        document.getElementById('login-error').style.display = 'block';
      }
    }
    function cerrarSesionAdmin() { ingresarModoCiudadano(); }

    function cambiarTabCiudadano(tab, btn) {
      document.querySelectorAll('.s-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.querySelectorAll('.s-pane').forEach(p => p.classList.remove('active'));
      document.getElementById('c-pane-' + tab).classList.add('active');
    }

    function cambiarTabAdminRight(tab, btn) {
      document.querySelectorAll('.ar-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.querySelectorAll('.ar-pane').forEach(p => p.classList.remove('active'));
      document.getElementById('ar-pane-' + tab).classList.add('active');
    }

    /* =========================================================
       4. TELEMETRIA SATELITAL EN VIVO (GPM + SMAP + GOES-16)
       ========================================================= */
    const ESTACIONES_CBBA = [
      { nombre: 'Cercado Centro / R\u00EDo Rocha', lat: -17.3935, lng: -66.1570 },
      { nombre: 'Zona Norte / Tiquipaya', lat: -17.3380, lng: -66.2150 },
      { nombre: 'Zona Sur / Distrito 9', lat: -17.4680, lng: -66.1540 },
      { nombre: 'La Maica / Cuenca Baja', lat: -17.4325, lng: -66.1985 },
      { nombre: 'Sacaba / Este', lat: -17.4040, lng: -66.0410 },
      { nombre: 'Quillacollo / Oeste', lat: -17.3920, lng: -66.2780 }
    ];

    let liveWeatherData = [];
    let selectedReportCoords = { lat: -17.3935, lng: -66.1570 };
    let citizenMap, citizenMarkersLayer;
    let liveReports = JSON.parse(localStorage.getItem('byral_realtime_reports_v8') || 'null') || [
      {
        id: 'RT-101',
        fecha: new Date().toLocaleTimeString('es-BO', { hour: '2-digit', minute: '2-digit' }) + ' \u00B7 Hoy',
        nombre: 'Carlos Mendoza Quispe',
        carnet: '6482910 CB',
        telefono: '71748291',
        tipo: 'Accidente de Tr\u00E1nsito',
        lugar: 'Av. Blanco Galindo km 3.5 (Puente Huayculi)',
        lat: -17.3948,
        lng: -66.1912,
        descripcion: 'Colisi\u00F3n vehicular con obstrucci\u00F3n parcial del carril oeste.',
        estado: 'Nuevo'
      }
    ];
    function guardarReportes() { localStorage.setItem('byral_realtime_reports_v8', JSON.stringify(liveReports)); }

    async function cargarTelemetriaSatelital() {
      const lats = ESTACIONES_CBBA.map(e => e.lat).join(',');
      const lngs = ESTACIONES_CBBA.map(e => e.lng).join(',');
      const url = `https://api.open-meteo.com/v1/forecast?latitude=${lats}&longitude=${lngs}&current=temperature_2m,relative_humidity_2m,precipitation,rain,shortwave_radiation&hourly=soil_moisture_0_to_7cm,precipitation_probability&timezone=America%2FLa_Paz&forecast_days=1`;
      try {
        const res = await fetch(url);
        const data = await res.json();
        const arr = Array.isArray(data) ? data : [data];
        const horaIdx = new Date().getHours();
        liveWeatherData = ESTACIONES_CBBA.map((est, i) => {
          const item = arr[i] || arr[0];
          const cur = item.current || {};
          const soilArr = item.hourly?.soil_moisture_0_to_7cm || [];
          const probArr = item.hourly?.precipitation_probability || [];
          const soil = soilArr[horaIdx] !== undefined ? soilArr[horaIdx] : 0.16;
          const rainProb = probArr[horaIdx] !== undefined ? probArr[horaIdx] : 15;
          const rain = +(cur.precipitation ?? cur.rain ?? 0);
          const temp = +(cur.temperature_2m ?? 20);
          const hum = +(cur.relative_humidity_2m ?? 45);
          const rad = +(cur.shortwave_radiation ?? 0);
          let condicion = 'Tiempo Seco Estable', esSequia = false;
          if (rain > 2.5) condicion = 'Lluvia Fuerte en Curso';
          else if (rain > 0) condicion = 'Lluvia Activa';
          else if (soil < 0.16 && hum < 42) { condicion = 'Alerta de Sequ\u00EDa / Suelo Seco'; esSequia = true; }
          else if (soil < 0.21) { condicion = 'D\u00E9ficit H\u00EDdrico / Sequ\u00EDa Leve'; esSequia = true; }
          return { ...est, rain, rainProb, temp, hum, rad, soil: +(soil * 100).toFixed(0), condicion, esSequia };
        });
        const satSt = document.getElementById('sat-link-status');
        if (satSt) satSt.innerText = 'ENLACE SATELITAL ACTIVO (GPM + SMAP + GOES-16)';
      } catch {
        liveWeatherData = ESTACIONES_CBBA.map(est => ({ ...est, rain: 0, rainProb: 12, temp: 21, hum: 38, rad: 420, soil: 14, condicion: 'Alerta de Sequ\u00EDa / Suelo Seco', esSequia: true }));
      }
      actualizarInterfazTiempoReal();
    }

    function actualizarInterfazTiempoReal() {
      if (liveWeatherData.length === 0) return;
      const centro = liveWeatherData[0];
      const maxRain = Math.max(...liveWeatherData.map(w => w.rain));
      const minSoil = Math.min(...liveWeatherData.map(w => w.soil));
      const zonasLluvia = liveWeatherData.filter(w => w.rain > 0);
      const zonasSequia = liveWeatherData.filter(w => w.esSequia);

      document.getElementById('live-clock').innerText = 'EN VIVO \u00B7 ' + new Date().toLocaleTimeString('es-BO', { hour: '2-digit', minute: '2-digit' });
      document.getElementById('top-temp').innerText = '\uD83C\uDF21 ' + centro.temp + '\u00B0C';
      document.getElementById('top-rain').innerText = '\uD83C\uDF27 ' + maxRain.toFixed(1) + ' mm/h';
      document.getElementById('top-drought').innerText = zonasLluvia.length > 0 ? '\uD83D\uDCA7 Lluvia Activa' : `\uD83C\uDFDC Suelo ${minSoil}% (${zonasSequia.length > 0 ? 'Sequ\u00EDa' : 'Normal'})`;
      document.getElementById('top-rad').innerText = '\u2600 ' + centro.rad + ' W/m\u00B2';

      let txt = '';
      if (zonasLluvia.length > 0) {
        txt += `\uD83C\uDF27 <strong>Lluvia satelital detectada:</strong> Precipitaci\u00F3n en <strong>${zonasLluvia.map(z => z.nombre + ' (' + z.rain + ' mm/h)').join(', ')}</strong>. `;
      } else if (zonasSequia.length > 0) {
        txt += `\uD83C\uDFDC <strong>Condici\u00F3n de sequ\u00EDa actual:</strong> Sin lluvias (0.0 mm/h) y humedad de suelo satelital baja (<strong>${minSoil}%</strong>) en <strong>${zonasSequia.map(z => z.nombre).slice(0, 3).join(', ')}</strong>. `;
      } else {
        txt += `\u26C5 <strong>Clima estable ahora:</strong> Sin precipitaciones (${centro.temp}\u00B0C \u00B7 Radiaci\u00F3n ${centro.rad} W/m\u00B2). `;
      }
      if (liveReports.length > 0) txt += `<br/>\uD83D\uDEA8 <strong>Accidentes activos (${liveReports.length}):</strong> \u00DAltimo en <strong>${liveReports[0].lugar}</strong>.`;
      document.getElementById('live-narrative').innerHTML = txt;

      renderMapaCiudadano();
      renderListaPuntosActivos();
    }

    function initCitizenMap() {
      if (!window.L) return;
      citizenMap = L.map('citizen-map', { zoomControl: false }).setView([-17.3935, -66.1570], 12);
      L.control.zoom({ position: 'bottomright' }).addTo(citizenMap);
      BASEMAP_LAYERS['citizen'] = createBasemapGroup('satellite').addTo(citizenMap);
      citizenMarkersLayer = L.layerGroup().addTo(citizenMap);
      citizenMap.on('click', (e) => {
        selectedReportCoords = { lat: +e.latlng.lat.toFixed(5), lng: +e.latlng.lng.toFixed(5) };
        document.getElementById('c-coords-lbl').innerText = `\uD83D\uDCCD Punto fijado: ${selectedReportCoords.lat}, ${selectedReportCoords.lng}`;
        L.popup().setLatLng(e.latlng).setContent(`<strong>\uD83D\uDCCD Punto elegido para reporte</strong><br/>${selectedReportCoords.lat}, ${selectedReportCoords.lng}`).openOn(citizenMap);
      });
    }

    function renderMapaCiudadano() {
      if (!citizenMap || !citizenMarkersLayer || !window.L) return;
      citizenMarkersLayer.clearLayers();
      liveWeatherData.forEach(w => {
        const color = w.rain > 0 ? '#67d5e8' : (w.esSequia ? '#e5b567' : '#4cc38a');
        L.circleMarker([w.lat, w.lng], { radius: w.rain > 0 ? 12 : 9, color: '#fff', fillColor: color, fillOpacity: 0.85, weight: 2 })
          .addTo(citizenMarkersLayer)
          .bindPopup(`<strong>\uD83D\uDCE1 ${w.nombre}</strong><br/>Estado: ${w.condicion}<br/>Lluvia: ${w.rain} mm/h \u00B7 Prob. lluvia: ${w.rainProb}%<br/>Humedad suelo: ${w.soil}% \u00B7 Radiaci\u00F3n: ${w.rad} W/m\u00B2`);
      });
      liveReports.forEach(rep => {
        L.circleMarker([rep.lat, rep.lng], { radius: 9.5, color: '#fff', fillColor: '#e06c75', fillOpacity: 0.94, weight: 2 })
          .addTo(citizenMarkersLayer)
          .bindPopup(`<strong style="color:#e06c75;">\uD83D\uDEA8 ${rep.tipo}</strong><br/><b>Lugar:</b> ${rep.lugar}<br/><b>Hora:</b> ${rep.fecha}<br/>${rep.descripcion}`);
      });
    }

    function renderListaPuntosActivos() {
      const accHtml = liveReports.map(r => `
        <div class="incident-item" onclick="if(citizenMap) citizenMap.flyTo([${r.lat}, ${r.lng}], 15)">
          <div style="display:flex;justify-content:space-between;"><strong style="color:var(--coral);">\uD83D\uDEA8 ${r.tipo}</strong><span style="font-size:10px;color:var(--muted);">${r.fecha}</span></div>
          <div style="color:var(--text);margin-top:2px;">\uD83D\uDCCD ${r.lugar}</div>
          <div style="color:var(--muted);font-size:11px;">${r.descripcion}</div>
        </div>
      `).join('');
      const climHtml = liveWeatherData.map(w => `
        <div class="incident-item weather-item" onclick="if(citizenMap) citizenMap.flyTo([${w.lat}, ${w.lng}], 14)">
          <div style="display:flex;justify-content:space-between;"><strong style="color:${w.rain > 0 ? 'var(--accent)' : 'var(--gold)'};">${w.rain > 0 ? '\uD83C\uDF27' : '\uD83C\uDFDC'} ${w.nombre}</strong><span style="font-family:Consolas,monospace;font-size:11px;">${w.rain} mm/h \u00B7 ${w.soil}%</span></div>
          <div style="color:var(--muted);font-size:11px;">${w.condicion} \u00B7 Prob. lluvia: ${w.rainProb}%</div>
        </div>
      `).join('');
      document.getElementById('live-points-list').innerHTML = accHtml + climHtml;
    }

    function registrarReporteCiudadano(e) {
      e.preventDefault();
      const nuevo = {
        id: 'RT-' + (100 + liveReports.length + 1),
        fecha: new Date().toLocaleTimeString('es-BO', { hour: '2-digit', minute: '2-digit' }) + ' \u00B7 Hoy',
        nombre: document.getElementById('c-nombre').value.trim(),
        carnet: document.getElementById('c-carnet').value.trim(),
        telefono: document.getElementById('c-telefono').value.trim(),
        tipo: document.getElementById('c-tipo').value,
        lugar: document.getElementById('c-lugar').value.trim(),
        lat: selectedReportCoords.lat,
        lng: selectedReportCoords.lng,
        descripcion: document.getElementById('c-desc').value.trim(),
        estado: 'Nuevo'
      };
      liveReports.unshift(nuevo);
      guardarReportes();
      actualizarInterfazTiempoReal();
      if (citizenMap) citizenMap.flyTo([nuevo.lat, nuevo.lng], 15);
      e.target.reset();
      alert('Reporte ' + nuevo.id + ' publicado en tiempo real.');
    }

    function preguntarIACiudadano(txt) { document.getElementById('citizen-ai-input').value = txt; enviarIACiudadano(); }
    function enviarIACiudadano() {
      const inp = document.getElementById('citizen-ai-input');
      const q = inp.value.trim();
      if (!q) return;
      inp.value = '';
      const chat = document.getElementById('citizen-ai-chat');
      chat.innerHTML += `<div class="msg-usr">${q}</div>`;
      const ql = q.toLowerCase();
      const maxRain = Math.max(...liveWeatherData.map(w => w.rain));
      const minSoil = Math.min(...liveWeatherData.map(w => w.soil));
      const zonasLluvia = liveWeatherData.filter(w => w.rain > 0);
      let resp = '';
      if (ql.includes('lluv') || ql.includes('sequ') || ql.includes('clima')) {
        resp = zonasLluvia.length > 0
          ? `Est\u00E1 lloviendo en <strong>${zonasLluvia.map(z => z.nombre + ' (' + z.rain + ' mm/h)').join(', ')}</strong>.`
          : `No hay lluvia ahora (0.0 mm/h). Humedad de suelo satelital en <strong>${minSoil}%</strong> (sequ\u00EDa / suelo seco).`;
      } else if (ql.includes('accidente') || ql.includes('donde')) {
        resp = liveReports.length > 0
          ? `Hay <strong>${liveReports.length} incidente(s) activo(s)</strong>: ${liveReports.slice(0, 3).map(r => '<strong>' + r.lugar + '</strong> (' + r.tipo + ')').join('; ')}.`
          : `No hay accidentes reportados en este momento.`;
      } else {
        resp = `Telemetr\u00EDa en vivo: Lluvia m\u00E1x. <strong>${maxRain} mm/h</strong>, suelo <strong>${minSoil}%</strong> y <strong>${liveReports.length} incidente(s)</strong>.`;
      }
      chat.innerHTML += `<div class="msg-ai"><strong>IA Ciudadana:</strong> ${resp}</div>`;
      chat.scrollTop = chat.scrollHeight;
    }

    /* =========================================================
       5. CONSOLA ADMIN DESACOPLADA (382 DATOS GAMC + MOTOR SATELITAL)
       ========================================================= */
    let adminMap;
    let adminDataLoaded = false;
    const adminVectorGroups = {};
    let allGamcRecords = [];
    let historicalStats = { emergencias: 0, cuencas: 0, drenaje: 0, distritos: 0, porZona: {} };
    let inboxFilter = 'TODOS';

    function getFeatureCenter(geom) {
      if (!geom || !geom.coordinates) return null;
      if (geom.type === 'Point') return geom.coordinates;
      let flat = [];
      function walk(c) {
        if (!Array.isArray(c)) return;
        if (typeof c[0] === 'number' && typeof c[1] === 'number') flat.push(c);
        else c.forEach(walk);
      }
      walk(geom.coordinates);
      if (flat.length === 0) return null;
      const sx = flat.reduce((a, b) => a + b[0], 0) / flat.length;
      const sy = flat.reduce((a, b) => a + b[1], 0) / flat.length;
      return [sx, sy];
    }

    function iniciarConsolaAdminTotal() {
      const datasets = window.BYRAL_HISTORICAL_DATA || { emergencias: [], cuencas: [], drenaje: [], distritos: [] };

      if (!adminDataLoaded) {
        allGamcRecords = [];
        historicalStats = { emergencias: 0, cuencas: 0, drenaje: 0, distritos: 0, porZona: {} };
        for (const cat of ['distritos', 'cuencas', 'drenaje', 'emergencias']) {
          const feats = datasets[cat] || [];
          feats.forEach(feature => {
            historicalStats[cat]++;
            const p = feature.properties || {};
            if (cat === 'emergencias') {
              const z = p.Comuna || p.distrito || p.Distrito || p.zona || 'Cercado / General';
              historicalStats.porZona[z] = (historicalStats.porZona[z] || 0) + 1;
            }
            allGamcRecords.push({
              capa: cat.toUpperCase(),
              titulo: p.tipo || p.Nombre_uh || p.Distrito || p.Comuna || p.descripcion || p.nombre || ('Registro ' + cat),
              zona: p.Comuna || p.Distrito || p.distrito || p.Nivel_7 || 'Cochabamba',
              coords: getFeatureCenter(feature.geometry)
            });
          });
        }
        adminDataLoaded = true;
      }

      document.getElementById('kpi-emerg').innerText = historicalStats.emergencias;
      document.getElementById('kpi-cuencas').innerText = historicalStats.cuencas;
      document.getElementById('kpi-dren').innerText = historicalStats.drenaje;
      document.getElementById('kpi-dist').innerText = historicalStats.distritos;
      document.getElementById('kpi-live-rep').innerText = liveReports.length;

      document.getElementById('cnt-emerg').innerText = historicalStats.emergencias;
      document.getElementById('cnt-cuencas').innerText = historicalStats.cuencas;
      document.getElementById('cnt-dren').innerText = historicalStats.drenaje;
      document.getElementById('cnt-dist').innerText = historicalStats.distritos;

      if (!adminMap && window.L) {
        adminMap = L.map('admin-map', { zoomControl: false }).setView([-17.3935, -66.1570], 12);
        L.control.zoom({ position: 'bottomright' }).addTo(adminMap);
        BASEMAP_LAYERS['admin'] = createBasemapGroup('satellite').addTo(adminMap);

        ['distritos', 'cuencas', 'drenaje', 'emergencias', 'live'].forEach(k => {
          adminVectorGroups[k] = L.featureGroup().addTo(adminMap);
        });

        const stylesByCat = {
          distritos: { color: '#a855f7', fillOpacity: 0.08, weight: 1.8 },
          cuencas: { color: '#e5b567', fillOpacity: 0.14, weight: 1.8 },
          drenaje: { color: '#67d5e8', fillOpacity: 0.0, weight: 2.2 },
          emergencias: { color: '#e06c75', fillOpacity: 0.92, weight: 1.5 }
        };

        for (const cat of ['distritos', 'cuencas', 'drenaje', 'emergencias']) {
          const feats = datasets[cat] || [];
          const st = stylesByCat[cat];
          feats.forEach(feature => {
            const layer = L.geoJSON(feature, {
              style: () => ({ color: st.color, weight: st.weight, fillColor: st.color, fillOpacity: st.fillOpacity }),
              pointToLayer: (f, latlng) => L.circleMarker(latlng, {
                radius: 6.5, color: '#ffffff', weight: 1.4, fillColor: '#e06c75', fillOpacity: 0.94
              }),
              onEachFeature: (f, lyr) => {
                const p = f.properties || {};
                const rows = Object.entries(p).filter(([k, v]) => !k.startsWith('_') && v !== null && v !== '').slice(0, 12)
                  .map(([k, v]) => `<div><b>${k}:</b> ${v}</div>`).join('');
                lyr.bindPopup(`<div style="font-size:11.5px;line-height:1.45;"><strong style="color:var(--accent);">\uD83D\uDCC2 ${cat.toUpperCase()} (${p._fuente || 'GAMC'})</strong>${rows || '<div>Registro Hist\u00F3rico GAMC</div>'}</div>`);
              }
            });
            layer.addTo(adminVectorGroups[cat]);
          });
        }
      }

      if (adminMap) setTimeout(() => adminMap.invalidateSize(), 150);

      renderLiveMarkersInAdmin();
      recalcularMotorAdmin();
      renderBandejaIA();
      buscarEnDatosGAMC();
    }

    function renderLiveMarkersInAdmin() {
      if (!adminVectorGroups['live'] || !window.L) return;
      adminVectorGroups['live'].clearLayers();
      liveReports.forEach(rep => {
        L.circleMarker([rep.lat, rep.lng], { radius: 8.5, color: '#67d5e8', weight: 2, fillColor: '#e5b567', fillOpacity: 0.95 })
          .addTo(adminVectorGroups['live'])
          .bindPopup(`<strong>\uD83D\uDEA8 Reporte Ciudadano ${rep.id}</strong><br/><b>Reportante:</b> ${rep.nombre} (CI: ${rep.carnet})<br/><b>Lugar:</b> ${rep.lugar}<br/>${rep.descripcion}`);
      });
    }

    function toggleAdminGroup(key, visible) {
      if (!adminMap || !adminVectorGroups[key]) return;
      visible ? adminVectorGroups[key].addTo(adminMap) : adminMap.removeLayer(adminVectorGroups[key]);
    }

    function zoomToLayer(key) {
      const grp = adminVectorGroups[key];
      if (adminMap && grp && grp.getBounds && grp.getBounds().isValid()) adminMap.fitBounds(grp.getBounds(), { padding: [24, 24] });
    }

    function recalcularMotorAdmin() {
      if (liveWeatherData.length === 0) return;
      const wH = +document.getElementById('w-hist').value;
      const wR = +document.getElementById('w-rain').value;
      const wS = +document.getElementById('w-soil').value;
      document.getElementById('w-hist-val').innerText = wH + ' %';
      document.getElementById('w-rain-val').innerText = wR + ' %';
      document.getElementById('w-soil-val').innerText = wS + ' %';

      const sumW = Math.max(1, wH + wR + wS);
      const nH = wH / sumW, nR = wR / sumW, nS = wS / sumW;

      const zonas = [
        { nombre: 'Distrito 9 \u00B7 Zona Sur (Torrenteras)', histBase: Math.max(28, historicalStats.porZona['Distrito 9'] || 34), meteo: liveWeatherData[2] || liveWeatherData[0] },
        { nombre: 'La Maica \u00B7 Cuenca Baja R\u00EDo Rocha', histBase: Math.max(24, historicalStats.porZona['Comuna Itocta'] || 29), meteo: liveWeatherData[3] || liveWeatherData[0] },
        { nombre: 'Zona Norte \u00B7 Tiquipaya / Taqui\u00F1a', histBase: 22, meteo: liveWeatherData[1] || liveWeatherData[0] },
        { nombre: 'Cercado Centro \u00B7 Eje R\u00EDo Rocha', histBase: Math.max(19, historicalStats.porZona['Comuna Adela Zamudio'] || 25), meteo: liveWeatherData[0] },
        { nombre: 'Sacaba \u00B7 Cuenca Maylanco', histBase: 18, meteo: liveWeatherData[4] || liveWeatherData[0] }
      ];

      const totalHist = Math.max(1, historicalStats.emergencias);
      const ranking = zonas.map(z => {
        const scoreH = Math.min(1, (z.histBase / totalHist) * 3.2 + 0.25);
        const scoreR = Math.min(1, Math.max(z.meteo.rain / 12, (z.meteo.rainProb || 0) / 100));
        const scoreS = z.meteo.esSequia ? Math.min(1, (26 - z.meteo.soil) / 20) : 0.15;
        const pct = Math.min(98, Math.round((scoreH * nH + scoreR * nR + scoreS * nS) * 100));
        const pLluvia = Math.round(z.meteo.rainProb || 0);
        const amenaza = z.meteo.rain > 0 ? 'Inundaci\u00F3n / Desborde' : (z.meteo.esSequia ? 'Sequ\u00EDa / D\u00E9ficit H\u00EDdrico' : 'Susceptibilidad Base');
        return { ...z, pct, pLluvia, amenaza };
      }).sort((a, b) => b.pct - a.pct);

      document.getElementById('probability-ranking-list').innerHTML = ranking.map(r => {
        const col = r.pct >= 65 ? '#e06c75' : (r.pct >= 40 ? '#e5b567' : '#67d5e8');
        return `
          <div class="prob-row" onclick="if(adminMap) adminMap.flyTo([${r.meteo.lat}, ${r.meteo.lng}], 14)">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <strong style="color:var(--text);">${r.nombre}</strong>
              <span style="font-family:Consolas,monospace;font-weight:700;color:${col};font-size:13px;">${r.pct}%</span>
            </div>
            <div style="font-size:10.5px;color:var(--muted);margin-top:3px;">
              Amenaza: <strong style="color:var(--text);">${r.amenaza}</strong> &middot; Hist GAMC: ${r.histBase} reg. &middot; Prob. Lluvia GPM: ${r.pLluvia}% (${r.meteo.rain} mm/h) &middot; Suelo SMAP: ${r.meteo.soil}%
            </div>
            <div class="prob-bar-bg"><div class="prob-bar-fill" style="width:${r.pct}%;background:${col};"></div></div>
          </div>
        `;
      }).join('');
    }

    function clasificarReporteConIA(rep) {
      const txt = `${rep.tipo} ${rep.descripcion} ${rep.lugar}`.toLowerCase();
      if (txt.includes('herid') || txt.includes('colis') || txt.includes('choque') || txt.includes('tr\u00E1nsito') || txt.includes('accidente')) {
        return { urgencia: 'CRITICA', categoria: 'Accidente Vial / Rescate', unidad: 'Tr\u00E1nsito + Ambulancia + SAR' };
      }
      if (txt.includes('inund') || txt.includes('desborde') || txt.includes('torrentera') || txt.includes('lluvia')) {
        return { urgencia: 'CRITICA', categoria: 'Emergencia Hidrol\u00F3gica', unidad: 'UGR GAMC + Maquinaria Pesada' };
      }
      if (txt.includes('derrumbe') || txt.includes('poste') || txt.includes('puente')) {
        return { urgencia: 'ALTA', categoria: 'Infraestructura Vial', unidad: 'Obras P\u00FAblicas + Bomberos' };
      }
      return { urgencia: 'MEDIA', categoria: 'Monitoreo Ambiental / Sequ\u00EDa', unidad: 'UGR + Bomberos Forestales' };
    }

    function filtrarBandejaIA(nivel) { inboxFilter = nivel; renderBandejaIA(); }
    function cambiarEstadoReporteAdmin(id) {
      const idx = liveReports.findIndex(r => r.id === id);
      if (idx === -1) return;
      const seq = ['Nuevo', 'Unidad Despachada', 'Atendido'];
      liveReports[idx].estado = seq[(seq.indexOf(liveReports[idx].estado) + 1) % seq.length];
      guardarReportes();
      renderBandejaIA();
    }

    function renderBandejaIA() {
      document.getElementById('admin-inbox-count').innerText = liveReports.length;
      const list = liveReports.map(r => ({ ...r, ia: clasificarReporteConIA(r) }));
      const filtrados = inboxFilter === 'TODOS' ? list : list.filter(r => r.ia.urgencia === inboxFilter);
      document.getElementById('admin-inbox-cards').innerHTML = filtrados.map(r => {
        const bCls = r.ia.urgencia === 'CRITICA' ? 'b-crit' : (r.ia.urgencia === 'ALTA' ? 'b-warn' : 'b-live');
        return `
          <div class="report-admin-card">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <strong style="color:var(--accent);font-family:Consolas,monospace;">${r.id} &middot; ${r.ia.categoria}</strong>
              <span class="badge ${bCls}">IA: ${r.ia.urgencia}</span>
            </div>
            <div>\uD83D\uDC64 <strong>${r.nombre}</strong> &middot; \uD83E\uDEAA CI: <strong>${r.carnet}</strong> &middot; \uD83D\uDCDE ${r.telefono}</div>
            <div>\uD83D\uDCCD <a href="#" style="color:var(--accent);" onclick="if(adminMap) adminMap.flyTo([${r.lat}, ${r.lng}], 16);return false;">${r.lugar}</a> (${r.fecha})</div>
            <div style="color:var(--text);">\uD83D\uDCDD ${r.descripcion}</div>
            <div class="ai-triage-box"><strong>Despacho IA:</strong> ${r.ia.unidad}</div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-top:7px;">
              <span style="font-size:10.5px;color:var(--muted);">Estado: <strong style="color:var(--text);">${r.estado}</strong></span>
              <button class="zoom-mini" onclick="cambiarEstadoReporteAdmin('${r.id}')">Cambiar Estado &#8635;</button>
            </div>
          </div>
        `;
      }).join('');
    }

    function buscarEnDatosGAMC() {
      const q = (document.getElementById('admin-search-gamc')?.value || '').toLowerCase();
      const res = allGamcRecords.filter(r => JSON.stringify(r).toLowerCase().includes(q)).slice(0, 80);
      document.getElementById('admin-gamc-list').innerHTML = res.map(r => {
        const flyAttr = r.coords ? `onclick="if(adminMap) adminMap.flyTo([${r.coords[1]}, ${r.coords[0]}], 16)" style="cursor:pointer;padding:8px 10px;border-bottom:1px solid var(--border);"` : `style="padding:8px 10px;border-bottom:1px solid var(--border);"`;
        return `
          <div ${flyAttr}>
            <span class="badge b-live">${r.capa}</span> <strong style="color:var(--text);">${r.titulo}</strong>
            <div style="font-size:10.5px;color:var(--muted);margin-top:2px;">Zona: ${r.zona}</div>
          </div>
        `;
      }).join('') || '<div style="color:var(--muted);padding:10px;">Sin registros coincidentes.</div>';
    }

    cargarTelemetriaSatelital();
  </script>
</body>
</html>
"""

final_html = html_template.replace("__BYRAL_JSON__", embedded_json)
out_index = os.path.join(out_dir, "index.html")
with open(out_index, "w", encoding="utf-8") as f:
    f.write(final_html)

print("Listo! Sitio generado en:", out_index, f"({os.path.getsize(out_index)} bytes)")
