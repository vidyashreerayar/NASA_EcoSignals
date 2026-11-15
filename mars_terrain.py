"""
Characterize Mars target sites from the MOLA global elevation grid, and render a Mars map.

Input : MOLA Mars Global.csv  (Latitude, Longitude 0-360 E, Elevation_m; 0.25 deg grid)
        Data: Mars Global Surveyor MOLA MEGDR, NASA PDS Geosciences Node.
Output: mars_terrain.json        terrain metrics per Mars target
        mars_mola.jpg             shaded-relief elevation map for the app (equirectangular)
        analog_data_scored.json   updated in place: targets get a "terrain" block

Metrics within a 50 km radius of each target:
  elevation_m       MOLA elevation at the site (vs. Mars datum)
  pressure_pa       surface pressure estimate, P = 610 Pa * exp(-h / 11.1 km)
  relief_m          local relief, 95th - 5th percentile elevation
  roughness_m       standard deviation of elevation
  mean_slope_deg    mean slope at ~15 km grid scale (regional, not boulder-scale)
  elev_percentile   share of Mars that is lower than this site

Usage:  pip install pandas numpy pillow
        python mars_terrain.py "MOLA Mars Global.csv" analog_data_scored.json
"""
import json, sys
import numpy as np
import pandas as pd
from PIL import Image

R_MARS = 3389.5e3          # m
P_DATUM, H_SCALE = 610.0, 11100.0
RADIUS = 50e3              # m, neighbourhood for terrain stats


def load_grid(path):
    df = pd.read_csv(path)
    lats = np.sort(df.Latitude.unique())[::-1]          # north -> south
    lons = np.sort(df.Longitude.unique())               # 0 -> 360 E
    grid = (df.pivot(index="Latitude", columns="Longitude", values="Elevation_m")
              .loc[lats, lons].to_numpy(dtype=float))
    return lats, lons, grid


def slope_deg(lats, grid, step_deg):
    dy = np.deg2rad(step_deg) * R_MARS
    dx = dy * np.cos(np.deg2rad(lats))[:, None]
    gy, gx = np.gradient(grid)
    return np.degrees(np.arctan(np.hypot(gx / dx, gy / dy)))


def site_metrics(lat, lon, lats, lons, grid, slope):
    lon360 = lon % 360
    la, lo = np.deg2rad(lats)[:, None], np.deg2rad(lons)[None, :]
    p1, l1 = np.deg2rad(lat), np.deg2rad(lon360)
    # haversine distance from the site to every grid cell
    d = 2 * R_MARS * np.arcsin(np.sqrt(np.sin((la - p1) / 2) ** 2 +
                                       np.cos(la) * np.cos(p1) * np.sin((lo - l1) / 2) ** 2))
    near = d <= RADIUS
    i, j = np.unravel_index(np.argmin(d), d.shape)
    h = grid[i, j]
    z = grid[near]
    return dict(
        elevation_m=int(round(h)),
        pressure_pa=int(round(P_DATUM * np.exp(-h / H_SCALE))),
        relief_m=int(round(np.percentile(z, 95) - np.percentile(z, 5))),
        roughness_m=int(round(z.std())),
        mean_slope_deg=round(float(slope[near].mean()), 2),
        elev_percentile=round(float((grid < h).mean() * 100), 1),
        cells=int(near.sum()),
    )


def render_map(lats, lons, grid, out, width=1440):
    # hillshade (sun from the north-west) blended with a single-hue elevation ramp
    gy, gx = np.gradient(grid)
    az, alt = np.deg2rad(315), np.deg2rad(40)
    slope = np.pi / 2 - np.arctan(np.hypot(gx, gy) / 1500)
    aspect = np.arctan2(-gx, gy)
    shade = np.clip(np.sin(alt) * np.sin(slope) + np.cos(alt) * np.cos(slope) * np.cos(az - aspect), 0, 1)
    lo, hi = np.percentile(grid, [1, 99.5])
    t = np.clip((grid - lo) / (hi - lo), 0, 1)[..., None]
    low, high = np.array([46, 20, 10]), np.array([246, 205, 170])       # deep rust -> pale sand
    rgb = (low + (high - low) * t) * (0.45 + 0.55 * shade[..., None])
    # roll so the map runs -180 .. 180 like the Earth map
    rgb = np.roll(rgb, rgb.shape[1] // 2, axis=1)
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    img.resize((width, width // 2), Image.LANCZOS).save(out, quality=85)


def main(csv_path, data_path):
    lats, lons, grid = load_grid(csv_path)
    slope = slope_deg(lats, grid, step_deg=lats[0] - lats[1])
    data = json.load(open(data_path))
    out = {}
    for t in data["targets"]:
        if t["body"] != "Mars":
            continue
        m = site_metrics(t["lat"], t["lon"], lats, lons, grid, slope)
        m["source"] = "MGS MOLA MEGDR 0.25 deg (NASA PDS)"
        t["terrain"] = out[t["id"]] = m
        print(f"{t['id']:<13} elev {m['elevation_m']:>6} m  P {m['pressure_pa']:>4} Pa  relief {m['relief_m']:>5} m"
              f"  slope {m['mean_slope_deg']:>4} deg  lower than {100 - m['elev_percentile']:.0f}% of Mars")
    json.dump(out, open("mars_terrain.json", "w"), indent=1)
    json.dump(data, open(data_path, "w"), indent=1)
    render_map(lats, lons, grid, "mars_mola.jpg")
    print("saved mars_terrain.json, mars_mola.jpg, updated", data_path)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "MOLA Mars Global.csv",
         sys.argv[2] if len(sys.argv) > 2 else "analog_data_scored.json")
