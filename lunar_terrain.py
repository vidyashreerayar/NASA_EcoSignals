"""
Characterize the lunar south pole target from LOLA elevation data and render a map for the app.

Input : LOLA_South Pole.csv  (Latitude, Longitude, Elevation_m)
        A 240 m/pixel polar-stereographic LOLA DEM (LDEM_75S_240M) exported as lat/lon points.
        Data: LRO Lunar Orbiter Laser Altimeter, NASA PDS Geosciences Node.
Output: lunar_terrain.json               terrain metrics for the Moon south-pole target
        lunar_south_pole.jpg             shaded-relief map for the app
        analog_data_scored.json          updated in place: MOON_SP target gets a "terrain" block

How it works
  1. Project every point back to polar-stereographic x/y (metres from the pole) and rebuild the
     square grid, so slopes are computed on the true 240 m spacing.
  2. Within a 10 km radius of the target (a landing-zone-sized area) compute:
       elevation_m        LOLA elevation at the site (relative to the 1737.4 km lunar sphere)
       mean_slope_deg     mean slope at 240 m scale
       pct_under_8deg     share of the area with slope < 8 deg (a typical crewed-lander limit)
       relief_m           95th - 5th percentile elevation
       roughness_m        standard deviation of elevation

Usage:  pip install pandas numpy pillow
        python lunar_terrain.py "LOLA_South Pole.csv" analog_data_scored.json
Runtime: about 1 minute for the full 393 MB file.
"""
import json, sys, time
import numpy as np
import pandas as pd
from PIL import Image

R_MOON = 1737.4e3        # m
RADIUS = 10e3            # m, landing-zone neighbourhood
SLOPE_LIMIT = 8.0        # deg
TARGET_ID = "MOON_SP"


def polar_xy(lat, lon):
    """South polar stereographic (spherical), true scale at the pole."""
    rho = 2 * R_MOON * np.tan(np.pi / 4 + np.deg2rad(lat) / 2)
    lam = np.deg2rad(lon)
    return rho * np.sin(lam), rho * np.cos(lam)


def load_grid(path):
    t0 = time.time()
    cols = dict(Latitude="float64", Longitude="float64", Elevation_m="float32")
    try:
        df = pd.read_csv(path, dtype=cols, engine="pyarrow")
    except Exception:
        df = pd.read_csv(path, dtype=cols)
    print(f"read {len(df):,} points in {time.time() - t0:.0f}s")

    x, y = polar_xy(df.Latitude.to_numpy(), df.Longitude.to_numpy())
    n = int(round(np.sqrt(len(df))))
    xmin, xmax, ymin, ymax = x.min(), x.max(), y.min(), y.max()
    dx = (xmax - xmin) / (n - 1)
    col = np.rint((x - xmin) / dx).astype(int)
    row = np.rint((ymax - y) / dx).astype(int)
    grid = np.full((n, n), np.nan, dtype="float32")
    grid[row.clip(0, n - 1), col.clip(0, n - 1)] = df.Elevation_m.to_numpy()
    filled = np.isfinite(grid).mean() * 100
    print(f"grid {n} x {n}, spacing {dx:.0f} m, {filled:.1f}% filled, extent {(n - 1) * dx / 1000:.0f} km")
    return grid, dict(xmin=xmin, ymax=ymax, dx=dx, n=n)


def metrics(grid, g, lat, lon):
    n, dx = g["n"], g["dx"]
    gy, gx = np.gradient(grid, dx)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))

    tx, ty = polar_xy(lat, lon)
    tc, tr = (tx - g["xmin"]) / dx, (g["ymax"] - ty) / dx
    r = int(np.ceil(RADIUS / dx))
    r0, r1 = max(0, int(tr) - r), min(n, int(tr) + r + 1)
    c0, c1 = max(0, int(tc) - r), min(n, int(tc) + r + 1)
    rr, cc = np.mgrid[r0:r1, c0:c1]
    near = np.hypot((rr - tr) * dx, (cc - tc) * dx) <= RADIUS
    z = grid[r0:r1, c0:c1][near]
    s = slope[r0:r1, c0:c1][near]
    ok = np.isfinite(z) & np.isfinite(s)
    z, s = z[ok], s[ok]
    h = grid[int(round(tr)), int(round(tc))]
    return slope, dict(
        elevation_m=int(round(float(h))),
        mean_slope_deg=round(float(s.mean()), 1),
        pct_under_8deg=round(float((s < SLOPE_LIMIT).mean() * 100), 1),
        relief_m=int(round(float(np.percentile(z, 95) - np.percentile(z, 5)))),
        roughness_m=int(round(float(z.std()))),
        radius_km=RADIUS / 1000,
        map_x=round(float(tc / (n - 1)), 4),     # pin position on the rendered map (0-1)
        map_y=round(float(tr / (n - 1)), 4),
        extent_km=round((n - 1) * dx / 1000),
        source="LRO LOLA LDEM 240 m polar (NASA PDS)",
    )


def render(grid, slope, out, size=1000):
    z = np.where(np.isfinite(grid), grid, np.nanmedian(grid))
    gy, gx = np.gradient(z, 240)
    az, alt = np.deg2rad(315), np.deg2rad(30)
    sl = np.pi / 2 - np.arctan(np.hypot(gx, gy) * 2)
    aspect = np.arctan2(-gx, gy)
    shade = np.clip(np.sin(alt) * np.sin(sl) + np.cos(alt) * np.cos(sl) * np.cos(az - aspect), 0, 1)
    lo, hi = np.percentile(z, [1, 99])
    t = np.clip((z - lo) / (hi - lo), 0, 1)[..., None]
    low, high = np.array([18, 24, 38]), np.array([214, 222, 235])     # deep blue-grey -> pale grey
    rgb = (low + (high - low) * t) * (0.35 + 0.65 * shade[..., None])
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize((size, size), Image.LANCZOS).save(out, quality=85)


def main(csv_path, data_path):
    grid, g = load_grid(csv_path)
    data = json.load(open(data_path))
    tgt = next(t for t in data["targets"] if t["id"] == TARGET_ID)
    slope, m = metrics(grid, g, tgt["lat"], tgt["lon"])
    tgt["terrain"] = m
    print(f"{TARGET_ID}: elev {m['elevation_m']} m, mean slope {m['mean_slope_deg']} deg, "
          f"{m['pct_under_8deg']}% of the 10 km zone under 8 deg, relief {m['relief_m']} m")
    json.dump(m, open("lunar_terrain.json", "w"), indent=1)
    json.dump(data, open(data_path, "w"), indent=1)
    render(grid, slope, "lunar_south_pole.jpg")
    print("saved lunar_terrain.json, lunar_south_pole.jpg, updated", data_path)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "LOLA_South Pole.csv",
         sys.argv[2] if len(sys.argv) > 2 else "analog_data_scored.json")
