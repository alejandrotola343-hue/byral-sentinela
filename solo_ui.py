import os, re, shutil

ruta = os.path.join("publicar_seguro", "index.html")
if not os.path.exists(ruta):
    print("ERROR: No se encontró publicar_seguro\\index.html")
    exit()

# Respaldo de seguridad fuera de la carpeta pública
shutil.copy2(ruta, "backup_index.html")

with open(ruta, "r", encoding="utf-8") as f:
    html = f.read()

# Limpiar inyecciones previas si existen
html = re.sub(r'<!-- BYRAL PARCHE DEFINITIVO.*?</script>', '', html, flags=re.S)
html = re.sub(r'<!-- BYRAL SOLUCION COMPLETA.*?</script>', '', html, flags=re.S)
html = re.sub(r'<!-- BYRAL MODULO TIEMPO REAL.*?</script>', '', html, flags=re.S)

parche_ui = r"""
<!-- BYRAL PARCHE DEFINITIVO -->
<style>
@media screen and (max-width: 768px) {
    html, body { overflow-x: hidden !important; max-width: 100vw !important; }
    #map, .leaflet-container {
        position: fixed !important; top: 0 !important; left: 0 !important;
        width: 100vw !important; height: 100vh !important; z-index: 1 !important;
    }
    aside, .sidebar, .panel, .control-panel, [class*="sidebar"], [class*="panel-left"], [class*="panel-right"] {
        position: fixed !important; bottom: 0 !important; left: 0 !important; right: 0 !important; top: auto !important;
        width: 100% !important; max-width: 100% !important; max-height: 42vh !important;
        overflow-y: auto !important; z-index: 1000 !important;
        border-radius: 16px 16px 0 0 !important;
    }
    #byral-user-widget {
        top: 52px !important; bottom: auto !important; left: 8px !important; right: 8px !important;
        width: auto !important; max-width: none !important;
    }
}
</style>

<div id="byral-lang-bar" style="position:fixed; top:10px; right:12px; z-index:999999; display:flex; align-items:center; gap:6px; background:rgba(10,15,28,0.92); border:1px solid rgba(56,189,248,0.5); padding:5px 10px; border-radius:8px; backdrop-filter:blur(10px);">
    <div id="google_translate_element"></div>
    <button onclick="byralToggleLang()" style="background:#0284c7; color:#fff; border:none; border-radius:5px; padding:4px 9px; font-size:11px; font-weight:700; cursor:pointer;">EN / ES</button>
</div>
<script src="https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit"></script>
<script>
function googleTranslateElementInit() {
    if (window.google && google.translate) {
        new google.translate.TranslateElement({
            pageLanguage: 'es',
            includedLanguages: 'en,es',
            layout: google.translate.TranslateElement.InlineLayout.SIMPLE
        }, 'google_translate_element');
    }
}
function byralToggleLang() {
    const mapaTexto = {
        'Probabilidad de Ocurrencia': 'Occurrence Probability',
        'Occurrence Probability': 'Probabilidad de Ocurrencia',
        'Asistente IA': 'AI Assistant',
        'AI Assistant': 'Asistente IA',
        'Sincronizar Satélites': 'Synchronize Satellites',
        'Synchronize Satellites': 'Sincronizar Satélites',
        'En Vivo': 'Live',
        'Live': 'En Vivo'
    };
    document.querySelectorAll('span, button, a, div, h1, h2, h3, label, strong').forEach(el => {
        if (el.children.length === 0) {
            const t = el.innerText.trim();
            if (mapaTexto[t]) el.innerText = mapaTexto[t];
        }
    });
}
</script>

<div id="byral-user-widget" style="position:fixed; bottom:14px; right:14px; z-index:99999; width:360px; background:rgba(10,15,28,0.95); border:1px solid rgba(56,189,248,0.55); border-radius:14px; padding:14px; color:#f8fafc; font-family:system-ui,-apple-system,sans-serif; font-size:12px; box-shadow:0 12px 32px rgba(0,0,0,0.85); backdrop-filter:blur(14px);">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
        <span style="color:#94a3b8; font-weight:700; text-transform:uppercase; font-size:11px; letter-spacing:0.5px;">Probabilidad de Ocurrencia</span>
        <div style="display:flex; align-items:center; gap:8px;">
            <span id="byral-prob-num" style="font-size:20px; font-weight:800; color:#facc15;">--%</span>
            <button onclick="const b=document.getElementById('byral-widget-body'); b.style.display=b.style.display==='none'?'block':'none';" style="background:rgba(255,255,255,0.1); color:#cbd5e1; border:none; border-radius:4px; padding:2px 7px; cursor:pointer; font-size:11px;">_</button>
        </div>
    </div>

    <div id="byral-widget-body">
        <div id="byral-rain-box" style="margin:6px 0 8px 0; padding:7px 9px; border-radius:7px; background:rgba(56,189,248,0.12); color:#38bdf8; font-weight:600; line-height:1.35;">
            Calculando lluvia torrencial en tiempo real...
        </div>

        <div style="border-top:1px solid rgba(255,255,255,0.12); padding-top:7px; color:#cbd5e1; line-height:1.55;">
            <div>📍 <b>Latitud / Longitud:</b> <span id="byral-coords-txt">-17.3935°, -66.1570°</span></div>
            <div>📊 <b>Magnitud / Histórico:</b> <span id="byral-mag-txt">0.0 mm/h · Base Histórica GAMC</span></div>
        </div>

        <div style="margin-top:9px; border-top:1px solid rgba(255,255,255,0.12); padding-top:9px;">
            <div style="font-size:11px; font-weight:700; color:#94a3b8; margin-bottom:5px; text-transform:uppercase;">Asistente IA (Internet + Tiempo Real + GAMC)</div>
            <div id="byral-ai-messages" style="height:125px; overflow-y:auto; background:rgba(15,23,42,0.9); border:1px solid rgba(255,255,255,0.12); border-radius:8px; padding:8px; margin-bottom:7px; line-height:1.45; color:#e2e8f0;">
                IA conectada. Consulta sobre lluvias torrenciales hoy, datos históricos GAMC o cualquier tema general.
            </div>
            <div style="display:flex; gap:6px;">
                <input id="byral-ai-prompt" type="text" placeholder="Escribe tu pregunta a la IA..." onkeydown="if(event.key==='Enter') byralAskAI()" style="flex:1; background:#1e293b; border:1px solid #475569; color:#fff; padding:7px 9px; border-radius:6px; font-size:12px; outline:none;">
                <button onclick="byralAskAI()" style="background:#2563eb; color:#fff; border:none; padding:7px 12px; border-radius:6px; font-weight:700; cursor:pointer;">Enviar</button>
            </div>
        </div>
    </div>
</div>

<script>
let byralCurLat = -17.3935;
let byralCurLon = -66.1570;
let byralClimaResumen = "Sincronizando...";
let byralProbResumen = "48%";

async function byralUpdateRealtime(lat = byralCurLat, lon = byralCurLon) {
    try {
        const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=precipitation,rain,temperature_2m,wind_speed_10m&hourly=precipitation_probability,precipitation&timezone=America%2FLa_Paz`;
        const resp = await fetch(url);
        const data = await resp.json();

        const lluviaAhora = data.current?.precipitation ?? 0;
        const tempAhora = data.current?.temperature_2m ?? 22;
        const probHora = data.hourly?.precipitation_probability?.[0] ?? 0;
        const lluviaProx = data.hourly?.precipitation?.[0] ?? 0;

        const magnitudMm = Math.max(lluviaAhora, lluviaProx);
        const baseHistorica = (116 / 240) * 100;
        const factorIntensidad = Math.min((magnitudMm / 15.0) * 100, 100);
        const probFinal = Math.round((probHora * 0.45) + (factorIntensidad * 0.25) + (baseHistorica * 0.30));
        const alertaTorrencial = magnitudMm >= 10.0 || probHora >= 75;

        byralProbResumen = probFinal + "%";
        byralClimaResumen = alertaTorrencial
            ? `⚠️ ALERTA: Lluvia Torrencial probable (${magnitudMm} mm/h · ${tempAhora}°C)`
            : `✅ Sin lluvia torrencial (${magnitudMm} mm/h · Prob. lluvia: ${probHora}% · ${tempAhora}°C)`;

        document.getElementById("byral-prob-num").innerText = byralProbResumen;
        document.getElementById("byral-rain-box").innerText = byralClimaResumen;
        document.getElementById("byral-coords-txt").innerText = `Lat: ${lat.toFixed(4)}° | Lon: ${lon.toFixed(4)}°`;
        document.getElementById("byral-mag-txt").innerText = `Magnitud: ${magnitudMm} mm/h · Base GAMC intacta`;
    } catch (err) {
        document.getElementById("byral-rain-box").innerText = "Error obteniendo datos meteorológicos en vivo.";
    }
}

async function byralAskAI() {
    const input = document.getElementById("byral-ai-prompt");
    const box = document.getElementById("byral-ai-messages");
    const pregunta = input.value.trim();
    if (!pregunta) return;

    input.value = "";
    box.innerHTML += `<div style="margin-top:6px; color:#38bdf8;"><b>Tú:</b> ${pregunta}</div>`;
    const msgId = "ai-msg-" + Date.now();
    box.innerHTML += `<div id="${msgId}" style="margin-top:4px; color:#94a3b8;"><i>Consultando internet, clima en vivo e historial GAMC...</i></div>`;
    box.scrollTop = box.scrollHeight;

    const contextoSistema = `Eres el Asistente IA oficial de BYRAL Sentinela en Cochabamba, Bolivia. Responde cualquier pregunta general o técnica como una IA completa y usa estos datos reales e históricos cuando aplique: Coordenadas=(Lat ${byralCurLat.toFixed(4)}, Lon ${byralCurLon.toFixed(4)}), Estado climático en tiempo real="${byralClimaResumen}", Probabilidad de ocurrencia="${byralProbResumen}", Base histórica GAMC=240 emergencias (116 críticas, 103 altas, 21 medias en Distrito 9 Zona Sur, La Maica Cuenca Baja, Sacaba Maylanco, Cercado Eje Río Rocha y Tiquipaya D13).`;

    try {
        const res = await fetch("https://text.pollinations.ai/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                messages: [
                    { role: "system", content: contextoSistema },
                    { role: "user", content: pregunta }
                ],
                model: "openai"
            })
        });
        if (!res.ok) throw new Error("Fallo POST");
        const texto = await res.text();
        document.getElementById(msgId).innerHTML = `<b>IA:</b> ${texto}`;
    } catch (e) {
        try {
            const resGet = await fetch(`https://text.pollinations.ai/${encodeURIComponent(contextoSistema + " Pregunta: " + pregunta)}`);
            const textoGet = await resGet.text();
            document.getElementById(msgId).innerHTML = `<b>IA:</b> ${textoGet}`;
        } catch (e2) {
            document.getElementById(msgId).innerHTML = `<b>IA:</b> En Lat ${byralCurLat.toFixed(4)}, Lon ${byralCurLon.toFixed(4)} el estado actual es "${byralClimaResumen}" con probabilidad ${byralProbResumen} según los registros históricos del GAMC.`;
        }
    }
    box.scrollTop = box.scrollHeight;
}

window.addEventListener("load", () => {
    byralUpdateRealtime();
    setTimeout(() => {
        if (typeof map !== "undefined" && map.on) {
            map.on("click", (e) => {
                byralCurLat = e.latlng.lat;
                byralCurLon = e.latlng.lng;
                byralUpdateRealtime(byralCurLat, byralCurLon);
            });
        }
    }, 1500);
});
</script>
"""

if '<meta name="viewport"' not in html and "<head>" in html:
    html = html.replace("<head>", '<head>\n<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">')

if "</body>" in html:
    html = html.replace("</body>", parche_ui + "\n</body>")
else:
    html += parche_ui

with open(ruta, "w", encoding="utf-8") as f:
    f.write(html)

print("EXITO: Solo se actualizó publicar_seguro\\index.html (respaldo guardado en backup_index.html).")
