"""
Lunar south pole landing-site finder.

Combines three LRO-derived maps on the same 240 m polar grid:
  slope        from LOLA elevation      (LOLA_South Pole.csv, via lunar_terrain.py)
  sunlight     average solar illumination, 18.6-year average   (AVGVISIB_65S_240M_201608.TIF)
  ice access   permanently shadowed regions, PSRs               (LPSR_65S_240M_201608.TIF)
Sunlight and PSR maps: Mazarico et al. 2011, NASA Goddard PGDA  https://pgda.gsfc.nasa.gov/products/69

For every 240 m cell within SEARCH_KM of the pole it looks at the surrounding ~2 km patch and scores:
  sunlight  mean illumination of the patch (solar power, thermal stability)    weight 0.45
  flatness  share of the patch with slope < 8 deg (crewed-lander limit)       weight 0.35
  ice       closeness to the nearest PSR (1 at the edge, 0 at >= 10 km)       weight 0.20
Cells inside a PSR, or patches less than 80% flat, are excluded. The best TOP_N patches at least
MIN_SEP_KM apart are reported.

Also adds sunlight / shadow stats for the MOON_SP target and re-renders lunar_south_pole.jpg as a zoomed
160 x 160 km view around the pole with PSRs tinted blue.

Usage (inside the .venv):
  pip install rasterio scipy
  python landing_sites.py "LOLA_South Pole.csv" AVGVISIB_65S_240M_201608.TIF LPSR_65S_240M_201608.TIF analog_data_scored.json
"""
import json, sys
import numpy as np
import rasterio
from PIL import Image
from scipy.ndimage import uniform_filter, distance_transform_edt

from lunar_terrain import load_grid, polar_xy, R_MOON

SEARCH_KM, PATCH_KM, MIN_SEP_KM, TOP_N = 70, 2.0, 8.0, 6
CROP_KM = 80          # the app map shows the central 160 x 160 km around the pole
SLOPE_LIMIT, MIN_FLAT, ICE_KM = 8.0, 0.8, 10.0
W_SUN, W_FLAT, W_ICE = 0.45, 0.35, 0.20


def sample_raster(path, x, y):
    """Nearest-neighbour sample of a polar-stereographic GeoTIFF at metre coordinates x, y."""
    with rasterio.open(path) as src:
        print(f"{path}: {src.width}x{src.height}, {src.res[0]:.0f} m, crs: {src.crs.to_proj4() if src.crs else 'none'}")
        band = src.read(1, masked=True).astype("float32").filled(np.nan)
        band = band * float(src.scales[0] or 1.0) + float(src.offsets[0] or 0.0)
        inv = ~src.transform
        col, row = inv * (x, y)
        col, row = np.floor(col).astype(int), np.floor(row).astype(int)
        ok = (row >= 0) & (row < src.height) & (col >= 0) & (col < src.width)
        out = np.full(x.shape, np.nan, dtype="float32")
        out[ok] = band[row[ok], col[ok]]
    return out


def latlon(x, y):
    rho = np.hypot(x, y)
    return np.degrees(2 * np.arctan(rho / (2 * R_MOON)) - np.pi / 2), np.degrees(np.arctan2(x, y))


def render(grid, psr, out, size=1000):
    z = np.where(np.isfinite(grid), grid, np.nanmedian(grid))
    gy, gx = np.gradient(z, 240)
    az, alt = np.deg2rad(315), np.deg2rad(30)
    sl = np.pi / 2 - np.arctan(np.hypot(gx, gy) * 2)
    shade = np.clip(np.sin(alt) * np.sin(sl) + np.cos(alt) * np.cos(sl) * np.cos(az - np.arctan2(-gx, gy)), 0, 1)
    lo, hi = np.percentile(z, [1, 99])
    t = np.clip((z - lo) / (hi - lo), 0, 1)[..., None]
    rgb = (np.array([18, 24, 38]) + np.array([196, 198, 197]) * t) * (0.35 + 0.65 * shade[..., None])
    blue = np.array([57, 135, 229])
    rgb[psr] = rgb[psr] * 0.35 + blue * 0.65
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize((size, size), Image.LANCZOS).save(out, quality=85)


def main(csv_path, illum_path, psr_path, data_path):
    grid, g = load_grid(csv_path)
    n, dx = g["n"], g["dx"]
    cols, rows = np.meshgrid(np.arange(n), np.arange(n))
    X = g["xmin"] + cols * dx
    Y = g["ymax"] - rows * dx

    pc, pr = (0 - g["xmin"]) / dx, (g["ymax"] - 0) / dx          # pole pixel
    h = int(CROP_KM * 1000 / dx)
    r0, r1 = max(0, int(pr) - h), min(n, int(pr) + h + 1)
    c0, c1 = max(0, int(pc) - h), min(n, int(pc) + h + 1)
    to_map = lambda r, c: (round((c - c0) / (c1 - 1 - c0), 4), round((r - r0) / (r1 - 1 - r0), 4))

    illum = sample_raster(illum_path, X, Y)
    if np.nanmax(illum) > 1.5:          # some releases store percent
        illum = illum / 100.0
    psr_raw = sample_raster(psr_path, X, Y)
    vals = np.unique(psr_raw[np.isfinite(psr_raw)])
    print("sunlight fraction:", np.nanmin(illum), "-", np.nanmax(illum), "| PSR values:", vals[:10])
    psr = np.isfinite(psr_raw) & (psr_raw > 0.5)
    print(f"PSR cells: {psr.mean() * 100:.1f}% of the map")

    gy, gx = np.gradient(grid, dx)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    k = int(round(PATCH_KM * 1000 / dx)) | 1
    flat = uniform_filter(np.nan_to_num(slope < SLOPE_LIMIT, nan=0).astype("float32"), k)
    sun = uniform_filter(np.nan_to_num(illum, nan=0), k)
    d_ice = distance_transform_edt(~psr) * dx / 1000            # km to nearest PSR cell
    ice = np.clip(1 - d_ice / ICE_KM, 0, 1)

    score = W_SUN * sun + W_FLAT * flat + W_ICE * ice
    ok = (np.hypot(X, Y) <= SEARCH_KM * 1000) & ~psr & (flat >= MIN_FLAT) & np.isfinite(grid)
    score = np.where(ok, score, -1)

    picks = []
    for idx in np.argsort(score, axis=None)[::-1]:
        r, c = divmod(int(idx), n)
        if score[r, c] < 0 or len(picks) == TOP_N:
            break
        if any(np.hypot((r - pr) * dx, (c - pc) * dx) < MIN_SEP_KM * 1000 for pr, pc in [(p["_r"], p["_c"]) for p in picks]):
            continue
        lat, lon = latlon(X[r, c], Y[r, c])
        picks.append(dict(
            _r=r, _c=c,
            rank=len(picks) + 1,
            lat=round(float(lat), 3), lon=round(float(lon), 2),
            score=round(float(score[r, c]) * 100, 1),
            sunlight_pct=round(float(sun[r, c]) * 100, 1),
            flat_pct=round(float(flat[r, c]) * 100, 1),
            ice_km=round(float(d_ice[r, c]), 1),
            elevation_m=int(round(float(grid[r, c]))),
            pole_km=round(float(np.hypot(X[r, c], Y[r, c])) / 1000, 1),
            map_x=to_map(r, c)[0], map_y=to_map(r, c)[1],
        ))
    for p in picks:
        p.pop("_r"); p.pop("_c")
        print(f"#{p['rank']}  {p['lat']:.3f}, {p['lon']:.2f}  score {p['score']}  sun {p['sunlight_pct']}%  "
              f"flat {p['flat_pct']}%  ice {p['ice_km']} km  ({p['pole_km']} km from pole)")

    data = json.load(open(data_path))
    tgt = next(t for t in data["targets"] if t["id"] == "MOON_SP")
    tx, ty = polar_xy(tgt["lat"], tgt["lon"])
    zone = np.hypot(X - tx, Y - ty) <= tgt.get("terrain", {}).get("radius_km", 10) * 1000
    tr, tc = int(round((g["ymax"] - ty) / dx)), int(round((tx - g["xmin"]) / dx))
    tgt.setdefault("terrain", {}).update(
        sunlight_pct=round(float(np.nanmean(illum[zone])) * 100, 1),
        psr_pct=round(float(psr[zone].mean()) * 100, 1),
        ice_km=round(float(d_ice[tr, tc]), 1),
        map_x=to_map(tr, tc)[0], map_y=to_map(tr, tc)[1],
        extent_km=round((c1 - 1 - c0) * dx / 1000),
    )
    data["landing_sites"] = dict(
        sites=picks,
        method=f"{PATCH_KM:.0f} km patches within {SEARCH_KM} km of the pole; score = {W_SUN} sunlight + "
               f"{W_FLAT} flatness (<{SLOPE_LIMIT:.0f} deg) + {W_ICE} closeness to permanent shadow",
        source="LOLA 240 m DEM; Mazarico et al. 2011 average illumination & PSR maps (NASA GSFC PGDA)",
    )
    json.dump(data, open(data_path, "w"), indent=1)
    json.dump(data["landing_sites"], open("landing_sites.json", "w"), indent=1)
    render(grid[r0:r1, c0:c1], psr[r0:r1, c0:c1], "lunar_south_pole.jpg")
    t = tgt["terrain"]
    print(f"MOON_SP target zone: sunlight {t['sunlight_pct']}%, {t['psr_pct']}% in permanent shadow, "
          f"nearest PSR {t['ice_km']} km")
    print("saved landing_sites.json, lunar_south_pole.jpg (PSRs in blue), updated", data_path)


if __name__ == "__main__":
    a = sys.argv[1:] + [None] * 4
    main(a[0] or "LOLA_South Pole.csv", a[1] or "AVGVISIB_65S_240M_201608.TIF",
         a[2] or "LPSR_65S_240M_201608.TIF", a[3] or "analog_data_scored.json")
