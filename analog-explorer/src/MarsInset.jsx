import marsMap from './assets/mars_mola.jpg'

// Equirectangular map: x from longitude (-180..180), y from latitude (90..-90).
const pos = (lat, lon) => ({ left: `${((lon + 180) / 360) * 100}%`, top: `${((90 - lat) / 180) * 100}%` })

function terrainClass(slope) {
  if (slope < 1) return 'Very smooth: favourable for landing'
  if (slope < 3) return 'Moderate relief'
  return 'Rugged: hard landing terrain'
}

export default function MarsInset({ target, allTargets, onPick }) {
  const t = target.terrain
  const mars = allTargets.filter((x) => x.body === 'Mars')

  return (
    <div className="inset">
      <div className="inset-map">
        <img src={marsMap} alt="Mars shaded-relief elevation map from MOLA" />
        {mars.map((m) => (
          <button
            key={m.id}
            className={'inset-pin' + (m.id === target.id ? ' active' : '')}
            style={pos(m.lat, m.lon)}
            onClick={() => onPick(m.id)}
            title={m.name}
            aria-label={m.name}
          />
        ))}
        <span className="inset-label">Mars · MOLA elevation</span>
      </div>

      {t && (
        <>
          <dl className="terrain">
            <div>
              <dt>Elevation</dt>
              <dd>{(t.elevation_m / 1000).toFixed(1)} km</dd>
            </div>
            <div>
              <dt>Air pressure</dt>
              <dd>{t.pressure_pa} Pa</dd>
            </div>
            <div>
              <dt>Local relief</dt>
              <dd>{t.relief_m.toLocaleString()} m</dd>
            </div>
            <div>
              <dt>Mean slope</dt>
              <dd>{t.mean_slope_deg}°</dd>
            </div>
          </dl>
          <div className="small muted">
            {terrainClass(t.mean_slope_deg)} · higher than {Math.round(t.elev_percentile)}% of Mars · Earth sea-level
            pressure is 101,325 Pa
          </div>
          <div className="small muted">Terrain within 50 km, from {t.source}</div>
        </>
      )}
    </div>
  )
}
