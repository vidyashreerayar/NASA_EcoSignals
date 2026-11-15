// Same scoring as rescore.py, in JavaScript, so weights can change live in the browser.

export const FLAG_LABELS = {
  basalt: 'Basalt / volcanic',
  anorthosite: 'Anorthosite (lunar highland rock)',
  impact: 'Impact structure',
  evaporites: 'Salts / sulfates',
  clays_sediments: 'Clays & lake/river sediments',
  ground_ice: 'Ground ice / permafrost',
  caves: 'Caves / lava tubes',
  regolith: 'Loose regolith-like soil',
  polar_dark: 'Polar darkness / cold traps',
}

// Sites where NASA POWER's ~50 km grid mixes in surrounding terrain.
export const COARSE_GRID = {
  MAUNAKEA: 'Grid cell averages in the lowlands; the 4,000 m summit is far colder and drier.',
  KILAUEA: 'Grid cell mixes in the wet windward slopes.',
  DALLOL: 'Grid cell mixes in rain from the Ethiopian highlands.',
  EREBUS: 'Grid cell mixes in the ocean; the summit is colder.',
  DRYVALLEYS: 'Grid cell mixes in snowfall over the ice sheet.',
}

export const VARS = [
  { key: 'T_mean', label: 'Mean surface temperature', unit: '°C' },
  { key: 'T_range', label: 'Daily temperature swing', unit: '°C' },
  { key: 'precip', label: 'Precipitation', unit: 'mm/yr' },
  { key: 'ndvi', label: 'Vegetation (NDVI)', unit: '' },
]

const clamp = (v, [lo, hi]) => Math.max(lo, Math.min(hi, v))
const gauss = (d, s) => Math.exp(-0.5 * (d / s) ** 2)

export function scoreSite(site, tgt, cfg, wClimate = 0.5) {
  const { earth_bounds: B, scales: S, climate_weights: W } = cfg
  const clamped = {
    T_mean: clamp(tgt.T_mean, B.T_mean),
    T_range: clamp(tgt.T_range, B.T_range),
    precip: tgt.precip,
    ndvi: tgt.ndvi,
  }
  const parts = {
    T_mean: gauss(site.T_mean - clamped.T_mean, S.T_mean),
    T_range: gauss(site.T_range - clamped.T_range, S.T_range),
    precip: gauss(Math.log10(site.precip + 1) - Math.log10(tgt.precip + 1), S.logp),
    ndvi: gauss(site.ndvi - tgt.ndvi, S.ndvi),
  }
  const wsum = W.T_mean + W.T_range + W.logp + W.ndvi
  const climate =
    (parts.T_mean * W.T_mean + parts.T_range * W.T_range + parts.precip * W.logp + parts.ndvi * W.ndvi) / wsum
  const matched = tgt.flags.filter((f) => site.flags.includes(f))
  const missing = tgt.flags.filter((f) => !site.flags.includes(f))
  const geology = matched.length / tgt.flags.length
  const total = Math.round(1000 * (wClimate * climate + (1 - wClimate) * geology)) / 10
  return { total, climate, geology, parts, clamped, matched, missing }
}

// Sequential single-hue ramp (orange), dim -> bright, readable on dark satellite imagery.
const RAMP = ['#5c2a12', '#8a3d17', '#b9511d', '#d95926', '#eb6834', '#f2894f', '#f8ac7a', '#fdd2b3']
export function scoreColor(score) {
  const i = Math.min(RAMP.length - 1, Math.max(0, Math.floor((score / 80) * RAMP.length)))
  return RAMP[i]
}
export const RAMP_STOPS = RAMP

export function worldviewUrl(lat, lon, pad = 1.5) {
  return `https://worldview.earthdata.nasa.gov/?v=${lon - pad},${lat - pad},${lon + pad},${lat + pad}`
}

// LROC QuickMap link centred on a lunar lat/lon (metres on the 1737.4 km sphere).
// South of 60 S: polar orthographic view (proj=17); elsewhere cylindrical (proj=10).
const R_MOON = 1737400
export function quickmapUrl(lat, lon, halfKm = 20) {
  const k = Math.PI / 180
  const h = halfKm * 1000
  let x, y, w, proj
  if (lat < -60) {
    x = R_MOON * Math.cos(lat * k) * Math.sin(lon * k)
    y = R_MOON * Math.cos(lat * k) * Math.cos(lon * k)
    w = h
    proj = 17
  } else {
    x = R_MOON * lon * k
    y = R_MOON * lat * k
    w = h / Math.max(Math.cos(lat * k), 0.02)
    proj = 10
  }
  const ext = [x - w, y - h, x + w, y + h].map((v) => v.toFixed(0)).join('%2C')
  return `https://quickmap.lroc.im-ldi.com/?prjExtent=${ext}&proj=${proj}`
}
