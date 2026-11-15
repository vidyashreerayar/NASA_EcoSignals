"""
Re-score every Earth site against every Moon/Mars target.

Usage (after extract_nasa_power.py):
  python rescore.py analog_data_nasa.json

Outputs:
  earth_sites_scored.csv   one row per site, a score (0-100) per target + best match
  analog_data_scored.json  same data + scores, for the React app
  Console report: top 6 sites per target, validation check, estimate-vs-NASA changes

Score = 50% climate similarity + 50% geology/feature match
  Climate: Gaussian similarity on mean surface temperature, diurnal range,
           log precipitation and NDVI. Moon/Mars targets are clamped to the most
           extreme values Earth can reach (Earth can't be -170 C).
  Geology: share of the target's features (basalt, ice, caves, ...) the site has.
"""
import csv, json, math, sys

EARTH_BOUNDS = dict(T_mean=(-55, 35), T_range=(0, 45))
SCALES = dict(T_mean=20, T_range=12, logp=0.8, ndvi=0.12)
WEIGHTS = dict(T_mean=1, T_range=1, logp=1.5, ndvi=1.5)
W_CLIMATE = 0.5
KNOWN_MUST_RANK = 6  # validation: a known analog must appear in each target's top N


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def score(site, tgt):
    g = lambda d, s: math.exp(-0.5 * (d / s) ** 2)
    parts = dict(
        T_mean=g(site["T_mean"] - clamp(tgt["T_mean"], *EARTH_BOUNDS["T_mean"]), SCALES["T_mean"]),
        T_range=g(site["T_range"] - clamp(tgt["T_range"], *EARTH_BOUNDS["T_range"]), SCALES["T_range"]),
        logp=g(math.log10(site["precip"] + 1) - math.log10(tgt["precip"] + 1), SCALES["logp"]),
        ndvi=g(site["ndvi"] - tgt["ndvi"], SCALES["ndvi"]),
    )
    climate = sum(parts[k] * WEIGHTS[k] for k in parts) / sum(WEIGHTS.values())
    tf = set(tgt["flags"])
    geology = len(tf & set(site["flags"])) / len(tf)
    return round(100 * (W_CLIMATE * climate + (1 - W_CLIMATE) * geology), 1)


def rank(sites, targets):
    return {t["id"]: sorted(sites, key=lambda s: -score(s, t)) for t in targets}


def main(path):
    data = json.load(open(path))
    sites, targets, flags = data["sites"], data["targets"], data["flags"]

    # --- scores per site
    for s in sites:
        s["scores"] = {t["id"]: score(s, t) for t in targets}
        s["best_match"] = max(s["scores"], key=s["scores"].get)

    # --- report: top sites per target + validation
    print("\nTOP MATCHES PER TARGET  (k = known analog, n = new candidate)")
    ok = True
    for tid, ranked in rank(sites, targets).items():
        top = ranked[:KNOWN_MUST_RANK]
        print(f"  {tid:<13}", ", ".join(f"{s['id']} {s['scores'][tid]}{s['status'][0]}" for s in top))
        if not any(s["status"] == "known" for s in top):
            ok = False
            print(f"    !! no known analog in top {KNOWN_MUST_RANK} for {tid}")
    print("\nVALIDATION:", "PASS - known analogs rank high for every target" if ok else "CHECK the targets flagged above")

    # --- how much did NASA data move rankings vs. the estimates?
    if all("estimate" in s for s in sites):
        est_sites = [{**s, **s["estimate"]} for s in sites]
        est_rank = rank(est_sites, targets)
        print("\nRANK CHANGES (estimate -> NASA), sites moving 3+ places")
        for tid, ranked in rank(sites, targets).items():
            before = [s["id"] for s in est_rank[tid]]
            for i, s in enumerate(ranked):
                j = before.index(s["id"])
                if abs(i - j) >= 3 and min(i, j) < 10:
                    print(f"  {tid:<13} {s['id']:<12} #{j+1} -> #{i+1}")
        print("\nBIGGEST CLIMATE CORRECTIONS")
        for s in sorted(sites, key=lambda s: -abs(s["T_mean"] - s["estimate"]["T_mean"]))[:5]:
            e = s["estimate"]
            print(f"  {s['id']:<12} T_mean {e['T_mean']} -> {s['T_mean']}   precip {e['precip']} -> {s['precip']}")

    # --- outputs
    tids = [t["id"] for t in targets]
    with open("earth_sites_scored.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "name", "country", "status", "best_match", "best_score"] + [f"score_{t}" for t in tids] +
                   ["lat", "lon", "T_mean", "T_range", "precip", "ndvi"] + flags + ["used_for"])
        for s in sorted(sites, key=lambda s: -s["scores"][s["best_match"]]):
            w.writerow([s["id"], s["name"], s["country"], s["status"], s["best_match"], s["scores"][s["best_match"]]] +
                       [s["scores"][t] for t in tids] +
                       [s["lat"], s["lon"], s["T_mean"], s["T_range"], s["precip"], s["ndvi"]] +
                       [int(f in s["flags"]) for f in flags] + [s["used_for"]])
    json.dump(data, open("analog_data_scored.json", "w"), indent=1)
    print("\nSaved earth_sites_scored.csv and analog_data_scored.json")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "analog_data_nasa.json")
