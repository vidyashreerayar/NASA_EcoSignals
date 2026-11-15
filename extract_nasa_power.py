"""
Extract real NASA climate values for every Earth candidate site and re-score analogs.

Data: NASA POWER (Prediction Of Worldwide Energy Resources), climatology endpoint.
      Long-term means built from NASA MERRA-2 (temperature) and GPM IMERG / MERRA-2 (precipitation).
      https://power.larc.nasa.gov/docs/services/api/temporal/climatology/
      No login or API key needed.

Variables pulled (annual climatology at each site's lat/lon):
  TS          Earth skin (surface) temperature, annual mean    deg C  -> T_mean
  TS_RANGE    Mean daily skin-temperature range (max - min)    deg C  -> T_range
  PRECTOTCORR Bias-corrected precipitation                     mm/day -> precip (x 365 = mm/yr)
  Period: 2001-2025 climatology. Sources: MERRA-2 (+ GPM IMERG for precipitation).

Usage:
  pip install requests
  python extract_nasa_power.py analog_data.json analog_data_nasa.json
"""
import json, sys, time
import requests

API = "https://power.larc.nasa.gov/api/temporal/climatology/point"
PARAMS = "TS,TS_RANGE,PRECTOTCORR"


def fetch_site(lat, lon, retries=3):
    q = dict(parameters=PARAMS, community="RE", latitude=lat, longitude=lon, format="JSON")
    for attempt in range(retries):
        try:
            r = requests.get(API, params=q, timeout=60)
            r.raise_for_status()
            return r.json()["properties"]["parameter"]
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(3 * (attempt + 1))


def summarize(p):
    """Turn POWER monthly climatology into the four numbers the score uses."""
    t_mean = p["TS"]["ANN"]
    t_range = p["TS_RANGE"]["ANN"]
    precip = p["PRECTOTCORR"]["ANN"] * 365
    return dict(T_mean=round(t_mean, 1), T_range=round(t_range, 1), precip=round(precip))


def main(src, dst):
    data = json.load(open(src))
    for s in data["sites"]:
        p = fetch_site(s["lat"], s["lon"])
        nasa = summarize(p)
        s["estimate"] = {k: s[k] for k in ("T_mean", "T_range", "precip")}  # keep old values
        s.update(nasa)
        s["climate_source"] = "NASA POWER climatology (MERRA-2 / GPM IMERG)"
        print(f"{s['id']:<14} T_mean {nasa['T_mean']:>6}  T_range {nasa['T_range']:>5}  precip {nasa['precip']:>5} mm/yr")
        time.sleep(0.5)  # be polite to the API
    json.dump(data, open(dst, "w"), indent=1)
    print("saved", dst)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "analog_data.json",
         sys.argv[2] if len(sys.argv) > 2 else "analog_data_nasa.json")
