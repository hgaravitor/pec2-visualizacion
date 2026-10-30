// PEC2 - Cálculo del cartograma contiguo (algoritmo de Gastner, Seguy y More, 2018 - "flow-based")
// Entrada: mapa mundial Natural Earth 1:110m (paquete world-atlas) + cartograma/co2.json
// Salida : cartograma/geo.json con la geometría original y la deformada (misma estructura de vértices)
// Uso    : node scripts/build_cartogram.mjs   (requiere: npm i go-cart-wasm world-atlas topojson-client d3-geo i18n-iso-countries)
import { readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { feature } from "topojson-client";
import { geoEqualEarth } from "d3-geo";
import { geoProject } from "d3-geo-projection"; // proyecta cortando el antimeridiano (Rusia, Fiyi)

const require = createRequire(import.meta.url);
const NM = new URL("../node_modules", import.meta.url).pathname;
const countries = require(`${NM}/i18n-iso-countries`);
countries.registerLocale(require(`${NM}/i18n-iso-countries/langs/es.json`));
// Nombres de uso común en lugar de la denominación oficial
const NOMBRE = { COD: "R. D. del Congo", COG: "Congo", CZE: "Chequia", KOR: "Corea del Sur", PRK: "Corea del Norte",
  LAO: "Laos", SYR: "Siria", RUS: "Rusia", IRN: "Irán", TZA: "Tanzania", BOL: "Bolivia", VEN: "Venezuela",
  SXM: "Sint Maarten", BES: "Caribe neerlandés", SHN: "Santa Elena", FSM: "Micronesia", MDA: "Moldavia",
  BHR: "Baréin", GBR: "Reino Unido", USA: "Estados Unidos", CIV: "Costa de Marfil", GNB: "Guinea-Bisáu", PSE: "Palestina", SAU: "Arabia Saudí" };
const nombre = (iso3) => NOMBRE[iso3] || countries.getName(iso3, "es");
const initGoCart = require(`${NM}/go-cart-wasm/dist/go-cart.cjs`);

const ROOT = new URL("..", import.meta.url).pathname;
const co2 = JSON.parse(readFileSync(`${ROOT}cartograma/co2.json`, "utf8")).paises;
const topo = JSON.parse(readFileSync(`${NM}/world-atlas/countries-110m.json`, "utf8"));
const world = feature(topo, topo.objects.countries);

// 1) Proyección de áreas iguales (Equal Earth) a coordenadas planas: requisito del algoritmo
const W = 960, H = 470;
const proj = geoEqualEarth().fitSize([W, H], { type: "Sphere" });
// Coordenadas cartesianas (y hacia arriba) y orientación GeoJSON estándar: exterior horario, huecos antihorario (convención de go-cart)
const signed = (r) => r.reduce((s, p, i) => { const q = r[(i + 1) % r.length]; return s + p[0] * q[1] - q[0] * p[1]; }, 0) / 2;
const orient = (r, ccw) => ((signed(r) > 0) === ccw ? r : r.slice().reverse());
const projectRing = (ring, i) => orient(ring.map(([x, y]) => [+x.toFixed(2), +(H - y).toFixed(2)]), i !== 0); // go-cart espera exterior en sentido horario
const projectGeom = (g) =>
  g.type === "Polygon"
    ? { type: "Polygon", coordinates: g.coordinates.map(projectRing) }
    : { type: "MultiPolygon", coordinates: g.coordinates.map((poly) => poly.map(projectRing)) };

// Kosovo (sin código ISO numérico) y Norte de Chipre se omiten; Antártida no emite CO2 -> fuera
const feats = [];
for (const f of world.features) {
  if (!f.id || f.id === "010") continue;
  const iso3 = countries.numericToAlpha3(f.id);
  if (!iso3) continue;
  const rec = co2[iso3];
  feats.push({
    type: "Feature",
    properties: { iso3, name: nombre(iso3) || f.properties.name,
                  co2: rec ? rec[1] : null, co2pc: rec ? rec[2] : null,
                  // el algoritmo necesita un valor > 0: países sin dato reciben un mínimo simbólico
                  w: rec && rec[1] > 0 ? rec[1] : 0.01 },
    geometry: projectGeom(geoProject(f, proj).geometry),
  });
}
const fc = { type: "FeatureCollection", features: feats };

// 2) Cartograma
const GoCart = await initGoCart({ locateFile: () => `${NM}/go-cart-wasm/dist/cart.wasm` });
const cart = GoCart.makeCartogram(fc, "w");

// 3) Comprobación: área de cada país proporcional a su CO2
const polyArea = (poly) => poly.reduce((s, r, i) => s + (i === 0 ? 1 : -1) * Math.abs(signed(r)), 0);
const area = (f) => (f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates).reduce((s, p) => s + polyArea(p), 0);
const tot = { a: 0, v: 0 };
cart.features.forEach((f) => { tot.a += area(f); tot.v += f.properties.w; });
const err = cart.features
  .filter((f) => f.properties.co2 > 100)
  .map((f) => ({ n: f.properties.name, ratio: +((area(f) / tot.a) / (f.properties.w / tot.v)).toFixed(2) }));
console.log("Países:", feats.length, "| área relativa / CO2 relativo (ideal = 1):", err.map((e) => `${e.n} ${e.ratio}`).join(" | "));

const round = (g) => JSON.parse(JSON.stringify(g, (k, v) => (typeof v === "number" ? +v.toFixed(1) : v)));
const out = feats.map((f, i) => ({ p: f.properties, o: round(f.geometry), c: round(cart.features[i].geometry) }));
const matched = cart.features.every((f, i) => f.properties.iso3 === feats[i].properties.iso3);
console.log("Orden conservado:", matched);
writeFileSync(`${ROOT}cartograma/geo.json`, JSON.stringify({ w: W, h: H, f: out }));
writeFileSync(`${ROOT}data/nombres_es.json`, JSON.stringify(
  Object.fromEntries(Object.keys(countries.getAlpha3Codes()).map((a3) => [a3, nombre(a3)])), null, 0));
