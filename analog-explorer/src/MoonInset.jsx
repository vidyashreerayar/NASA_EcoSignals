import poleMap from './assets/lunar_south_pole.jpg'
import { quickmapUrl } from './scoring'

const SCALE_KM = 50

export default function MoonInset({ target, landing }) {
  const t = target.terrain
  if (!t) return null
  const barPct = (SCALE_KM / t.extent_km) * 100
  const sites = landing?.sites || []

  return (
    <div className="inset">
      <div className="inset-map">
        <img src={poleMap} alt="Lunar south pole shaded-relief map from LOLA, permanently shadowed regions in blue" />
        <span
          className="inset-zone"
          style={{
            left: `${t.map_x * 100}%`,
            top: `${t.map_y * 100}%`,
            width: `${((2 * t.radius_km) / t.extent_km) * 100}%`,
          }}
          title={`${t.radius_km} km zone around the target`}
        />
        <span className="inset-pin target" style={{ left: `${t.map_x * 100}%`, top: `${t.map_y * 100}%` }} title={target.name} />
        {sites.map((s) => (
          <a
            key={s.rank}
            className="land-pin"
            style={{ left: `${s.map_x * 100}%`, top: `${s.map_y * 100}%` }}
            href={quickmapUrl(s.lat, s.lon, 12)}
            target="_blank"
            rel="noreferrer"
            title={`Landing site #${s.rank}: open in LROC QuickMap`}
          >
            {s.rank}
          </a>
        ))}
        <span className="inset-label">Moon south pole · LOLA 240 m · pole at centre</span>
        <span className="inset-scale" style={{ width: `${barPct}%` }}>
          {SCALE_KM} km
        </span>
      </div>

      <div className="map-key small">
        <span><i className="key-swatch psr" /> Permanent shadow (ice likely)</span>
        <span><i className="key-swatch tgt" /> Target</span>
        <span><i className="key-swatch site" /> Best landing sites</span>
      </div>

      <dl className="terrain">
        <div>
          <dt>Mean slope</dt>
          <dd>{t.mean_slope_deg}°</dd>
        </div>
        <div>
          <dt>Area &lt; 8°</dt>
          <dd>{t.pct_under_8deg}%</dd>
        </div>
        {t.sunlight_pct != null ? (
          <>
            <div>
              <dt>Sunlight</dt>
              <dd>{t.sunlight_pct}%</dd>
            </div>
            <div>
              <dt>In shadow</dt>
              <dd>{t.psr_pct}%</dd>
            </div>
          </>
        ) : (
          <>
            <div>
              <dt>Elevation</dt>
              <dd>{(t.elevation_m / 1000).toFixed(1)} km</dd>
            </div>
            <div>
              <dt>Local relief</dt>
              <dd>{t.relief_m.toLocaleString()} m</dd>
            </div>
          </>
        )}
      </dl>
      <div className="small muted">
        Within {t.radius_km} km of the target (dashed circle). Slopes under 8° are a typical crewed-lander limit. No
        atmosphere.
      </div>

      {sites.length > 0 && (
        <div className="landing">
          <h4>Best landing sites nearby</h4>
          <table className="compare">
            <thead>
              <tr>
                <th>#</th>
                <th>Sunlight</th>
                <th>Flat</th>
                <th>To ice</th>
                <th>From pole</th>
              </tr>
            </thead>
            <tbody>
              {sites.map((s) => (
                <tr key={s.rank}>
                  <td>
                    <a href={quickmapUrl(s.lat, s.lon, 12)} target="_blank" rel="noreferrer">
                      {s.rank}
                    </a>
                  </td>
                  <td>{s.sunlight_pct}%</td>
                  <td>{s.flat_pct}%</td>
                  <td>{s.ice_km} km</td>
                  <td>{s.pole_km} km</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="small muted">{landing.method}. Click a number to view it in LROC QuickMap.</div>
          <div className="small muted">Data: {landing.source}</div>
        </div>
      )}

      <a className="link" href={quickmapUrl(target.lat, target.lon, 20)} target="_blank" rel="noreferrer">
        Open the target in LROC QuickMap →
      </a>
      <div className="small muted">From {t.source}</div>
    </div>
  )
}
