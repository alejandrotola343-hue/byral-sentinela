const BASEMAP_LAYERS = {};
const BASEMAP_LABELS = {
  satellite: '\uD83D\uDEF0 Satelital',
  relief: '\u26F0 Relieve 3D',
  topo: '\uD83D\uDDFA Topogr\u00E1fico',
  streets: '\uD83D\uDEE3 Calles'
};

function createBasemapGroup(type) {
  if (!window.L) return null;
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
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxZoom: 18 }),
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}', { maxZoom: 18, opacity: 0.85 })
  ]);
}

function toggleBasemapMenu(target, ev) {
  if (ev) ev.stopPropagation();
  const menu = document.getElementById(target + '-bm-menu');
  if (menu) menu.classList.toggle('open');
}

document.addEventListener('click', () => {
  document.querySelectorAll('.bm-dropdown-menu.open').forEach(m => m.classList.remove('open'));
});

function setBasemap(target, type, btn) {
  const mapObj = target === 'citizen' ? citizenMap : adminMap;
  if (!mapObj || !window.L) return;
  const menu = document.getElementById(target + '-bm-menu');
  if (menu) {
    menu.querySelectorAll('.bm-opt').forEach(b => b.classList.remove('active'));
    menu.classList.remove('open');
  }
  if (btn) btn.classList.add('active');
  const lbl = document.getElementById(target + '-bm-current');
  if (lbl) lbl.innerText = BASEMAP_LABELS[type] || '\uD83D\uDEF0 Satelital';

  if (BASEMAP_LAYERS[target]) mapObj.removeLayer(BASEMAP_LAYERS[target]);
  const grp = createBasemapGroup(type).addTo(mapObj);
  grp.eachLayer(l => { if (l.bringToBack) l.bringToBack(); });
  BASEMAP_LAYERS[target] = grp;
  if (target === 'admin') reordenarCapasAdmin();
}

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
  document.getElementById('env-tag').innerText = ' \u00B7 Ciudadano';
  if (!citizenMap) initCitizenMap();
  if (citizenMap) setTimeout(() => citizenMap.invalidateSize(), 180);
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
    document.getElementById('admin-app').style.display = 'block';
    document.getElementById('btn-open-admin').style.display = 'none';
    document.getElementById('btn-exit-admin').style.display = 'inline-block';
    document.getElementById('env-tag').innerText = ' \u00B7 Desarrollador';
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

const ESTACIONES_CBBA = [
  { nombre: 'Cercado Centro / R\u00EDo Rocha', lat: -17.3935, lng: -66.1570 },
  { nombre: 'Zona Norte / Tiquipaya', lat: -17.3380, lng: -66.2150 },
  { nombre: 'Zona Sur / Distrito 9', lat: -17.4680, lng: -66.1540 },
  { nombre: 'La Maica / Cuenca Baja', lat: -17.4325, lng: -66.1985 },
  { nombre: 'Sacaba / Este', lat: -17.4040, lng: -66.0410 },
  { nombre: 'Quillacollo / Oeste', lat: -17.3920, lng: -66.2780 }
];

let liveWeatherData = ESTACIONES_CBBA.map(est => ({
  ...est, rain: 0, rainProb: 18, temp: 20, hum: 44, rad: 680, soil: 32, condicion: 'Estable', esSequia: false
}));
let selectedReportCoords = { lat: -17.3935, lng: -66.1570 };
let citizenMap, citizenMarkersLayer;
let liveReports = JSON.parse(localStorage.getItem('byral_realtime_reports_v9') || 'null') || [
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
function guardarReportes() { localStorage.setItem('byral_realtime_reports_v9', JSON.stringify(liveReports)); }

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
      const soil = soilArr[horaIdx] !== undefined ? soilArr[horaIdx] : 0.18;
      const rainProb = probArr[horaIdx] !== undefined ? probArr[horaIdx] : 15;
      const rain = +(cur.precipitation ?? cur.rain ?? 0);
      const temp = +(cur.temperature_2m ?? 20);
      const hum = +(cur.relative_humidity_2m ?? 45);
      const rad = +(cur.shortwave_radiation ?? 0);
      let condicion = 'Estable', esSequia = false;
      if (rain > 2.5) condicion = 'Lluvia Fuerte';
      else if (rain > 0) condicion = 'Lluvia Activa';
      else if (soil < 0.16 && hum < 42) { condicion = 'Sequ\u00EDa / Suelo Seco'; esSequia = true; }
      else if (soil < 0.21) { condicion = 'D\u00E9ficit H\u00EDdrico'; esSequia = true; }
      return { ...est, rain, rainProb, temp, hum, rad, soil: +(soil * 100).toFixed(0), condicion, esSequia };
    });
  } catch (e) {}
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
  document.getElementById('top-drought').innerText = zonasLluvia.length > 0 ? '\uD83D\uDCA7 Lluvia' : `\uD83C\uDFDC Suelo ${minSoil}%`;
  document.getElementById('top-rad').innerText = '\u2600 ' + centro.rad + ' W/m\u00B2';

  let txt = zonasLluvia.length > 0
    ? `\uD83C\uDF27 Lluvia en <strong>${zonasLluvia.map(z => z.nombre).join(', ')}</strong>`
    : (zonasSequia.length > 0
      ? `\uD83C\uDFDC Suelo seco (<strong>${minSoil}%</strong>) en ${zonasSequia.slice(0, 2).map(z => z.nombre).join(', ')}`
      : `\u26C5 Clima estable \u00B7 ${centro.temp}\u00B0C`);
  if (liveReports.length > 0) txt += ` &nbsp;|&nbsp; \uD83D\uDEA8 <strong>${liveReports.length}</strong> reporte(s) activo(s)`;
  document.getElementById('live-narrative').innerHTML = txt;

  renderMapaCiudadano();
  renderListaPuntosActivos();
}

function initCitizenMap() {
  if (!window.L) return;
  citizenMap = L.map('citizen-map', { zoomControl: false }).setView([-17.3935, -66.1570], 12);
  L.control.zoom({ position: 'bottomright' }).addTo(citizenMap);
  const grp = createBasemapGroup('satellite').addTo(citizenMap);
  grp.eachLayer(l => { if (l.bringToBack) l.bringToBack(); });
  BASEMAP_LAYERS['citizen'] = grp;
  citizenMarkersLayer = L.layerGroup().addTo(citizenMap);
  citizenMap.on('click', (e) => {
    selectedReportCoords = { lat: +e.latlng.lat.toFixed(5), lng: +e.latlng.lng.toFixed(5) };
    document.getElementById('c-coords-lbl').innerText = `\uD83D\uDCCD ${selectedReportCoords.lat}, ${selectedReportCoords.lng}`;
    L.popup().setLatLng(e.latlng).setContent(`<strong>\uD83D\uDCCD Punto fijado</strong><br/>${selectedReportCoords.lat}, ${selectedReportCoords.lng}`).openOn(citizenMap);
  });
}

function renderMapaCiudadano() {
  if (!citizenMap || !citizenMarkersLayer || !window.L) return;
  citizenMarkersLayer.clearLayers();
  liveWeatherData.forEach(w => {
    const color = w.rain > 0 ? '#67d5e8' : (w.esSequia ? '#e5b567' : '#4cc38a');
    L.circleMarker([w.lat, w.lng], { radius: w.rain > 0 ? 11 : 8, color: '#fff', fillColor: color, fillOpacity: 0.88, weight: 2 })
      .addTo(citizenMarkersLayer)
      .bindPopup(`<strong>\uD83D\uDCE1 ${w.nombre}</strong><br/>${w.condicion} \u00B7 ${w.rain} mm/h \u00B7 Suelo ${w.soil}%`);
  });
  liveReports.forEach(rep => {
    L.circleMarker([rep.lat, rep.lng], { radius: 9, color: '#fff', fillColor: '#e06c75', fillOpacity: 0.95, weight: 2 })
      .addTo(citizenMarkersLayer)
      .bindPopup(`<strong style="color:#e06c75;">\uD83D\uDEA8 ${rep.tipo}</strong><br/>${rep.lugar}<br/>${rep.descripcion}`);
  });
}

function renderListaPuntosActivos() {
  const accHtml = liveReports.map(r => `
    <div class="incident-item" onclick="if(citizenMap) citizenMap.flyTo([${r.lat}, ${r.lng}], 15)">
      <div style="display:flex;justify-content:space-between;"><strong style="color:var(--coral);">\uD83D\uDEA8 ${r.tipo}</strong><span style="font-size:10px;color:var(--muted);">${r.fecha}</span></div>
      <div style="color:var(--text);margin-top:2px;">\uD83D\uDCCD ${r.lugar}</div>
    </div>
  `).join('');
  const climHtml = liveWeatherData.map(w => `
    <div class="incident-item" onclick="if(citizenMap) citizenMap.flyTo([${w.lat}, ${w.lng}], 14)">
      <div style="display:flex;justify-content:space-between;"><strong style="color:${w.rain > 0 ? 'var(--accent)' : 'var(--gold)'};">${w.rain > 0 ? '\uD83C\uDF27' : '\uD83C\uDFDC'} ${w.nombre}</strong><span style="font-family:Consolas,monospace;font-size:11px;">${w.rain} mm/h \u00B7 ${w.soil}%</span></div>
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
  alert('Reporte ' + nuevo.id + ' publicado.');
}

function enviarIACiudadano() {
  const inp = document.getElementById('citizen-ai-input');
  const q = inp.value.trim();
  if (!q) return;
  inp.value = '';
  const chat = document.getElementById('citizen-ai-chat');
  chat.innerHTML += `<div class="msg-usr">${q}</div>`;
  const maxRain = Math.max(...liveWeatherData.map(w => w.rain));
  const minSoil = Math.min(...liveWeatherData.map(w => w.soil));
  const resp = `Lluvia m\u00E1x. <strong>${maxRain} mm/h</strong> \u00B7 Suelo <strong>${minSoil}%</strong> \u00B7 <strong>${liveReports.length}</strong> reporte(s) activos.`;
  chat.innerHTML += `<div class="msg-ai"><strong>IA:</strong> ${resp}</div>`;
  chat.scrollTop = chat.scrollHeight;
}

/* =========================================================
   CONSOLA DESARROLLADOR: FILTRO POR NIVEL DE DESASTRE
   Y EXPEDIENTE COMPLETO POR DISTRITO / REGISTRO GAMC
   ========================================================= */
let adminMap;
let adminDataLoaded = false;
const adminVectorGroups = {};
let emergencyMarkerEntries = [];
let allGamcRecords = [];
let historicalStats = { emergencias: 0, cuencas: 0, drenaje: 0, distritos: 0, porZona: {} };
let activeSeverityFilter = 'TODOS';
let activeGamcCategoryFilter = 'TODOS';
let expandedGamcRecordId = null;

const COLORES_UH7 = {
  '4669881': '#f5d782',
  '4669882': '#f6c5ce',
  '4669883': '#f7c59f',
  '4669884': '#d6c3b3',
  '4669885': '#f3e59a',
  '4669886': '#f7cf9e',
  '4669887': '#f5b8ad',
  '4669888': '#cbb9b0',
  '4669889': '#f6d496'
};
const PALETA_UH7_FALLBACK = ['#d6c3b3', '#f7cf9e', '#f3e59a', '#f5b8ad', '#f7c59f', '#f6d496', '#f6c5ce', '#cbb9b0', '#f5d782'];

// Clasificador automatico de Nivel de Desastre (CRITICO, ALTO, MEDIO, BAJO)
function clasificarNivelDesastre(texto) {
  const t = String(texto || '').toLowerCase();
  if (/(desborde|inund|colapso|socavamiento|deslizamiento|herid|grave|derrumbe|torrentera)/.test(t)) return 'CRITICO';
  if (/(arbol|árbol|tapando|corte de cable|media tensi|rotura|muro|choque|colisi|puente)/.test(t)) return 'ALTO';
  if (/(obstrucci|sumidero|sedimento|anegamiento|poste|fuga|bache)/.test(t)) return 'MEDIO';
  return 'BAJO';
}

function getSeverityBadge(sev) {
  if (sev === 'CRITICO') return '<span class="badge b-crit">CR&Iacute;TICO</span>';
  if (sev === 'ALTO') return '<span class="badge b-warn">ALTO</span>';
  if (sev === 'MEDIO') return '<span class="badge b-live">MEDIO</span>';
  return '<span class="badge b-low">BAJO</span>';
}

function getSeverityColor(sev) {
  if (sev === 'CRITICO') return '#f43f5e';
  if (sev === 'ALTO') return '#f59e0b';
  if (sev === 'MEDIO') return '#22d3ee';
  return '#34d399';
}

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
  return [
    flat.reduce((a, b) => a + b[0], 0) / flat.length,
    flat.reduce((a, b) => a + b[1], 0) / flat.length
  ];
}

// Ray-casting point-in-polygon para vincular emergencias/quejas dentro de cada Distrito
function pointInPolygon(pt, geom) {
  if (!pt || !geom || !geom.coordinates) return false;
  const x = pt[0], y = pt[1];
  const polys = geom.type === 'Polygon' ? [geom.coordinates] : (geom.type === 'MultiPolygon' ? geom.coordinates : []);
  for (const poly of polys) {
    const ring = poly[0] || [];
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const xi = ring[i][0], yi = ring[i][1];
      const xj = ring[j][0], yj = ring[j][1];
      const intersect = ((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / ((yj - yi) || 1e-12) + xi);
      if (intersect) inside = !inside;
    }
    if (inside) return true;
  }
  return false;
}

function reordenarCapasAdmin() {
  if (!adminMap) return;
  if (BASEMAP_LAYERS['admin']) {
    BASEMAP_LAYERS['admin'].eachLayer(l => { if (l.bringToBack) l.bringToBack(); });
  }
  ['cuencas', 'distritos', 'drenaje', 'emergencias', 'live'].forEach(k => {
    if (adminVectorGroups[k] && adminMap.hasLayer(adminVectorGroups[k]) && adminVectorGroups[k].bringToFront) {
      adminVectorGroups[k].bringToFront();
    }
  });
}

function iniciarConsolaAdminTotal() {
  const datasets = window.BYRAL_HISTORICAL_DATA || { emergencias: [], cuencas: [], drenaje: [], distritos: [] };

  if (!adminDataLoaded) {
    allGamcRecords = [];
    historicalStats = { emergencias: 0, cuencas: 0, drenaje: 0, distritos: 0, porZona: {} };
    let seqId = 1;

    for (const cat of ['distritos', 'emergencias', 'cuencas', 'drenaje']) {
      (datasets[cat] || []).forEach(feature => {
        historicalStats[cat]++;
        const p = feature.properties || {};
        const desc = p['Descripción'] || p.Descripcion || p['Nombre uh'] || p.Nombre_uh || p.Distrito || p['Clasificación'] || ('Registro ' + cat);
        const sev = cat === 'emergencias' ? clasificarNivelDesastre(desc) : 'MEDIO';
        if (cat === 'emergencias') {
          const z = p.Comuna || p.distrito || p.Distrito || p['Unidad Responsable'] || 'Cercado';
          historicalStats.porZona[z] = (historicalStats.porZona[z] || 0) + 1;
        }
        allGamcRecords.push({
          uid: 'GAMC-' + (seqId++),
          capa: cat.toUpperCase(),
          severidad: sev,
          numero: p.Numero || '',
          fecha: p.Fecha || '',
          denunciante: p.Denunciante || '',
          carnet: p.Carnet || p.CI || '',
          celular: p.Celular || p.Telefono || '',
          unidadRegistro: p['Unidad Registro'] || '',
          unidadResponsable: p['Unidad Responsable'] || '',
          titulo: desc,
          zona: p.Comuna || p.Distrito || p['Nivel 7'] || p.Nivel_7 || p['Unidad Responsable'] || 'Cochabamba',
          estado: p.Estado || '',
          coords: getFeatureCenter(feature.geometry),
          geometry: feature.geometry,
          rawProps: p
        });
      });
    }
    adminDataLoaded = true;
  }

  // Actualizar contadores de Nivel de Desastre
  const emgs = allGamcRecords.filter(r => r.capa === 'EMERGENCIAS');
  document.getElementById('sev-cnt-todos').innerText = emgs.length;
  document.getElementById('sev-cnt-crit').innerText = emgs.filter(r => r.severidad === 'CRITICO').length;
  document.getElementById('sev-cnt-alto').innerText = emgs.filter(r => r.severidad === 'ALTO').length;
  document.getElementById('sev-cnt-medio').innerText = emgs.filter(r => r.severidad === 'MEDIO').length;
  document.getElementById('sev-cnt-bajo').innerText = emgs.filter(r => r.severidad === 'BAJO').length;

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
    adminMap = L.map('admin-map', { zoomControl: false, preferCanvas: true }).setView([-17.3935, -66.1570], 12);
    L.control.zoom({ position: 'bottomright' }).addTo(adminMap);
    const bm = createBasemapGroup('satellite').addTo(adminMap);
    bm.eachLayer(l => { if (l.bringToBack) l.bringToBack(); });
    BASEMAP_LAYERS['admin'] = bm;

    ['cuencas', 'distritos', 'drenaje', 'emergencias', 'live'].forEach(k => {
      adminVectorGroups[k] = L.featureGroup().addTo(adminMap);
    });

    emergencyMarkerEntries = [];

    for (const cat of ['cuencas', 'distritos', 'drenaje', 'emergencias']) {
      const feats = datasets[cat] || [];
      feats.forEach((feature, idx) => {
        try {
          const p = feature.properties || {};
          const desc = p['Descripción'] || p.Descripcion || '';
          const sev = cat === 'emergencias' ? clasificarNivelDesastre(desc) : 'MEDIO';
          const n7 = String(p['Nivel 7'] || p.Nivel_7 || '');
          const uhColor = COLORES_UH7[n7] || PALETA_UH7_FALLBACK[idx % PALETA_UH7_FALLBACK.length];

          const layer = L.geoJSON(feature, {
            style: () => {
              if (cat === 'cuencas') {
                return { color: '#5c5346', weight: 1.4, opacity: 0.85, fillColor: uhColor, fillOpacity: 0.30 };
              }
              if (cat === 'distritos') {
                return { color: '#a78bfa', weight: 1.8, opacity: 0.92, fillColor: '#a78bfa', fillOpacity: 0.05 };
              }
              if (cat === 'drenaje') {
                return { color: '#1d9bf0', weight: 1.6, opacity: 0.94, lineCap: 'round', lineJoin: 'round' };
              }
              return { color: '#22d3ee', weight: 1.5 };
            },
            pointToLayer: (f, latlng) => {
              if (cat === 'cuencas') {
                return L.circleMarker(latlng, { radius: 7, color: '#5c5346', weight: 1.5, fillColor: uhColor, fillOpacity: 0.88 });
              }
              if (cat === 'distritos') {
                return L.circleMarker(latlng, { radius: 6, color: '#a78bfa', weight: 2, fillColor: '#ede9fe', fillOpacity: 0.65 });
              }
              if (cat === 'drenaje') {
                return L.circleMarker(latlng, { radius: 5, color: '#ffffff', weight: 1.2, fillColor: '#1d9bf0', fillOpacity: 0.92 });
              }
              return L.circleMarker(latlng, {
                radius: sev === 'CRITICO' ? 6.5 : 5.2,
                color: '#ffffff',
                weight: 1.4,
                fillColor: getSeverityColor(sev),
                fillOpacity: 0.94
              });
            },
            onEachFeature: (f, lyr) => {
              const fp = f.properties || {};
              const titulo = fp['Nombre uh'] || fp.Nombre_uh
                ? `${fp['Nombre uh'] || fp.Nombre_uh} (UH ${fp['Nivel 7'] || fp.Nivel_7 || ''})`
                : (fp.Distrito ? `${fp.Distrito} \u00B7 ${fp.Comuna || ''}` : (fp.Numero ? `Caso GAMC #${fp.Numero} [${sev}]` : (fp['Clasificación'] || `${cat.toUpperCase()} #${idx + 1}`)));

              if (cat === 'distritos') {
                lyr.on('click', () => {
                  const rec = allGamcRecords.find(r => r.capa === 'DISTRITOS' && r.titulo === fp.Distrito && r.zona === (fp.Comuna || fp.Distrito));
                  if (rec) {
                    const tabBtn = document.querySelectorAll('.ar-tab')[2];
                    if (tabBtn) cambiarTabAdminRight('gamc', tabBtn);
                    expandedGamcRecordId = rec.uid;
                    buscarEnDatosGAMC();
                  }
                });
              }

              if (cat === 'cuencas' || cat === 'distritos') {
                lyr.bindTooltip(`<strong>${titulo}</strong>`, { sticky: true, direction: 'center' });
                lyr.on('mouseover', function () {
                  if (this.setStyle) this.setStyle({ fillOpacity: cat === 'cuencas' ? 0.46 : 0.18, weight: 2.5 });
                });
                lyr.on('mouseout', function () {
                  if (this.setStyle) this.setStyle({ fillOpacity: cat === 'cuencas' ? 0.30 : 0.05, weight: cat === 'cuencas' ? 1.4 : 1.8 });
                });
              }

              const rows = Object.entries(fp)
                .filter(([k, v]) => !k.startsWith('_') && v !== null && String(v).trim() !== '')
                .map(([k, v]) => `<div><b>${k}:</b> ${String(v).replace(/&NBSP;/gi, ' ')}</div>`).join('');
              lyr.bindPopup(`<div style="font-size:11.5px;line-height:1.45;max-width:295px;"><strong style="color:var(--accent);">${titulo}</strong>${rows || '<div>Registro Oficial GAMC</div>'}</div>`);
            }
          });

          if (cat === 'emergencias') {
            emergencyMarkerEntries.push({ layer, severidad: sev });
          }
          layer.addTo(adminVectorGroups[cat]);
        } catch (err) {}
      });
    }
    reordenarCapasAdmin();
    const boundsGrp = adminVectorGroups.cuencas.getLayers().length > 0 ? adminVectorGroups.cuencas : adminVectorGroups.emergencias;
    if (boundsGrp && boundsGrp.getBounds && boundsGrp.getBounds().isValid()) {
      adminMap.fitBounds(boundsGrp.getBounds(), { padding: [20, 20] });
    }
  }

  if (adminMap) setTimeout(() => adminMap.invalidateSize(), 180);

  try { renderLiveMarkersInAdmin(); } catch (e) {}
  try { recalcularMotorAdmin(); } catch (e) {}
  try { renderBandejaIA(); } catch (e) {}
  try { buscarEnDatosGAMC(); } catch (e) {}
}

function filtrarPorNivelDesastre(nivel, btn) {
  activeSeverityFilter = nivel;
  document.querySelectorAll('#severity-filter-bar .sev-pill').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');

  // Filtrar marcadores en el mapa en tiempo real sin eliminar los datos subyacentes
  if (adminVectorGroups['emergencias']) {
    adminVectorGroups['emergencias'].clearLayers();
    let visibles = 0;
    emergencyMarkerEntries.forEach(entry => {
      if (nivel === 'TODOS' || entry.severidad === nivel) {
        entry.layer.addTo(adminVectorGroups['emergencias']);
        visibles++;
      }
    });
    document.getElementById('cnt-emerg').innerText = visibles;
  }

  renderLiveMarkersInAdmin();
  renderBandejaIA();
  buscarEnDatosGAMC();
}

function filtrarCategoriaGAMC(cat, btn) {
  activeGamcCategoryFilter = cat;
  document.querySelectorAll('#ar-pane-gamc .sev-pill').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  buscarEnDatosGAMC();
}

function toggleDetalleGAMC(uid) {
  expandedGamcRecordId = (expandedGamcRecordId === uid) ? null : uid;
  buscarEnDatosGAMC();
}

function renderLiveMarkersInAdmin() {
  if (!adminVectorGroups['live'] || !window.L) return;
  adminVectorGroups['live'].clearLayers();
  liveReports.forEach(rep => {
    const sev = clasificarNivelDesastre(`${rep.tipo} ${rep.descripcion}`);
    if (activeSeverityFilter !== 'TODOS' && sev !== activeSeverityFilter) return;

    L.circleMarker([rep.lat, rep.lng], { radius: 8, color: '#ffffff', weight: 1.8, fillColor: '#f43f5e', fillOpacity: 0.96 })
      .addTo(adminVectorGroups['live'])
      .bindPopup(`
        <div style="font-size:11.5px;line-height:1.45;max-width:295px;">
          <strong style="color:#f43f5e;">\uD83D\uDEA8 REPORTE EN VIVO ${rep.id} [${sev}]</strong><br/>
          <b>Fecha/Hora:</b> ${rep.fecha}<br/>
          <b>Denunciante:</b> ${rep.nombre}<br/>
          <b>Carnet (CI):</b> ${rep.carnet}<br/>
          <b>Celular / Tel:</b> ${rep.telefono}<br/>
          <b>Tipo:</b> ${rep.tipo}<br/>
          <b>Lugar:</b> ${rep.lugar} (${rep.lat}, ${rep.lng})<br/>
          <b>Queja / Descripci\u00F3n:</b> ${rep.descripcion}<br/>
          <b>Estado:</b> ${rep.estado}
        </div>
      `);
  });
  reordenarCapasAdmin();
}

function toggleAdminGroup(key, visible) {
  if (!adminMap || !adminVectorGroups[key]) return;
  visible ? adminVectorGroups[key].addTo(adminMap) : adminMap.removeLayer(adminVectorGroups[key]);
  reordenarCapasAdmin();
}

function zoomToLayer(key) {
  const grp = adminVectorGroups[key];
  if (adminMap && grp && grp.getBounds && grp.getBounds().isValid()) adminMap.fitBounds(grp.getBounds(), { padding: [24, 24] });
}

function recalcularMotorAdmin() {
  const listEl = document.getElementById('probability-ranking-list');
  if (!listEl) return;
  const wH = +(document.getElementById('w-hist')?.value || 45);
  const wR = +(document.getElementById('w-rain')?.value || 35);
  const wS = +(document.getElementById('w-soil')?.value || 20);
  document.getElementById('w-hist-val').innerText = wH + ' %';
  document.getElementById('w-rain-val').innerText = wR + ' %';
  document.getElementById('w-soil-val').innerText = wS + ' %';

  const sumW = Math.max(1, wH + wR + wS);
  const nH = wH / sumW, nR = wR / sumW, nS = wS / sumW;

  const zonas = [
    { nombre: 'Distrito 9 \u00B7 Zona Sur', histBase: Math.max(28, historicalStats.porZona['Distrito 9'] || 34), meteo: liveWeatherData[2] || liveWeatherData[0] },
    { nombre: 'La Maica \u00B7 Cuenca Baja', histBase: Math.max(24, historicalStats.porZona['Comuna Itocta'] || 29), meteo: liveWeatherData[3] || liveWeatherData[0] },
    { nombre: 'Zona Norte \u00B7 Tiquipaya (D13)', histBase: 22, meteo: liveWeatherData[1] || liveWeatherData[0] },
    { nombre: 'Cercado \u00B7 Eje R\u00EDo Rocha (UH 4669885)', histBase: Math.max(19, historicalStats.porZona['Comuna Adela Zamudio'] || 25), meteo: liveWeatherData[0] },
    { nombre: 'Sacaba \u00B7 Maylanco', histBase: 18, meteo: liveWeatherData[4] || liveWeatherData[0] }
  ];

  const totalHist = Math.max(1, historicalStats.emergencias);
  const ranking = zonas.map(z => {
    const scoreH = Math.min(1, (z.histBase / totalHist) * 3.2 + 0.25);
    const scoreR = Math.min(1, Math.max(z.meteo.rain / 12, (z.meteo.rainProb || 0) / 100));
    const scoreS = z.meteo.esSequia ? Math.min(1, (26 - z.meteo.soil) / 20) : 0.15;
    const pct = Math.min(98, Math.round((scoreH * nH + scoreR * nR + scoreS * nS) * 100));
    const pLluvia = Math.round(z.meteo.rainProb || 0);
    const amenaza = z.meteo.rain > 0 ? 'Inundaci\u00F3n' : (z.meteo.esSequia ? 'Sequ\u00EDa' : 'Susceptibilidad');
    return { ...z, pct, pLluvia, amenaza };
  }).sort((a, b) => b.pct - a.pct);

  listEl.innerHTML = ranking.map(r => {
    const col = r.pct >= 65 ? '#fb7185' : (r.pct >= 40 ? '#fbbf24' : '#38bdf8');
    return `
      <div class="prob-row" onclick="if(adminMap) adminMap.flyTo([${r.meteo.lat}, ${r.meteo.lng}], 14)">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <strong style="color:var(--text);">${r.nombre}</strong>
          <span style="font-family:Consolas,monospace;font-weight:700;color:${col};font-size:13px;">${r.pct}%</span>
        </div>
        <div style="font-size:10.5px;color:var(--muted);margin-top:3px;">
          ${r.amenaza} &middot; GPM ${r.pLluvia}% &middot; Suelo ${r.meteo.soil}%
        </div>
        <div class="prob-bar-bg"><div class="prob-bar-fill" style="width:${r.pct}%;background:${col};"></div></div>
      </div>
    `;
  }).join('');
}

function cambiarEstadoReporteAdmin(id) {
  const idx = liveReports.findIndex(r => r.id === id);
  if (idx === -1) return;
  const seq = ['Nuevo', 'Despachado', 'Atendido'];
  liveReports[idx].estado = seq[(seq.indexOf(liveReports[idx].estado) + 1) % seq.length];
  guardarReportes();
  renderBandejaIA();
  renderLiveMarkersInAdmin();
}

function renderBandejaIA() {
  const cntEl = document.getElementById('admin-inbox-count');
  const cardsEl = document.getElementById('admin-inbox-cards');
  if (!cardsEl) return;

  const list = liveReports.map(r => ({
    ...r,
    sev: clasificarNivelDesastre(`${r.tipo} ${r.descripcion}`)
  }));
  const filtrados = activeSeverityFilter === 'TODOS' ? list : list.filter(r => r.sev === activeSeverityFilter);
  if (cntEl) cntEl.innerText = filtrados.length;

  cardsEl.innerHTML = filtrados.map(r => `
    <div class="report-admin-item">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <strong style="color:var(--accent);font-family:Consolas,monospace;">${r.id} &middot; ${r.tipo}</strong>
        ${getSeverityBadge(r.sev)}
      </div>
      <div style="font-size:10.5px;color:var(--muted);margin-top:2px;">\uD83D\uDD52 ${r.fecha}</div>
      <div style="margin-top:4px;">\uD83D\uDC64 <strong>Denunciante:</strong> ${r.nombre} &middot; <strong>CI:</strong> ${r.carnet} &middot; <strong>Cel:</strong> ${r.telefono}</div>
      <div>\uD83D\uDCCD <a href="#" style="color:var(--accent);text-decoration:none;" onclick="if(adminMap) adminMap.flyTo([${r.lat}, ${r.lng}], 16);return false;">${r.lugar}</a></div>
      <div style="color:var(--text);margin-top:4px;"><strong>Queja / Molestia:</strong> ${r.descripcion}</div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px;">
        <span style="font-size:10.5px;color:var(--muted);">Estado: <strong style="color:var(--mint);">${r.estado}</strong></span>
        <div style="display:flex;gap:8px;"><button class="zoom-mini" onclick="cambiarEstadoReporteAdmin('${r.id}')">Estado &#8635;</button><button class="zoom-mini" style="color:var(--coral);" onclick="eliminarReporteEnVivo('${r.id}')">Quitar &#10005;</button></div>
      </div>
    </div>
  `).join('') || '<div style="color:var(--muted);padding:12px 0;">Sin reportes en vivo para este nivel de desastre.</div>';
}

// Construye el expediente completo desplegable debajo de cualquier Distrito o Registro GAMC
function renderExpedienteDebajo(rec) {
  const todasEmergencias = allGamcRecords.filter(e => e.capa === 'EMERGENCIAS');

  if (rec.capa === 'DISTRITOS') {
    const distNum = String(rec.titulo || '').replace(/\D+/g, '');
    const relacionadas = todasEmergencias.filter(em => {
      if (activeSeverityFilter !== 'TODOS' && em.severidad !== activeSeverityFilter) return false;
      const dentroPoligono = em.coords && rec.geometry && pointInPolygon(em.coords, rec.geometry);
      const mencDistrito = distNum && new RegExp(`\\b(distrito|d)\\s*0?${distNum}\\b`, 'i').test(`${em.titulo} ${em.zona}`);
      return dentroPoligono || mencDistrito;
    });

    const enVivoDistrito = liveReports.filter(lr =>
      rec.geometry && pointInPolygon([lr.lng, lr.lat], rec.geometry)
    );

    const listaHtml = relacionadas.map(em => `
      <div class="sub-complaint-line" onclick="event.stopPropagation(); if(adminMap && ${!!em.coords}) adminMap.flyTo([${em.coords ? em.coords[1] : -17.39}, ${em.coords ? em.coords[0] : -66.15}], 16)">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <strong style="color:var(--accent);">#${em.numero || 'S/N'} &middot; ${em.fecha || 'Sin fecha'}</strong>
          ${getSeverityBadge(em.severidad)}
        </div>
        <div>\uD83D\uDC64 <strong>Denunciante:</strong> ${em.denunciante || 'No registrado'} &middot; <strong>CI:</strong> ${em.carnet || 'S/D'} &middot; <strong>Cel:</strong> ${em.celular || 'S/D'}</div>
        <div style="color:#fff;margin-top:2px;"><strong>Queja / Consulta:</strong> ${em.titulo}</div>
        <div style="color:var(--muted);font-size:10.5px;">Unidad: ${em.unidadResponsable || em.zona} &middot; Estado: <strong>${em.estado || 'REGISTRADO'}</strong></div>
      </div>
    `).join('');

    const vivoHtml = enVivoDistrito.map(lr => `
      <div class="sub-complaint-line">
        <div style="display:flex;justify-content:space-between;"><strong style="color:var(--coral);">EN VIVO ${lr.id} &middot; ${lr.fecha}</strong><span class="badge b-crit">HOY</span></div>
        <div>\uD83D\uDC64 <strong>Denunciante:</strong> ${lr.nombre} &middot; <strong>CI:</strong> ${lr.carnet} &middot; <strong>Cel:</strong> ${lr.telefono}</div>
        <div style="color:#fff;"><strong>Queja:</strong> ${lr.descripcion} (${lr.lugar})</div>
      </div>
    `).join('');

    return `
      <div class="gamc-drawer-detail" onclick="event.stopPropagation()">
        <div style="font-weight:700;color:#fff;margin-bottom:6px;">
          EXPEDIENTE DISTRITO ${rec.titulo} (${rec.zona}) &middot; ${relacionadas.length + enVivoDistrito.length} QUEJAS / CONSULTAS ENCONTRADAS
        </div>
        ${vivoHtml}
        ${listaHtml || '<div style="color:var(--muted);">No hay quejas registradas en este distrito para el filtro seleccionado.</div>'}
      </div>
    `;
  }

  // Para Emergencias, Cuencas o Drenaje: mostrar absolutamente todos los atributos sin censura
  const camposCompletos = Object.entries(rec.rawProps || {})
    .filter(([k, v]) => !k.startsWith('_') && v !== null && String(v).trim() !== '')
    .map(([k, v]) => `<div><strong style="color:#cbd5e1;">${k}:</strong> <span style="color:#fff;">${String(v).replace(/&NBSP;/gi, ' ')}</span></div>`)
    .join('');

  return `
    <div class="gamc-drawer-detail" onclick="event.stopPropagation()">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
        <strong style="color:var(--accent);">FICHA COMPLETA DEL REGISTRO</strong>
        ${rec.capa === 'EMERGENCIAS' ? getSeverityBadge(rec.severidad) : ''}
      </div>
      ${camposCompletos}
      ${rec.coords ? `<div style="margin-top:4px;color:var(--muted);font-family:Consolas,monospace;font-size:10.5px;">Coordenadas: ${rec.coords[1]}, ${rec.coords[0]}</div>` : ''}
    </div>
  `;
}

function buscarEnDatosGAMC() {
  const listEl = document.getElementById('admin-gamc-list');
  if (!listEl) return;
  const q = (document.getElementById('admin-search-gamc')?.value || '').toLowerCase();

  const res = allGamcRecords.filter(r => {
    if (activeGamcCategoryFilter !== 'TODOS' && r.capa !== activeGamcCategoryFilter) return false;
    if (r.capa === 'EMERGENCIAS' && activeSeverityFilter !== 'TODOS' && r.severidad !== activeSeverityFilter) return false;
    if (q && !JSON.stringify(r).toLowerCase().includes(q)) return false;
    return true;
  }).slice(0, 140);

  listEl.innerHTML = res.map(r => {
    const isExpanded = expandedGamcRecordId === r.uid;
    const flyCode = r.coords ? `if(adminMap) adminMap.flyTo([${r.coords[1]}, ${r.coords[0]}], 15);` : '';
    const sevTag = r.capa === 'EMERGENCIAS' ? getSeverityBadge(r.severidad) : `<span style="font-size:10px;color:var(--muted);">${r.estado || r.zona}</span>`;
    const metaDen = r.denunciante
      ? `<div style="font-size:11px;color:#cbd5e1;margin-top:2px;">\uD83D\uDC64 <strong>${r.denunciante}</strong> &middot; CI: ${r.carnet || 'S/D'} &middot; Cel: ${r.celular || 'S/D'}</div>`
      : '';

    return `
      <div class="gamc-row-item" onclick="${flyCode} toggleDetalleGAMC('${r.uid}')">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:10.5px;font-weight:700;color:${r.capa === 'DISTRITOS' ? 'var(--purple)' : 'var(--accent)'};">
            ${r.capa}${r.numero ? ' #' + r.numero : ''} ${isExpanded ? '&#9662;' : '&#9656;'}
          </span>
          ${sevTag}
        </div>
        <div style="color:var(--text);font-size:12px;font-weight:600;margin-top:2px;">
          ${r.capa === 'DISTRITOS' ? `${r.titulo} &middot; ${r.zona}` : r.titulo}
        </div>
        ${metaDen}
        ${isExpanded ? renderExpedienteDebajo(r) : ''}
      </div>
    `;
  }).join('') || '<div style="color:var(--muted);padding:12px 0;">Sin coincidencias para este filtro.</div>';
}

window.addEventListener('DOMContentLoaded', () => {
  const d = window.BYRAL_HISTORICAL_DATA || {};
  const total = (d.emergencias?.length || 0) + (d.cuencas?.length || 0) + (d.drenaje?.length || 0) + (d.distritos?.length || 0);
  const el = document.getElementById('db-sync-status');
  if (el) el.innerText = `BASE GAMC: ${total} REGISTROS`;
  cargarTelemetriaSatelital();
});
