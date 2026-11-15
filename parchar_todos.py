import glob, re

archivos = glob.glob("**/index.html", recursive=True)
if os.path.exists("index.html") and "index.html" not in archivos:
    archivos.append("index.html")

parche = """
<!-- BYRAL SOLUCION COMPLETA -->
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
@media screen and (max-width: 768px) {
    body, html { overflow-x: hidden !important; }
    #map, .leaflet-container {
        position: fixed !important; top: 0 !important; left: 0 !important;
        width: 100vw !important; height: 100vh !important; z-index: 1 !important;
    }
    aside, .sidebar, .panel, .control-panel, [class*="sidebar"], [class*="panel-left"], [class*="panel-right"] {
        position: fixed !important; bottom: 0 !important; left: 0 !important; right: 0 !important; top: auto !important;
        width: 100% !important; max-width: 100% !important; max-height: 44vh !important;
        overflow-y: auto !important; z-index: 1000 !important;
        border-radius: 16px 16px 0 0 !important; background: rgba(10, 15, 28, 0.95) !important;
    }
    #byral-hud-usuario {
        top: 52px !important; bottom: auto !important; left: 8px !important; right: 8px !important;
        width: auto !important; max-width: none !important;
    }
}
</style>

<div id="byral-lang-box" style="position:fixed; top:10px; right:12px; z-index:999999; display:flex; gap:6px; align-items:center; background:rgba(15,23,42,0.92); padding:5px 10px; border-radius:8px; border:1px solid rgba(56,189,248,0.45);">
    <div id="google_translate_element"></div>
    <button onclick="alternarIdiomaManual()" style="background:#0284c7; color:#fff; border:none; border-radius:5px; padding:4px 8px; font-size:11px; font-weight:700; cursor:pointer;">EN / ES</button>
</div>
<script src="https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit"></script>
<script>
function googleTranslateElementInit() {
    if (window.google && google.translate) {
        new google.translate.TranslateElement({pageLanguage: 'es', includedLanguages: 'en,es', layout: google.translate.TranslateElement.InlineLayout.SIMPLE}, 'google_translate_element');
    }
}
function alternarIdiomaManual() {
    const dict = {
        'Probabilidad de Ocurrencia': 'Occurrence Probability', 'Occurrence Probability': 'Probabilidad de Ocurrencia',
        'En Vivo': 'Live', 'Live': 'En Vivo', 'Reportar': 'Report', 'Report': 'Reportar',
        'Asistente IA': 'AI Assistant', 'AI Assistant': 'Asistente IA',
        'Sincronizar Satélites': 'Synchronize Satellites', 'Synchronize Satellites': 'Sincronizar Satélites'
    };
    document.querySelectorAll('span, button, a, div, h1, h2, h3, label').forEach(el => {
        if (el.children.length === 0 && dict[el.innerText.trim()]) el.innerText = dict[el.innerText.trim()];
    });
}
</script>

<div id="byral-hud-usuario" style="position:fixed; bottom:14px; right:14px; z-index:99999; width:350px; background:rgba(10,15,28,0.95); border:1px solid rgba(56,189,248,0.5); border-radius:12px; padding:14px; color:#f8fafc; font-family:system-ui,sans-serif; font-size:12px; box-shadow:0 10px 30px rgba(0,0,0,0.8); backdrop-filter:blur(12px);">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="color:#94a3b8; font-weight:700; text-transform:uppercase; font-size:11px;">Probabilidad de Ocurrencia</span>
        <span id="byral-prob" style="font-size:20px; font-weight:800; color:#facc15;">--%</span>
    </div>
    <div id="byral-lluvia-estado" style="margin:6px 0; padding:6px 8px; border-radius:6px; background:rgba(56,189,248,0.12); color:#38bdf8; font-weight:600;">
        Calculando lluvia torrencial en tiempo real...
    </div>
    <div style="border-top:1px solid rgba(255,255,255,0.12); padding-top:6px; color:#cbd5e1; line-height:1.5;">
        <div>📍 <b>Latitud / Longitud:</b> <span id="byral-coords">-17.3935°, -66.1570°</span></div>
        <div>📊 <b>Magnitud / Histórico:</b> <span id="byral-magnitud">0.0 mm/h · 240 eventos GAMC</span></div>
    </div>
    <div style="margin-top:8px; border-top:1px solid rgba(255,255,255,0.12); padding-top:8px;">
        <div style="font-size:11px; font-weight:700; color:#94a3b8; margin-bottom:4px;">ASISTENTE IA (INTERNET + TIEMPO REAL + GAMC)</div>
        <div id="byral-chat-log" style="height:115px; overflow-y:auto; background:rgba(15,23,42,0.85); border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:8px; margin-bottom:6px; line-height:1.4;">
            IA activa. Consulta sobre lluvias torrenciales, datos históricos GAMC o cualquier tema.
        </div>
        <div style="display:flex; gap:5px;">
            <input id="byral-chat-in" type="text" placeholder="Pregunta a la IA..." onkeydown="if(event.key==='Enter') preguntarIA()" style="flex:1; background:#1e293b; border:1px solid #475569; color:#fff; padding:6px 8px; border-radius:6px; font-size:12px;">
            <button onclick="preguntarIA()" style="background:#2563eb; color:#fff; border:none; padding:6px 12px; border-radius:6px; font-weight:700; cursor:pointer;">Enviar</button>
        </div>
    </div>
</div>

<script>
let latActual = -17.3935, lonActual = -66.1570;
let infoClimaIA = "Sin datos", infoProbIA = "48%";

async function actualizarMotorTiempoReal(lat = latActual, lon = lonActual) {
    try {
        const r = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=precipitation,rain,temperature_2m&hourly=precipitation_probability,precipitation&timezone=America%2FLa_Paz`);
        const d = await r.json();
        const lluvia = d.current.precipitation || 0;
        const temp = d.current.temperature_2m || 22;
        const probH = (d.hourly && d.hourly.precipitation_probability) ? d.hourly.precipitation_probability[0] : 0;
        const lluviaProx = (d.hourly && d.hourly.precipitation) ? d.hourly.precipitation[0] : 0;

        const maxMm = Math.max(lluvia, lluviaProx);
        const histGAMC = (116 / 240) * 100;
        const probTotal = Math.round((probH * 0.45) + (Math.min((maxMm / 15) * 100, 100) * 0.25) + (histGAMC * 0.30));
        const torrencial = maxMm >= 10 || probH >= 75;

        infoProbIA = probTotal + "%";
        infoClimaIA = torrencial
            ? `⚠️ ALERTA LLUVIA TORRENCIAL (${maxMm} mm/h · ${temp}°C)`
            : `✅ Sin lluvia torrencial (${maxMm} mm/h · Prob: ${probH}% · ${temp}°C)`;

        document.getElementById("byral-prob").innerText = infoProbIA;
        document.getElementById("byral-lluvia-estado").innerText = infoClimaIA;
        document.getElementById("byral-coords").innerText = `${lat.toFixed(4)}°, ${lon.toFixed(4)}°`;
        document.getElementById("byral-magnitud").innerText = `Intensidad: ${maxMm} mm/h · Hist. GAMC: 240 eventos (116 críticos)`;
    } catch (e) {
        document.getElementById("byral-lluvia-estado").innerText = "Error de red meteorológica.";
    }
}

async function preguntarIA() {
    const inp = document.getElementById("byral-chat-in");
    const log = document.getElementById("byral-chat-log");
    const q = inp.value.trim();
    if (!q) return;
    inp.value = "";
    log.innerHTML += `<div style="margin-top:5px; color:#38bdf8;"><b>Tú:</b> ${q}</div>`;
    const lid = "msg-" + Date.now();
    log.innerHTML += `<div id="${lid}" style="margin-top:3px; color:#94a3b8;"><i>Analizando datos en tiempo real e historial...</i></div>`;
    log.scrollTop = log.scrollHeight;

    const contexto = `Eres el Asistente IA de BYRAL Sentinela en Cochabamba, Bolivia. Responde cualquier pregunta general o técnica como una IA completa y usa estos datos reales e históricos cuando corresponda: Coordenadas=${latActual.toFixed(4)}, ${lonActual.toFixed(4)}; Clima en vivo=${infoClimaIA}; Probabilidad de ocurrencia=${infoProbIA}; Base histórica GAMC=240 emergencias (116 críticas, 103 altas, 21 medias en Distrito 9, Río Rocha, Tiquipaya, La Maica, Sacaba y Quillacollo). Pregunta: ${q}`;

    try {
        const res = await fetch(`https://text.pollinations.ai/${encodeURIComponent(contexto)}`);
        const txt = await res.text();
        document.getElementById(lid).innerHTML = `<b>IA:</b> ${txt}`;
    } catch (e) {
        document.getElementById(lid).innerHTML = `<b>IA:</b> En (${latActual.toFixed(4)}, ${lonActual.toFixed(4)}) el estado es ${infoClimaIA} con probabilidad ${infoProbIA} según los 240 eventos históricos del GAMC.`;
    }
    log.scrollTop = log.scrollHeight;
}

window.addEventListener("load", () => {
    actualizarMotorTiempoReal();
    setTimeout(() => {
        if (typeof map !== "undefined" && map.on) {
            map.on("click", e => {
                latActual = e.latlng.lat;
                lonActual = e.latlng.lng;
                actualizarMotorTiempoReal(latActual, lonActual);
            });
        }
    }, 1200);
});
</script>
"""

for ruta in set(archivos):
    with open(ruta, "r", encoding="utf-8") as f:
        html = f.read()
    html = re.sub(r'<!-- BYRAL MODULO TIEMPO REAL.*?</script>', '', html, flags=re.S)
    html = re.sub(r'<!-- BYRAL SOLUCION COMPLETA.*?</script>', '', html, flags=re.S)
    if "</body>" in html:
        html = html.replace("</body>", parche + "\n</body>")
    else:
        html += parche
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"PARCHADO: {ruta}")
