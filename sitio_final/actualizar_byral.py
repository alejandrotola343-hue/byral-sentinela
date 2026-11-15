import os

ruta_html = "index.html"
if not os.path.exists(ruta_html):
    print("ERROR: No se encontró index.html en C:\\Users\\Lenovo\\Desktop\\BYRAL\\sitio_final")
    exit()

with open(ruta_html, "r", encoding="utf-8") as f:
    contenido = f.read()

codigo_extra = """
<!-- BYRAL MODULO TIEMPO REAL + TRADUCTOR + IA (PROBLEMAS 2, 3, 4, 5) -->
<div id="google_translate_element" style="position: fixed; top: 10px; right: 14px; z-index: 999999; background: rgba(15,23,42,0.92); padding: 4px 8px; border-radius: 8px; border: 1px solid rgba(56,189,248,0.45);"></div>
<script type="text/javascript">
function googleTranslateElementInit() {
  new google.translate.TranslateElement({pageLanguage: 'es', includedLanguages: 'en,es', layout: google.translate.TranslateElement.InlineLayout.SIMPLE}, 'google_translate_element');
}
</script>
<script type="text/javascript" src="https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit"></script>

<div id="byral-realtime-panel" style="position: fixed; bottom: 14px; right: 14px; z-index: 99999; width: 350px; max-width: 92vw; background: rgba(10, 15, 28, 0.95); border: 1px solid rgba(56, 189, 248, 0.5); border-radius: 12px; padding: 14px; color: #f8fafc; font-family: system-ui, -apple-system, sans-serif; font-size: 12.5px; box-shadow: 0 10px 30px rgba(0,0,0,0.75); backdrop-filter: blur(12px);">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
        <span style="color:#94a3b8; font-weight:700; letter-spacing:0.5px; text-transform:uppercase; font-size:11px;">Probabilidad de Ocurrencia</span>
        <span id="byral-prob-val" style="font-size:20px; font-weight:800; color:#facc15;">--%</span>
    </div>
    <div id="byral-rain-alert" style="color:#38bdf8; font-weight:600; margin-bottom:8px; padding:6px 8px; background:rgba(56,189,248,0.12); border-radius:6px;">
        Sincronizando radar y datos históricos...
    </div>
    <div style="color:#cbd5e1; line-height:1.55; border-top:1px solid rgba(255,255,255,0.12); padding-top:8px; font-size:12px;">
        <div>📍 <strong>Latitud / Longitud:</strong> <span id="byral-latlon">-17.3935°, -66.1570°</span></div>
        <div>📊 <strong>Magnitud / Intensidad:</strong> <span id="byral-mag">0.0 mm/h · Hist. GAMC: 240 eventos</span></div>
    </div>

    <div style="margin-top:10px; border-top:1px solid rgba(255,255,255,0.12); padding-top:10px;">
        <div style="font-size:11px; color:#94a3b8; font-weight:700; margin-bottom:5px; text-transform:uppercase;">Asistente IA (Internet + Tiempo Real + GAMC)</div>
        <div id="byral-ai-chat" style="background:rgba(15,23,42,0.85); border:1px solid rgba(255,255,255,0.12); border-radius:8px; padding:8px; height:120px; overflow-y:auto; margin-bottom:6px; color:#e2e8f0; font-size:12px; line-height:1.45;">
            Listo. Pregúntame sobre lluvias torrenciales, probabilidad por zona, datos históricos GAMC o cualquier consulta general.
        </div>
        <div style="display:flex; gap:6px;">
            <input id="byral-ai-input" type="text" placeholder="Escribe tu pregunta aquí..." onkeydown="if(event.key==='Enter') enviarPreguntaByral()" style="flex:1; background:#1e293b; border:1px solid #475569; color:#fff; padding:7px 9px; border-radius:6px; font-size:12px; outline:none;">
            <button onclick="enviarPreguntaByral()" style="background:#2563eb; color:white; border:none; padding:7px 12px; border-radius:6px; cursor:pointer; font-weight:700; font-size:12px;">Enviar</button>
        </div>
    </div>
</div>

<script>
let selLat = -17.3935;
let selLon = -66.1570;
let ultimoEstadoClima = "Sin datos";
let ultimaProb = "0%";

async function calcularProbabilidadTiempoReal(lat = selLat, lon = selLon) {
    try {
        const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=precipitation,rain,temperature_2m,wind_speed_10m&hourly=precipitation_probability,precipitation&timezone=America%2FLa_Paz`;
        const res = await fetch(url);
        const data = await res.json();

        const lluviaActual = data.current.precipitation ?? 0;
        const tempActual = data.current.temperature_2m ?? 22;
        const probHora = (data.hourly && data.hourly.precipitation_probability) ? data.hourly.precipitation_probability[0] : 0;
        const lluviaProxHora = (data.hourly && data.hourly.precipitation) ? data.hourly.precipitation[0] : 0;

        const recurrenciaHistorica = (116 / 240) * 100;
        const intensidadMax = Math.max(lluviaActual, lluviaProxHora);
        const factorTorrencial = Math.min((intensidadMax / 15.0) * 100, 100);

        const probOcurrencia = Math.round((probHora * 0.45) + (factorTorrencial * 0.25) + (recurrenciaHistorica * 0.30));
        const esTorrencial = intensidadMax >= 10.0 || probHora >= 75;

        ultimaProb = probOcurrencia + "%";
        ultimoEstadoClima = esTorrencial
            ? `⚠️ ALERTA DE LLUVIA TORRENCIAL (${intensidadMax} mm/h · Temp: ${tempActual}°C)`
            : `✅ Sin lluvia torrencial (${intensidadMax} mm/h · Prob. lluvia: ${probHora}% · ${tempActual}°C)`;

        document.getElementById("byral-prob-val").innerText = ultimaProb;
        document.getElementById("byral-rain-alert").innerText = ultimoEstadoClima;
        document.getElementById("byral-latlon").innerText = `${lat.toFixed(4)}°, ${lon.toFixed(4)}°`;
        document.getElementById("byral-mag").innerText = `${intensidadMax} mm/h · Base GAMC: 240 eventos (116 críticos)`;
    } catch (err) {
        document.getElementById("byral-rain-alert").innerText = "Error obteniendo telemetría meteorológica en vivo.";
    }
}

async function enviarPreguntaByral() {
    const input = document.getElementById("byral-ai-input");
    const chat = document.getElementById("byral-ai-chat");
    const pregunta = input.value.trim();
    if (!pregunta) return;

    input.value = "";
    chat.innerHTML += `<div style="margin-top:6px; color:#38bdf8;"><strong>Tú:</strong> ${pregunta}</div>`;
    const idLoading = "ia-load-" + Date.now();
    chat.innerHTML += `<div id="${idLoading}" style="margin-top:4px; color:#94a3b8;"><em>Consultando datos en tiempo real, historial GAMC e internet...</em></div>`;
    chat.scrollTop = chat.scrollHeight;

    const systemPrompt = `Eres el Asistente IA de BYRAL Sentinela (Cochabamba, Bolivia). Responde cualquier pregunta general como una IA completa y también usa estos datos reales e históricos cuando aplique: Coordenadas consultadas=(${selLat.toFixed(4)}, ${selLon.toFixed(4)}), Estado climático actual="${ultimoEstadoClima}", Probabilidad calculada=${ultimaProb}, Historial GAMC=240 emergencias totales (116 críticas, 103 altas, 21 medias) concentradas en Distrito 9 Zona Sur, La Maica Cuenca Baja, Sacaba Maylanco, Cercado Eje Río Rocha y Tiquipaya.`;

    try {
        const res = await fetch("https://text.pollinations.ai/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                messages: [
                    { role: "system", content: systemPrompt },
                    { role: "user", content: pregunta }
                ],
                model: "openai"
            })
        });
        if (!res.ok) throw new Error("Fallo POST");
        const respuesta = await res.text();
        document.getElementById(idLoading).innerHTML = `<strong>IA:</strong> ${respuesta}`;
    } catch (e) {
        try {
            const urlGet = `https://text.pollinations.ai/${encodeURIComponent(systemPrompt + " | Pregunta: " + pregunta)}`;
            const res2 = await fetch(urlGet);
            const respuesta2 = await res2.text();
            document.getElementById(idLoading).innerHTML = `<strong>IA:</strong> ${respuesta2}`;
        } catch (e2) {
            document.getElementById(idLoading).innerHTML = `<strong>IA:</strong> En (${selLat.toFixed(4)}, ${selLon.toFixed(4)}) el estado es ${ultimoEstadoClima} con probabilidad ${ultimaProb} según los 240 eventos históricos del GAMC.`;
        }
    }
    chat.scrollTop = chat.scrollHeight;
}

window.addEventListener("load", () => {
    calcularProbabilidadTiempoReal();
    setTimeout(() => {
        if (typeof map !== "undefined" && map.on) {
            map.on("click", (e) => {
                selLat = e.latlng.lat;
                selLon = e.latlng.lng;
                calcularProbabilidadTiempoReal(selLat, selLon);
            });
        }
    }, 1500);
});
</script>
"""

if "<!-- BYRAL MODULO TIEMPO REAL" in contenido:
    contenido = contenido.split("<!-- BYRAL MODULO TIEMPO REAL")[0] + "\n</body>\n</html>"

if "</body>" in contenido:
    contenido = contenido.replace("</body>", codigo_extra + "\n</body>")
else:
    contenido += codigo_extra

with open(ruta_html, "w", encoding="utf-8") as f:
    f.write(contenido)

print("EXITO: index.html actualizado en sitio_final.")
