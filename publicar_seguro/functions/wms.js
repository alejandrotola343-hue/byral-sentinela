export async function onRequest(context) {
  const url = new URL(context.request.url);
  const serviceId = url.searchParams.get("service_id");

  // Si guardas las URLs o API Keys como Secrets en Cloudflare, se leen con context.env
  const ALLOWED_SERVICES = {
    "fb368617-f2fd-43e8-867a-4456364efb52": context.env.WMS_CUENCAS_URL || "https://geoportal.cochabamba.bo/geoserver/wms",
    "d4cea6e3-fc7f-482a-94ad-bd377df78886": context.env.WMS_DRENAJE_URL || "https://geoportal.cochabamba.bo/geoserver/wms",
    "7eb13092-bf0e-493b-aae6-03c43eedda2c": context.env.WMS_DISTRITOS_URL || "https://geoportal.cochabamba.bo/geoserver/wms",
    "e105a6ed-74bb-41a5-8c85-9360711ddf69": context.env.WMS_EMERGENCIAS_URL || "https://geoportal.cochabamba.bo/geoserver/wms"
  };

  if (!serviceId || !ALLOWED_SERVICES[serviceId]) {
    return new Response(JSON.stringify({ error: "Servicio no autorizado" }), {
      status: 403,
      headers: { "Content-Type": "application/json" }
    });
  }

  const targetUrl = new URL(ALLOWED_SERVICES[serviceId]);
  url.searchParams.forEach((value, key) => {
    if (key !== "service_id") targetUrl.searchParams.set(key, value);
  });

  try {
    const upstream = await fetch(targetUrl.toString(), {
      headers: { "User-Agent": "BYRAL-Sentinela-Edge/1.0" }
    });

    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("Content-Type") || "application/json",
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=60"
      }
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: "Error conectando con servicio origen" }), {
      status: 502,
      headers: { "Content-Type": "application/json" }
    });
  }
}
