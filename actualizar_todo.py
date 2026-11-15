import os

ruta_html = os.path.join("sitio_final", "index.html")

if not os.path.exists(ruta_html):
    print(f"No se encontró {ruta_html}. Verifica estar en la carpeta raíz del proyecto.")
    exit()

with open(ruta_html, "r", encoding="utf-8") as f:
    html = f.read()

inyeccion_head = """
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
@media screen and (max-width: 768px) {
    body, html { overflow-x: hidden !important; }
    #map { width: 100vw !important; height: 100vh !important; position: fixed !important; top: 0; left: 0; z-index: 1 !important; }
    .sidebar, .control-panel, .panel-flotante, aside, div[class*="panel"], div[class*="sidebar"] {
        position: fixed !important;
        bottom: 0 !important;
        left: 0 !important;
        right: 0 !important;
        top: auto !important;
        width: 100% !important;
        max-width: 100% !important;
        max-height: 48vh !important;
        overflow-y: auto !important;
        z-index: 1000 !important;
        border-radius: 16px 16px 0 0 !important;
        background: rgba(10, 15, 28, 0.94) !important;
        backdrop-filter: blur(12px) !important;
    }
}
#byral-floating-hud {
    position: fixed;
    bottom: 12px;
    left: 12px;
    z-index: 9999;
    background: rgba(15, 23, 42, 0.92);
    border: 1px solid rgba(56, 189, 248, 0.4);
    border-radius: 12px;
    padding: 12px 15px;
    color: #f8fafc;
    font-family: system-ui, sans-serif;
    font-size: 12px;
    max-width: 340px;
    box-shadow: 0 8px 25px rgba(0,0,0,0.6);
    backdrop-filter: blur(10px);
}
@media screen and (max-width: 768px) {
    #byral-floating-hud {
        top: 55px;
        bottom: auto;
        left: 10px;
        right: 10px;
        max-width: none;
    }
}
</style>
"""

inyeccion_body = """
<div id="google_translate_element" style="position: fixed; top: 10px; right: 12px; z-index: 99999; background: rgba(15,23,42,0.85); padding: 4px 8px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.2);"></div>
<script type="text/javascript">
function googleTranslateElementInit() {
  new google.translate.TranslateElement({pageLanguage: 'es', includedLanguages: 'en,es', layout: google.translate.TranslateElement.InlineLayout.SIMPLE}, 'google_translate_element');
}
</script>
<script type="text/javascript" src="//translate.google.com/translate_a/element.js?cb=googleTranslateElementInit"></script>

<div id="byral-floating-hud">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
        <span style="color:#94a3b8; font-weight:600; text-transform:uppercase;">Probabilidad de Ocurrencia</span>
        <span id="hud-prob" style="font-size:18px; font-weight:800; color:#facc15;">--%</span>
    </div>
    <div id="hud-lluvia" style="color:#38bdf8; font-weight:600; margin-bottom:6px;">Sincronizando radar en tiempo real...</div>
    <div style="color:#cbd5e1; line-height:1.5; border-top:1px solid rgba(255,255,255,0.1); padding-top:6px;">
        <div>📍 <b>Coords:</b> <span id="hud-coords">-17.3935°, -66.1570°</span></div>
        <div>📊 <b>Magnitud / Histórico:</b> <span id="hud-mag">240 eventos GAMC (116 críticos)</span></div>
    </div>
    <div style="margin-top:8px; border-top:1px solid rgba(255,255,255,0.1); padding-top:8px;">
        <div style="display:flex; gap:5px;">
            <input id="hud-ia-input" type="text" placeholder="Pregunta a la IA (clima, historial, zonas)..." style="flex:1; background:rgba(30,41,59,0.9); border:1px solid #475569; color:white; padding:6px 8px; border-radius:6px; font-size:12px;">
            <button onclick="consultarIAByral()" style="background:#2563eb; color:white; border:none; padding:6px 10px; border-radius:6px; cursor:pointer; font-weight:600;">IA</button>
        </div>
        <div id="hud-ia-resp" style="margin-top:6px; color:#e2e8f0; max-height:110px; overflow-y:auto; font-size:11.5px; line-height:1.4;"></div>
    </div>
</div>

<script>
let byralLat = -17.3935;
let byralLon = -66.1570;

async function actualizarDatosTiempoReal(lat = byralLat, lon = byralLon) {
    try {
        const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=precipitation,rain,temperature_2m&hourly=precipitation_probability&timezone=America%2FLa_Paz`);
        const data = await res.json();
        const lluvia = data.current.precipitation || 0;
        const temp = data.current.temperature_2m || 22;
        const probHora = (data.hourly && data.hourly.precipitation_probability) ? data.hourly.precipitation_probability[0] : 0;

        const baseHistorica = 48.3;
        const factorTorrencial = Math.min((lluvia / 15.0) * 100, 100);
        const probTotal = Math.round((probHora * 0.45) + (factorTorrencial * 0.25) + (baseHistorica * 0.30));
        const torrencial = lluvia >= 10 || probHora >= 75;

        document.getElementById('hud-prob').innerText = probTotal + '%';
        document.getElementById('hud-lluvia').innerText = torrencial
            ? `⚠️ ALERTA LLUVIA TORRENCIAL (${lluvia} mm/h | ${temp}°C)`
            : `✅ Sin lluvia torrencial (${lluvia} mm/h | Prob: ${probHora}% | ${temp}°C)`;
        document.getElementById('hud-coords').innerText = `Lat: ${lat.toFixed(4)}° | Lon: ${lon.toFixed(4)}°`;
        document.getElementById('hud-mag').innerText = `Intensidad: ${lluvia} mm/h · Base GAMC: 240 eventos`;
    } catch (e) {
        document.getElementById('hud-lluvia').innerText = "Error conectando clima satelital.";
    }
}

async function consultarIAByral() {
    const input = document.getElementById('hud-ia-input');
    const respBox = document.getElementById('hud-ia-resp');
    const pregunta = input.value.trim();
    if (!pregunta) return;

    respBox.innerText = "Consultando satélites, historial GAMC e internet...";
    const climaActual = document.getElementById('hud-lluvia').innerText;
    const probActual = document.getElementById('hud-prob').innerText;
    const coordsActual = document.getElementById('hud-coords').innerText;

    const promptCompleto = `Eres el Asistente IA de BYRAL Sentinela en Cochabamba, Bolivia. Responde de forma clara y directa usando estos datos en tiempo real e históricos: Coordenadas=${coordsActual}, Clima=${climaActual}, Probabilidad de ocurrencia=${probActual}, Base Histórica GAMC=240 emergencias (116 críticas, 103 altas en Río Rocha, Distrito 9, Tiquipaya, La Maica, Sacaba, Quillacollo). Pregunta del usuario: ${pregunta}`;

    try {
        const url = `https://text.pollinations.ai/${encodeURIComponent(promptCompleto)}`;
        const res = await fetch(url);
        const texto = await res.text();
        respBox.innerText = texto;
    } catch (e) {
        respBox.innerText = "No se pudo conectar con la IA en este momento.";
    }
}

window.addEventListener('load', () => {
    actualizarDatosTiempoReal();
    if (typeof map !== 'undefined' && map.on) {
        map.on('click', (e) => {
            byralLat = e.latlng.lat;
            byralLon = e.latlng.lng;
            actualizarDatosTiempoReal(byralLat, byralLon);
        });
    }
});
</script>
"""

if "</head>" in html and "byral-floating-hud" not in html:
    html = html.replace("</head>", inyeccion_head + "\n</head>")

if "</body>" in html and "byral-floating-hud" not in html:
    html = html.replace("</body>", inyeccion_body + "\n</body>")

with open(ruta_html, "w", encoding="utf-8") as f:
    f.write(html)

print("¡ÉXITO! Se actualizó sitio_final/index.html correctamente.")
