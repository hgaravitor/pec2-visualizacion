"""PEC2 - Preparación de datos para las tres visualizaciones.

Fuentes (datos abiertos):
  - Our World in Data, CO2 and Greenhouse Gas Emissions (github.com/owid/co2-data)
  - Our World in Data, Energy dataset (github.com/owid/energy-data)
  - Eurostat, nrg_ti_gas - Imports of natural gas by partner country (2024, Mm3)

Uso:  python scripts/prep.py   (desde la raíz del repositorio)
"""
import json
from pathlib import Path

import pandas as pd

D = Path(__file__).resolve().parent.parent / "data"
YEAR = 2024

# ---------------------------------------------------------------- 1. Cartograma
raw = pd.read_csv(D / "raw_owid_co2.csv", usecols=["country", "iso_code", "year", "co2", "co2_per_capita", "population"])
raw = raw[raw.year == YEAR]
# Total mundial = fila "World" de OWID: incluye la aviación y el transporte marítimo internacionales,
# que no se asignan a ningún país. Los porcentajes se calculan sobre este total.
WORLD = float(raw.loc[raw.country == "World", "co2"].iloc[0])
BUNKERS = float(raw.loc[raw.country.isin(["International aviation", "International shipping"]), "co2"].sum())
# Se eliminan los agregados (continentes, grupos de renta, UE...): no tienen código ISO o usan OWID_*
co2 = raw[raw.iso_code.notna() & ~raw.iso_code.str.startswith("OWID")]
co2 = co2.dropna(subset=["co2"])[["iso_code", "country", "co2", "co2_per_capita", "population"]]
co2.to_csv(D / "cartograma_co2_2024.csv", index=False)
print(f"Cartograma: {len(co2)} países y territorios, suma {co2.co2.sum():,.0f} Mt; total mundial {WORLD:,.0f} Mt "
      f"(transporte internacional {BUNKERS:,.0f} Mt)")

# ---------------------------------------------------------------- 2. Flow map
EU = ["AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU", "IE", "IT",
      "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"]
THRESHOLD = 1000  # Mm3: se muestran solo los flujos >= 1 bcm (96 % del gas extra-UE)

# Nodo de cada país = su capital (lat, lon, nombre en español)
NODES = {
    # orígenes
    "NO": (59.91, 10.75, "Noruega"), "UK": (51.51, -0.13, "Reino Unido"), "RU": (55.76, 37.62, "Rusia"),
    "TR": (39.93, 32.86, "Turquía"), "AZ": (40.41, 49.87, "Azerbaiyán"), "DZ": (36.75, 3.06, "Argelia"),
    "LY": (32.89, 13.19, "Libia"), "NG": (9.08, 7.40, "Nigeria"), "QA": (25.29, 51.53, "Catar"),
    "US": (38.90, -77.04, "Estados Unidos"), "TT": (10.66, -61.51, "Trinidad y Tobago"), "PE": (-12.05, -77.04, "Perú"),
    # destinos (Estados miembro)
    "BE": (50.85, 4.35, "Bélgica"), "BG": (42.70, 23.32, "Bulgaria"), "CZ": (50.08, 14.44, "Chequia"),
    "DE": (52.52, 13.40, "Alemania"), "DK": (55.68, 12.57, "Dinamarca"), "EL": (37.98, 23.73, "Grecia"),
    "ES": (40.42, -3.70, "España"), "FI": (60.17, 24.94, "Finlandia"), "FR": (48.86, 2.35, "Francia"),
    "HR": (45.81, 15.98, "Croacia"), "HU": (47.50, 19.04, "Hungría"), "IE": (53.35, -6.26, "Irlanda"),
    "IT": (41.90, 12.50, "Italia"), "LT": (54.69, 25.28, "Lituania"), "NL": (52.37, 4.90, "Países Bajos"),
    "PT": (38.72, -9.14, "Portugal"), "SK": (48.15, 17.11, "Eslovaquia"),
}

g = pd.read_csv(D / "raw_eurostat_nrg_ti_gas_2024.csv")
g = g[(g.TIME_PERIOD == YEAR) & (g.siec == "G3000") & (g.unit == "MIO_M3") & g.geo.isin(EU) & (g.OBS_VALUE > 0)]
# partner: código de país de 2 letras, o agregado (TOTAL, NSP = no especificado, *_OTH = "otros países de...")
TOTAL_UE = g.loc[g.partner == "TOTAL", "OBS_VALUE"].sum()                       # todas las importaciones
INTRA_UE = g.loc[g.partner.isin(EU), "OBS_VALUE"].sum()                          # desde otro Estado miembro
SIN_PAIS = g.loc[(g.partner.str.len() != 2) & (g.partner != "TOTAL"), "OBS_VALUE"].sum()  # origen no identificado
extra = g[~g.partner.isin(EU) & (g.partner.str.len() == 2)]                      # fuera de la UE, país identificado
flows = extra[extra.OBS_VALUE >= THRESHOLD].rename(columns={"partner": "origen", "geo": "destino", "OBS_VALUE": "mm3"})
flows = flows[["origen", "destino", "mm3"]].sort_values("mm3", ascending=False)
for side in ("origen", "destino"):
    flows[f"{side}_nombre"] = flows[side].map(lambda c: NODES[c][2])
    flows[f"{side}_lat"] = flows[side].map(lambda c: NODES[c][0])
    flows[f"{side}_lon"] = flows[side].map(lambda c: NODES[c][1])
flows.to_csv(D / "flowmap_gas_ue_2024.csv", index=False)
print(f"Flow map: {len(flows)} flujos >= {THRESHOLD} Mm3, {flows.origen.nunique()} orígenes, "
      f"{flows.destino.nunique()} destinos, {flows.mm3.sum() / extra.OBS_VALUE.sum():.0%} del gas extra-UE")

# ---------------------------------------------------------------- 3. UpSet
SETS = {"coal": "Carbón", "gas": "Gas", "oil": "Petróleo", "nuclear": "Nuclear", "hydro": "Hidráulica",
        "wind": "Eólica", "solar": "Solar", "biofuel": "Bioenergía", "other_renewables_exc_biofuel": "Otras renovables"}
# "Otras renovables" = geotérmica, mareomotriz, etc. (columna other_renewables_share_elec_exc_biofuel)
UMBRAL = 5.0  # % de la electricidad generada: un país "pertenece" al conjunto si la fuente aporta >= 5 %
col = lambda k: "other_renewables_share_elec_exc_biofuel" if k.startswith("other") else f"{k}_share_elec"
cols = [col(k) for k in SETS]
en = pd.read_csv(D / "raw_owid_energy.csv", usecols=["country", "iso_code", "year", "electricity_generation"] + cols)
en = en[(en.year == YEAR) & en.iso_code.notna() & ~en.iso_code.str.startswith("OWID")].dropna(subset=cols[:-1])
en[cols[-1]] = en[cols[-1]].fillna(0)  # "otras renovables" sin dato = no se usa
up = en[["iso_code", "country", "electricity_generation"]].copy()
for k, name in SETS.items():
    up[name] = (en[col(k)] >= UMBRAL).astype(int)
up.to_csv(D / "upset_mix_electrico_2024.csv", index=False)
print(f"UpSet: {len(up)} países, {len(SETS)} conjuntos, tamaños: {up[list(SETS.values())].sum().to_dict()}")

# Nombres en español (generados por build_cartogram.mjs a partir de i18n-iso-countries)
ES = json.loads((D / "nombres_es.json").read_text()) if (D / "nombres_es.json").exists() else {}

# JSON compactos que consumen las páginas web
(D.parent / "cartograma" / "co2.json").write_text(json.dumps({
    "mundo": round(WORLD, 1), "transporte_internacional": round(BUNKERS, 1),
    "mundo_por_hab": round(float(raw.loc[raw.country == "World", "co2_per_capita"].iloc[0]), 2),
    "africa": round(float(raw.loc[raw.country == "Africa", "co2"].iloc[0]), 1),
    "africa_pob": float(raw.loc[raw.country == "Africa", "population"].iloc[0]),
    "paises": {r.iso_code: [ES.get(r.iso_code) or r.country, round(r.co2, 1),
                            None if pd.isna(r.co2_per_capita) else round(r.co2_per_capita, 2)]
               for r in co2.itertuples()}}, ensure_ascii=False))
(D.parent / "flowmap" / "flows.json").write_text(json.dumps({
    "umbral_mm3": THRESHOLD,
    "total_importado": round(TOTAL_UE, 1), "intra_ue": round(INTRA_UE, 1), "sin_pais": round(SIN_PAIS, 1),
    "total_extra_ue": round(extra.OBS_VALUE.sum(), 1),          # todos los flujos extra-UE, sin umbral
    "por_origen": extra.groupby("partner").OBS_VALUE.sum().round(1).to_dict(),
    "por_destino": extra.groupby("geo").OBS_VALUE.sum().round(1).to_dict(),
    "flujos": flows.round(2).to_dict("records")}, ensure_ascii=False))
(D.parent / "upset" / "mix.json").write_text(json.dumps(
    [{"name": ES.get(r["iso_code"]) or r["country"], "iso": r["iso_code"], "twh": None if pd.isna(r["electricity_generation"]) else round(r["electricity_generation"], 1),
      "sets": [n for n in SETS.values() if r[n]]} for _, r in up.iterrows()], ensure_ascii=False))
