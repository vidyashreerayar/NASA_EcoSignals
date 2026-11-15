import { useEffect, useMemo, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Tooltip, LayersControl, useMap } from 'react-leaflet'
import data from './data/analog_data_scored.json'
import { scoreSite, scoreColor, RAMP_STOPS, FLAG_LABELS, quickmapUrl } from './scoring'
import SiteCard from './SiteCard'
import MarsInset from './MarsInset'
import MoonInset from './MoonInset'

const GIBS = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best'
const ATTR = 'Imagery: <a href="https://earthdata.nasa.gov/gibs">NASA GIBS</a> / Worldview'

function FlyTo({ site }) {
  const map = useMap()
  useEffect(() => {
    if (site) map.flyTo([site.lat, site.lon], Math.max(map.getZoom(), 4), { duration: 0.8 })
  }, [site, map])
  return null
}

export default function App() {
  const [targetId, setTargetId] = useState('MOON_PIT')
  const [wClimate, setWClimate] = useState(0.5)
  const [filter, setFilter] = useState('all')
  const [selectedId, setSelectedId] = useState(null)

  const target = data.targets.find((t) => t.id === targetId)

  const scored = useMemo(
    () =>
      data.sites
        .map((s) => ({ ...s, r: scoreSite(s, target, data, wClimate) }))
        .sort((a, b) => b.r.total - a.r.total)
        .map((s, i) => ({ ...s, rank: i + 1 })),
    [target, wClimate],
  )
  const visible = scored.filter((s) => filter === 'all' || s.status === filter)
  const selected = scored.find((s) => s.id === selectedId)

  const groups = ['Moon', 'Mars'].map((body) => ({ body, targets: data.targets.filter((t) => t.body === body) }))

  return (
    <div className="app">
      <aside className="sidebar">
        <header>
          <h1>EcoSignals Analog Explorer</h1>
          <p className="muted">
            Which places on Earth are most like a given Moon or Mars site? Scores combine NASA POWER climate data with
            geology features.
          </p>
        </header>

        <section>
          <h2>1. Choose a target</h2>
          {groups.map((g) => (
            <div key={g.body} className="target-group">
              <span className="group-label">{g.body}</span>
              <div className="chips">
                {g.targets.map((t) => (
                  <button
                    key={t.id}
                    className={'chip' + (t.id === targetId ? ' active' : '')}
                    onClick={() => setTargetId(t.id)}
                  >
                    {t.name.split(' (')[0]}
                  </button>
                ))}
              </div>
            </div>
          ))}
          <div className="target-info">
            <strong>{target.name}</strong>
            <div className="muted small">
              {target.T_mean} °C mean · {target.T_range} °C daily swing · no liquid water
            </div>
            <div className="tags">
              {target.flags.map((f) => (
                <span key={f} className="tag">
                  {FLAG_LABELS[f]}
                </span>
              ))}
            </div>
            <div className="muted small">Reference data: {target.source}</div>
            {target.body === 'Mars' && (
              <MarsInset target={target} allTargets={data.targets} onPick={setTargetId} />
            )}
            {target.body === 'Moon' && target.terrain && <MoonInset target={target} landing={data.landing_sites} />}
            {target.body === 'Moon' && !target.terrain && (
              <a className="link" href={quickmapUrl(target.lat, target.lon, 15)} target="_blank" rel="noreferrer">
                Open the target in LROC QuickMap →
              </a>
            )}
          </div>
        </section>

        <section>
          <h2>2. Weigh the evidence</h2>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={wClimate}
            onChange={(e) => setWClimate(+e.target.value)}
            aria-label="Climate versus geology weight"
          />
          <div className="slider-labels small">
            <span>Climate {Math.round(wClimate * 100)}%</span>
            <span>Geology {Math.round((1 - wClimate) * 100)}%</span>
          </div>
          <div className="segmented">
            {[
              ['all', 'All sites'],
              ['new', 'New candidates'],
              ['known', 'Known analogs'],
            ].map(([k, l]) => (
              <button key={k} className={filter === k ? 'active' : ''} onClick={() => setFilter(k)}>
                {l}
              </button>
            ))}
          </div>
        </section>

        <section className="ranking">
          <h2>3. Best matches</h2>
          <ol>
            {visible.slice(0, 12).map((s) => (
              <li
                key={s.id}
                className={s.id === selectedId ? 'selected' : ''}
                onClick={() => setSelectedId(s.id)}
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && setSelectedId(s.id)}
              >
                <span className="rank">{s.rank}</span>
                <span className="site-name">
                  {s.name}
                  <span className="muted small">
                    {' '}
                    · {s.country}
                    {s.status === 'new' && <span className="new-badge">NEW</span>}
                  </span>
                </span>
                <span className="bar">
                  <span style={{ width: `${s.r.total}%`, background: scoreColor(s.r.total) }} />
                </span>
                <span className="score">{s.r.total}</span>
              </li>
            ))}
          </ol>
        </section>

        <footer className="muted small">
          Data: NASA POWER (MERRA-2, GPM IMERG), LRO Diviner/LOLA, Mars 2020 MEDA, MSL REMS, SWIM, THEMIS via PDS. Imagery:
          NASA GIBS.
        </footer>
      </aside>

      <main className="map-wrap">
        <MapContainer center={[20, 10]} zoom={2} minZoom={2} maxZoom={8} worldCopyJump className="map">
          <LayersControl position="topleft">
            <LayersControl.BaseLayer checked name="NASA Blue Marble">
              <TileLayer
                url={`${GIBS}/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg`}
                attribution={ATTR}
                maxNativeZoom={8}
              />
            </LayersControl.BaseLayer>
            <LayersControl.BaseLayer name="VIIRS true color (2025)">
              <TileLayer
                url={`${GIBS}/VIIRS_SNPP_CorrectedReflectance_TrueColor/default/2025-06-15/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`}
                attribution={ATTR}
                maxNativeZoom={9}
              />
            </LayersControl.BaseLayer>
          </LayersControl>

          {[...visible].reverse().map((s) => (
            <CircleMarker
              key={`${s.id}-${targetId}`}
              center={[s.lat, s.lon]}
              radius={5 + s.r.total / 9}
              pathOptions={{
                fillColor: scoreColor(s.r.total),
                fillOpacity: 0.95,
                color: s.id === selectedId ? '#3987e5' : s.status === 'new' ? '#f0efec' : '#1a1a19',
                weight: s.id === selectedId ? 4 : s.status === 'new' ? 2.5 : 1.5,
              }}
              eventHandlers={{ click: () => setSelectedId(s.id) }}
            >
              <Tooltip direction="top" offset={[0, -6]}>
                <strong>{s.name}</strong>
                <br />#{s.rank} · score {s.r.total} {s.status === 'new' ? '· new candidate' : '· known analog'}
              </Tooltip>
            </CircleMarker>
          ))}
          <FlyTo site={selected} />
        </MapContainer>

        <div className="legend">
          <div className="legend-title">Similarity to {target.name.split(' (')[0]}</div>
          <div className="ramp">
            {RAMP_STOPS.map((c) => (
              <span key={c} style={{ background: c }} />
            ))}
          </div>
          <div className="ramp-labels small">
            <span>0</span>
            <span>80+</span>
          </div>
          <div className="legend-row small">
            <span className="dot new" /> New candidate (white ring)
          </div>
          <div className="legend-row small">
            <span className="dot known" /> Known analog
          </div>
          <div className="muted small">Bigger, brighter = more similar</div>
        </div>

        {selected && (
          <SiteCard site={selected} target={target} total={scored.length} onClose={() => setSelectedId(null)} />
        )}
      </main>
    </div>
  )
}
