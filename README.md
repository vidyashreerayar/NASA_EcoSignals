# EcoSignals Analog Explorer

**Which places on Earth are most like a given Moon or Mars site, and which of them are not yet being used?**

An interactive map that scores 32 Earth sites against 7 lunar and Martian target sites using open NASA data, then characterizes the targets themselves with LRO and MGS mission data.

**Live app:** https://nasa-eco-signals.vercel.app
**Challenge:** NASA Space Apps, *identify and characterize new terrestrial analogs for future bases or landing sites*

---

## What it does

- **Pick a target** on the Moon (south pole, Mare Tranquillitatis lava-tube pit, Hadley Rille) or Mars (Jezero, Gale, Arcadia Planitia, Arsia Mons cave skylights).
- **See every Earth candidate re-scored** on a NASA Blue Marble / VIIRS map. Bigger, brighter dots are closer matches. New candidates are ringed in white.
- **Weigh the evidence:** a slider shifts the score between climate and geology, and the ranking updates live.
- **Open a site card** to compare the Earth site and the target variable by variable, see which geological features match, and jump to NASA Worldview.
- **Inspect the target:** Mars targets show MOLA terrain (elevation, air pressure, relief, slope). The lunar south pole shows LOLA terrain, sunlight, permanent shadow and the **six best landing patches nearby**, each linked to LROC QuickMap imagery.

## Key findings

| Finding | Evidence |
|---|---|
| **Umm Jirsan lava tube (Saudi Arabia)** is the strongest cave analog on Earth for both the Moon (72.4) and Mars (72.0), ahead of established sites such as Lanzarote and Kilauea. It is not yet used as an analog. | Hyper-arid basalt, a 1.5 km lava tube, almost no vegetation (NASA POWER) |
| **Kamil Crater (Egypt)** ranks #1 for lunar mare plains and #2 for Jezero. | A pristine small impact crater in a hyper-arid desert with 0 mm/yr precipitation |
| **Arcadia Planitia** is almost perfectly flat: 37 m of relief and a 0.05° mean slope within 50 km. | MOLA. This explains its status as a crewed-base candidate. |
| **Arsia Mons cave skylights** offer radiation shelter but sit at +10 km, with about 246 Pa of air, versus 775–911 Pa at Jezero and Gale. | MOLA, giving a shelter-versus-access trade-off |
| **The exact lunar south pole is a poor landing site:** 29.6° mean slope, only 4.8% of the 10 km zone under 8°, 19% sunlight. | LOLA 240 m DEM, LOLA illumination and PSR maps |
| **Sunlight versus flatness at the lunar pole:** peaks reach 93% sunlight but are steep. The best *flat* patches get 19–38% sunlight, and all lie within about 2 km of permanently shadowed (ice-bearing) ground. | Landing-site finder |
| **Validation passes:** known analogs (Dry Valleys, Death Valley, Lanzarote, Haughton) rank in the top 6 for every target. | `rescore.py` |

## Method

**Similarity score (0–100) = 50% climate + 50% geology** (the weight is adjustable in the app).

- **Climate:** Gaussian similarity on mean surface temperature, daily temperature range, log precipitation and vegetation (NDVI). Earth cannot reach −170 °C, so Moon and Mars targets are **clamped to the most extreme values Earth reaches**. Sites are ranked by how close they get.
- **Geology:** the share of the target's features present at the site (basalt, anorthosite, impact structure, salts, clays/sediments, ground ice, caves, regolith, polar darkness).
- **Validation:** the method must rank established analogs highly without being told which ones they are. Only then are high-scoring *new* sites treated as findings.

**Lunar landing-site finder:** for every 240 m cell within 70 km of the pole, the surrounding 2 km patch is scored as 0.45 × sunlight + 0.35 × share of slopes under 8° + 0.20 × closeness to permanent shadow. Cells inside shadow and patches under 80% flat are excluded. The top six patches at least 8 km apart are kept.

## Data

| Body | Data | Used for |
|---|---|---|
| Earth | NASA POWER climatology 2001–2025 (MERRA-2, GPM IMERG) | Surface temperature, daily range, precipitation for all 32 sites |
| Earth | NASA GIBS (Blue Marble, VIIRS true color), NASA Worldview | Map imagery, site links |
| Moon | LRO LOLA LDEM 240 m south-polar DEM (PDS) | Elevation, slope, relief |
| Moon | LOLA average illumination and permanent-shadow maps, Mazarico et al. 2011 (NASA GSFC PGDA) | Sunlight, ice proximity, landing sites |
| Moon | LRO Diviner, LROC (literature values), LROC QuickMap | Target temperatures, imagery links |
| Mars | MGS MOLA MEGDR 0.25° (PDS) | Elevation, pressure estimate, relief, slope, Mars map |
| Mars | Mars 2020 MEDA, MSL REMS, SWIM, THEMIS (literature values) | Target temperatures and features |

## Reproduce the pipeline

The raw rasters are too large for GitHub. Download them first:

- `MOLA Mars Global.csv`: MOLA MEGDR 0.25° elevation (PDS Geosciences)
- `LOLA_South Pole.csv`: LOLA LDEM_75S_240M exported as lat/lon points (PDS Geosciences)
- `AVGVISIB_65S_240M_201608.tiff` and `LPSR_65S_240M_201608.tiff`: https://pgda.gsfc.nasa.gov/products/69

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pandas numpy pillow requests rasterio scipy

python extract_nasa_power.py analog_data.json analog_data_nasa.json   # Earth climate from NASA POWER
python rescore.py analog_data_nasa.json                                # scores + validation report
python mars_terrain.py "MOLA Mars Global.csv" analog_data_scored.json  # Mars terrain + map
python lunar_terrain.py "LOLA_South Pole.csv" analog_data_scored.json  # lunar terrain
python landing_sites.py "LOLA_South Pole.csv" AVGVISIB_65S_240M_201608.tiff LPSR_65S_240M_201608.tiff analog_data_scored.json

cp analog_data_scored.json analog-explorer/src/data/
cp lunar_south_pole.jpg mars_mola.jpg analog-explorer/src/assets/

cd analog-explorer && npm install && npm run dev
```

## Repository structure

```
analog-explorer/        React + Vite + Leaflet web app
  src/App.jsx           map, target picker, weights, ranking
  src/SiteCard.jsx      Earth-vs-target comparison card
  src/MarsInset.jsx     MOLA Mars map and terrain
  src/MoonInset.jsx     LOLA pole map, sunlight/shadow, landing sites
  src/scoring.js        scoring (mirrors rescore.py), QuickMap/Worldview links
extract_nasa_power.py   NASA POWER climate extraction
rescore.py              similarity scoring + validation
mars_terrain.py         MOLA terrain metrics + Mars map
lunar_terrain.py        LOLA terrain metrics + pole map
landing_sites.py        lunar landing-site finder
analog_data_scored.json final dataset used by the app
earth_sites_scored.csv  results table
```

## Limitations

- **Coarse Earth climate grid:** NASA POWER cells are about 50 km wide, so small or high-altitude sites mix in surrounding terrain. Mauna Kea, Kilauea, Dallol, Erebus and the Dry Valleys are flagged ⚠ in the app. Next step: 1 km MODIS land-surface temperature and NDVI.
- **Geology is binary feature tags** from the literature. Spectral data (for example CRISM, Moon Mineralogy Mapper, Sentinel-2) would make it quantitative.
- **Moon and Mars target climates** are rounded literature values. Terrain metrics are computed directly from LOLA and MOLA.
- **Landing-site scoring** uses illustrative weights and a 240 m slope scale. It is not a mission-grade hazard assessment.
- **Partner-agency data** (CSA RADARSAT, ESA Sentinel, JAXA) is not yet integrated. Radar roughness comparisons are a natural extension.

## Tech

Python (pandas, numpy, rasterio, scipy, Pillow) · React · Vite · Leaflet / react-leaflet · deployed on Vercel

## Use of AI

This project was built with help from Claude (Anthropic): it assisted with scoping, the Python data pipeline, the React app and documentation. All data and results come from NASA datasets; we ran and checked every step ourselves.

## Use of AI

This project was built with help from Claude (Anthropic): it assisted with the Python data pipeline, the React app and documentation. All data and results come from NASA datasets; the team ran and checked every step.
