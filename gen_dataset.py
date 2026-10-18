#!/usr/bin/env python3
"""Generate a dataset for the 5-transistor OTA.

For each sample: draw random transistor sizes, write a netlist, run ngspice
in batch mode, parse the printed results, and record whether the circuit is a
sensible working design. Everything is written to a CSV file.

Run inside the IIC-OSIC-TOOLS container, from the folder containing this file:
    python3 gen_dataset.py -n 20 --out test.csv        # quick test
    python3 gen_dataset.py -n 3000 --out dataset.csv   # real run
"""
import argparse
import csv
import math
import os
import random
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor

# Path to the SKY130 ngspice library (same one used in the hand-written netlists).
LIB = "/foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice"
VDD = 1.8

# Design variables and their ranges (W and L in um, IB in uA). Sampled log-uniformly.
# WP, LP : input pair M1 = M2
# WL, LL : PMOS mirror load M3 = M4
# WT, LT : tail source M5 (M6 uses the same L so the mirror is accurate; W6 is fixed at 2)
# IB     : reference current into M6
RANGES = {
    "WP": (1.0, 40.0),
    "LP": (0.5, 2.0),
    "WL": (1.0, 40.0),
    "LL": (0.5, 2.0),
    "WT": (2.0, 16.0),
    "LT": (0.5, 2.0),
    "IB": (5.0, 30.0),
}

TEMPLATE = """* 5T OTA, SKY130 (generated)
.lib @LIB@ tt

Vdd vdd 0 @VDD@
Vinn inn 0 dc 1.0
Vinp inp 0 dc 1.0 ac 1
Ib vdd nb @IB@u
CL out 0 1p

XM6 nb nb 0 0 sky130_fd_pr__nfet_01v8 W=2 L=@LT@
XM5 tail nb 0 0 sky130_fd_pr__nfet_01v8 W=@WT@ L=@LT@
XM1 d1 inp tail 0 sky130_fd_pr__nfet_01v8 W=@WP@ L=@LP@
XM2 out inn tail 0 sky130_fd_pr__nfet_01v8 W=@WP@ L=@LP@
XM3 d1 d1 vdd vdd sky130_fd_pr__pfet_01v8 W=@WL@ L=@LL@
XM4 out d1 vdd vdd sky130_fd_pr__pfet_01v8 W=@WL@ L=@LL@

.nodeset v(out)=1.0 v(d1)=1.0

.control
op
print v(out) v(d1) v(tail) v(nb)
print -i(Vdd)
ac dec 20 10 10G
meas ac dcgain find vdb(out) at=10
let tgt = dcgain - 3
meas ac f3db when vdb(out)=$&tgt fall=1
meas ac ugf when vdb(out)=0 fall=1
.endc
.end
"""

# Matches lines such as "v(out) = 6.663979e-01" or "dcgain = 3.55826e+01".
LINE_RE = re.compile(r"^\s*(-?[A-Za-z_][\w.()]*)\s*=\s*([-+]?[\d.]+(?:[eE][-+]?\d+)?)\s*$")


def sample_sizing(rng):
    """Draw one random sizing, log-uniform within each range, rounded for readable netlists."""
    sizing = {}
    for name, (lo, hi) in RANGES.items():
        value = math.exp(rng.uniform(math.log(lo), math.log(hi)))
        sizing[name] = round(value, 2)
    return sizing


def build_netlist(sizing):
    text = TEMPLATE.replace("@LIB@", LIB).replace("@VDD@", str(VDD))
    for name, value in sizing.items():
        text = text.replace(f"@{name}@", str(value))
    return text


def parse_output(stdout):
    """Pull 'name = number' pairs out of the ngspice output."""
    results = {}
    for line in stdout.splitlines():
        match = LINE_RE.match(line)
        if match:
            results[match.group(1)] = float(match.group(2))
    return results


def run_one(sizing):
    """Simulate one sizing. Returns a dict of results plus a valid flag and a reason."""
    row = dict(sizing)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "ota.cir")
        with open(path, "w") as f:
            f.write(build_netlist(sizing))
        try:
            proc = subprocess.run(
                ["ngspice", "-b", path], capture_output=True, text=True, timeout=60
            )
        except subprocess.TimeoutExpired:
            row.update(valid=0, reason="timeout")
            return row

    out = parse_output(proc.stdout)

    # Without the operating point and the DC gain there is nothing to record.
    basics = ["v(out)", "v(d1)", "v(tail)", "-i(vdd)", "dcgain"]
    missing = [k for k in basics if k not in out]
    if missing:
        row.update(valid=0, reason="simulation failed: missing " + ",".join(missing))
        return row

    # Record everything that was measured, even for circuits that get rejected,
    # so the reason for each rejection can be checked later.
    row.update(
        vout=out["v(out)"],
        vd1=out["v(d1)"],
        vtail=out["v(tail)"],
        i_supply_uA=out["-i(vdd)"] * 1e6,
        power_uW=VDD * out["-i(vdd)"] * 1e6,
        gain_db=out["dcgain"],
    )
    if "f3db" in out:
        row["f3db_hz"] = out["f3db"]
    if "ugf" in out:
        row["ugf_hz"] = out["ugf"]

    # Sanity filters: node voltages away from the rails, tail source not collapsed,
    # and a real amplifier (gain above 0 dB with measurable f3db and unity-gain frequency).
    reason = ""
    if not 0.15 <= row["vout"] <= VDD - 0.15:
        reason = "output near a rail"
    elif not 0.15 <= row["vd1"] <= VDD - 0.15:
        reason = "mirror node near a rail"
    elif row["vtail"] < 0.1:
        reason = "tail source in triode"
    elif row["gain_db"] <= 0:
        reason = "no gain (DC gain at or below 0 dB)"
    elif "ugf_hz" not in row:
        reason = "unity-gain frequency not found"
    elif "f3db_hz" not in row:
        reason = "f3db not found"
    elif row["ugf_hz"] <= 0:
        reason = "no gain (non-positive unity-gain frequency)"
    row.update(valid=0 if reason else 1, reason=reason)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-n", type=int, default=20, help="number of random sizings to simulate")
    parser.add_argument("--out", default="dataset.csv", help="output CSV file")
    parser.add_argument("--seed", type=int, default=0, help="random seed (for reproducible datasets)")
    parser.add_argument("--workers", type=int, default=4, help="parallel ngspice processes")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    sizings = [sample_sizing(rng) for _ in range(args.n)]

    columns = list(RANGES) + [
        "vout", "vd1", "vtail", "i_supply_uA", "power_uW",
        "gain_db", "f3db_hz", "ugf_hz", "valid", "reason",
    ]
    rows = []
    # Each row is written to the CSV as soon as it finishes, so if the run is
    # interrupted the rows completed so far are still saved.
    with open(args.out, "w", newline="") as f, ThreadPoolExecutor(max_workers=args.workers) as pool:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for i, row in enumerate(pool.map(run_one, sizings), start=1):
            rows.append(row)
            writer.writerow(row)
            f.flush()
            if i % 50 == 0 or i == args.n:
                valid = sum(r["valid"] for r in rows)
                print(f"{i}/{args.n} simulated, {valid} valid so far", flush=True)

    valid = sum(r["valid"] for r in rows)
    print(f"Done. {valid}/{len(rows)} valid ({100 * valid / len(rows):.0f}%). Saved to {args.out}")
    reasons = {}
    for r in rows:
        if not r["valid"]:
            reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    for reason, count in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"  rejected ({count}): {reason}")


if __name__ == "__main__":
    main()