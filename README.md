# PEC2 · Visualización de datos (UOC)

Harold Yesid Garavito Reyes. Tres técnicas de visualización aplicadas a datos abiertos de energía. Se publican con GitHub Pages.

| Técnica | Página | Datos |
|---|---|---|
| I · Cartograma: *Emisiones de CO₂ por país, 2024* | `cartograma/` | Our World in Data (Global Carbon Project) |
| II · Flow Map: *Importaciones de gas natural de la UE por país de origen, 2024* | `flowmap/` | Eurostat `nrg_ti_gas` |
| III · UpSet: *Fuentes de generación eléctrica por país, 2024* | `upset/` | Our World in Data (Ember, Energy Institute) |

## Estructura

- `index.html`: portada con enlaces a las tres visualizaciones.
- `cartograma/`, `flowmap/`, `upset/`: una página estática por técnica, con sus datos en JSON.
- `assets/`: estilos comunes, mapa base Natural Earth 1:110m y librerías (D3.js, topojson-client, UpSet.js) servidas localmente.
- `data/`: datos originales (`raw_*`) y CSV limpios por técnica.
- `scripts/prep.py`: limpieza y transformación con pandas.
- `scripts/build_cartogram.mjs`: cálculo del cartograma contiguo con go-cart-wasm (Gastner, Seguy y More, 2018).

## Regenerar los datos

```bash
pip install pandas
npm install
python scripts/prep.py
node scripts/build_cartogram.mjs   # calcula el cartograma y genera los nombres en español
python scripts/prep.py            # segunda pasada: aplica esos nombres
```

## Publicar en GitHub Pages

1. Sube el contenido de esta carpeta a un repositorio público. No hace falta subir `node_modules/`.
2. En el repositorio, ve a *Settings → Pages → Source*: elige *Deploy from a branch*, la rama `main` y la carpeta `/ (root)`.
3. Las URL quedan así:
   - `https://<usuario>.github.io/<repo>/cartograma/`
   - `https://<usuario>.github.io/<repo>/flowmap/`
   - `https://<usuario>.github.io/<repo>/upset/`

## Licencias de los datos

- Our World in Data: CC BY 4.0.
- Eurostat: reutilización libre con cita de la fuente.
- Natural Earth: dominio público.
