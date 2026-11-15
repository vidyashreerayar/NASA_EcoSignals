import { VARS, FLAG_LABELS, COARSE_GRID, worldviewUrl } from './scoring'

const fmt = (v, key) => (key === 'ndvi' ? v.toFixed(2) : Math.round(v * 10) / 10)

export default function SiteCard({ site, target, total, onClose }) {
  const { r } = site
  const extras = site.flags.filter((f) => !target.flags.includes(f))

  return (
    <div className="card" role="dialog" aria-label={`Details for ${site.name}`}>
      <button className="close" onClick={onClose} aria-label="Close">
        ×
      </button>

      <div className="card-head">
        <div>
          <h3>{site.name}</h3>
          <div className="muted small">
            {site.country} · {site.lat.toFixed(2)}, {site.lon.toFixed(2)} · {site.elev} m
          </div>
          <span className={'status ' + site.status}>{site.status === 'new' ? 'New candidate' : 'Known analog'}</span>
        </div>
        <div className="big-score">
          <div className="num">{r.total}</div>
          <div className="muted small">
            #{site.rank} of {total}
          </div>
        </div>
      </div>

      <div className="split small">
        <div>
          Climate match <strong>{Math.round(r.climate * 100)}%</strong>
        </div>
        <div>
          Geology match <strong>{Math.round(r.geology * 100)}%</strong>
        </div>
      </div>

      <h4>Earth site vs. {target.name.split(' (')[0]}</h4>
      <table className="compare">
        <thead>
          <tr>
            <th>Variable</th>
            <th>Earth</th>
            <th>{target.body}</th>
            <th>Match</th>
          </tr>
        </thead>
        <tbody>
          {VARS.map((v) => {
            const clampedNote = r.clamped[v.key] !== target[v.key]
            return (
              <tr key={v.key}>
                <td>
                  {v.label}
                  {v.unit && <span className="muted"> ({v.unit})</span>}
                </td>
                <td>{fmt(site[v.key], v.key)}</td>
                <td>
                  {fmt(target[v.key], v.key)}
                  {clampedNote && (
                    <span className="muted" title="Earth can't reach this value, so the score uses Earth's extreme instead">
                      {' '}
                      → {r.clamped[v.key]}*
                    </span>
                  )}
                </td>
                <td>
                  <span className="mini-bar">
                    <span style={{ width: `${Math.round(r.parts[v.key] * 100)}%` }} />
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="muted small">
        * Beyond Earth's range, so the score compares against the most extreme value Earth reaches.
      </p>

      <h4>Geology & features</h4>
      <div className="tags">
        {r.matched.map((f) => (
          <span key={f} className="tag ok">
            ✓ {FLAG_LABELS[f]}
          </span>
        ))}
        {r.missing.map((f) => (
          <span key={f} className="tag miss">
            ✗ {FLAG_LABELS[f]}
          </span>
        ))}
        {extras.map((f) => (
          <span key={f} className="tag">
            + {FLAG_LABELS[f]}
          </span>
        ))}
      </div>

      <h4>Why it matters</h4>
      <p className="small">{site.used_for}</p>

      <h4>Data</h4>
      <p className="small muted">
        Climate: {site.climate_source || 'estimate'}
        {site.estimate && (
          <>
            {' '}
            (first estimate was {site.estimate.T_mean} °C, {site.estimate.precip} mm/yr)
          </>
        )}
      </p>
      {COARSE_GRID[site.id] && (
        <p className="warn small">
          <span aria-hidden="true">⚠</span> <strong>Coarse grid:</strong> {COARSE_GRID[site.id]} Refine with 1 km MODIS data.
        </p>
      )}
      <a className="link" href={worldviewUrl(site.lat, site.lon)} target="_blank" rel="noreferrer">
        Open this site in NASA Worldview →
      </a>
    </div>
  )
}
