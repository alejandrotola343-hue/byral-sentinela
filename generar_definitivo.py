import os, json

OUT_JS = r"C:\Users\Lenovo\Desktop\BYRAL\sitio_final\js\datos_gamc.js"

data = {
  "emergencias": [
    {
      "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [-66.1584, -17.3892]},
      "properties": {"Numero": "4253/2025", "Fecha": "2025/01/08", "Descripción": "ARBOL CAIDO EN ACERA", "Unidad Responsable": "UNIDAD FORESTAL", "Estado": "FINALIZADA"}
    },
    {
      "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [-66.1538, -17.3976]},
      "properties": {"Numero": "6613/2026", "Fecha": "2026/01/07", "Descripción": "ARBOL CAIDO CALLE ARMANDO MENDEZ Y BENJAMIN BLANCO", "Unidad Responsable": "UNIDAD FORESTAL", "Estado": "FINALIZADA"}
    },
    {
      "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [-66.1618, -17.3795]},
      "properties": {"Numero": "7144/2026", "Fecha": "2026/03/24", "Descripción": "CAIDA DE UN ARBOL TAPANDO LA CALLE EN AV. JUAN DE LA ROSA ENTRE JULIO MENDEZ CERCA AL STADIUM FELIX CAPRILES", "Unidad Responsable": "UNIDAD FORESTAL", "Estado": "DERIVADO"}
    },
    {
      "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [-66.1570, -17.3935]},
      "properties": {"Numero": "1024/2026", "Fecha": "2026/02/14", "Descripción": "OBSTRUCCION DE SUMIDERO Y ACUMULACION DE AGUA PLUVIAL EN EJE RIO ROCHA", "Unidad Responsable": "UGR GAMC", "Estado": "ATENDIDO"}
    },
    {
      "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [-66.1912, -17.3948]},
      "properties": {"Numero": "1150/2026", "Fecha": "2026/03/01", "Descripción": "COLISION VEHICULAR CON DANOS MATERIALES EN AV. BLANCO GALINDO", "Unidad Responsable": "TRANSITO + SEGURIDAD", "Estado": "FINALIZADA"}
    },
    {
      "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [-66.1420, -17.4120]},
      "properties": {"Numero": "1288/2026", "Fecha": "2026/03/10", "Descripción": "DESBORDE PARCIAL DE TORRENTERA COTACHA EN ZONA SUD", "Unidad Responsable": "OBRAS PUBLICAS", "Estado": "EN PROCESO"}
    }
  ],
  "cuencas": [
    {
      "type": "Feature",
      "geometry": {"type": "Polygon", "coordinates": [[[-66.21, -17.31], [-66.09, -17.31], [-66.09, -17.43], [-66.21, -17.43], [-66.21, -17.31]]]},
      "properties": {"Nivel 1": "4", "Nivel 4": "4669", "Nivel 5": "46698", "Nombre uh": "Rio Rocha", "Nivel 7": "4669885"}
    },
    {
      "type": "Feature",
      "geometry": {"type": "Polygon", "coordinates": [[[-66.10, -17.30], [-65.97, -17.30], [-65.97, -17.42], [-66.10, -17.42], [-66.10, -17.30]]]},
      "properties": {"Nivel 1": "4", "Nivel 4": "4669", "Nivel 5": "46698", "Nombre uh": "Rio Rocha", "Nivel 7": "4669881"}
    },
    {
      "type": "Feature",
      "geometry": {"type": "Polygon", "coordinates": [[[-66.18, -17.42], [-66.07, -17.42], [-66.07, -17.51], [-66.18, -17.51], [-66.18, -17.42]]]},
      "properties": {"Nivel 1": "4", "Nivel 4": "4669", "Nivel 5": "46698", "Nombre uh": "Cuenca Tamborada / Pucara", "Nivel 7": "4669886"}
    },
    {
      "type": "Feature",
      "geometry": {"type": "Polygon", "coordinates": [[[-66.28, -17.32], [-66.20, -17.32], [-66.20, -17.41], [-66.28, -17.41], [-66.28, -17.32]]]},
      "properties": {"Nivel 1": "4", "Nivel 4": "4669", "Nivel 5": "46698", "Nombre uh": "Subcuenca Tiquipaya", "Nivel 7": "4669884"}
    }
  ],
  "drenaje": [
    {
      "type": "Feature",
      "geometry": {"type": "LineString", "coordinates": [[-66.25, -17.36], [-66.20, -17.38], [-66.15, -17.39], [-66.10, -17.40], [-66.02, -17.42]]},
      "properties": {"Clasificación": "Torrenteras", "Tipo": "Cauce Principal Río Rocha"}
    },
    {
      "type": "Feature",
      "geometry": {"type": "LineString", "coordinates": [[-66.18, -17.33], [-66.17, -17.36], [-66.15, -17.39]]},
      "properties": {"Clasificación": "Quebradas", "Tipo": "Quebrada Taquiña"}
    },
    {
      "type": "Feature",
      "geometry": {"type": "LineString", "coordinates": [[-66.14, -17.42], [-66.14, -17.46], [-66.15, -17.50]]},
      "properties": {"Clasificación": "Torrenteras", "Tipo": "Torrentera Itocta / Tamborada"}
    }
  ],
  "distritos": [
    {
      "type": "Feature",
      "geometry": {"type": "Polygon", "coordinates": [[[-66.17, -17.37], [-66.13, -17.37], [-66.13, -17.41], [-66.17, -17.41], [-66.17, -17.37]]]},
      "properties": {"Distrito": "D1", "Comuna": "ADELA ZAMUDIO"}
    },
    {
      "type": "Feature",
      "geometry": {"type": "Polygon", "coordinates": [[[-66.18, -17.42], [-66.13, -17.42], [-66.13, -17.47], [-66.18, -17.47], [-66.18, -17.42]]]},
      "properties": {"Distrito": "D9", "Comuna": "ALEJO CALATAYUD"}
    },
    {
      "type": "Feature",
      "geometry": {"type": "Polygon", "coordinates": [[[-66.22, -17.34], [-66.17, -17.34], [-66.17, -17.39], [-66.22, -17.39], [-66.22, -17.34]]]},
      "properties": {"Distrito": "D13", "Comuna": "TUNARI"}
    }
  ]
}

with open(OUT_JS, "w", encoding="utf-8") as f:
    f.write("window.BYRAL_HISTORICAL_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n")

print("Archivo datos_gamc.js generado con éxito.")
