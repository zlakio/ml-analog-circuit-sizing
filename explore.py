#!/usr/bin/env python3
"""Quick look at the OTA dataset before training any model.

Run from the folder containing dataset.csv:
    python3 explore.py
"""
import sys

import pandas as pd

path = sys.argv[1] if len(sys.argv) > 1 else "dataset.csv"
df = pd.read_csv(path)
ok = df[df.valid == 1].copy()

pd.set_option("display.width", 120)
pd.set_option("display.max_columns", 20)

print(f"{len(ok)} valid of {len(df)} ({100 * len(ok) / len(df):.0f}%)\n")

print("Rejection reasons:")
print(df[df.valid == 0].reason.value_counts().to_string(), "\n")

print("Inputs (valid rows):")
print(ok[["WP", "LP", "WL", "LL", "WT", "LT", "IB"]].describe().round(2).to_string(), "\n")

print("Outputs (valid rows):")
print(ok[["gain_db", "f3db_hz", "ugf_hz", "power_uW"]].describe().to_string(), "\n")

# How far apart are the outputs? Large ratios mean the models should predict on a log scale.
for col in ["f3db_hz", "ugf_hz", "power_uW"]:
    print(f"{col}: max/min = {ok[col].max() / ok[col].min():.0f}x")
print()

# Headroom check: M2 needs some drain-source voltage to be a good amplifier.
headroom = ok.vout - ok.vtail
print(f"Valid rows with under 0.1 V of headroom on M2: {(headroom < 0.1).sum()}")
print(f"Valid rows with gain above 60 dB: {(ok.gain_db > 60).sum()}")
print(f"Valid rows with UGF above 1 GHz: {(ok.ugf_hz > 1e9).sum()}\n")

# Which inputs move which outputs? (simple correlation, a first hint only)
ok["logUGF"] = ok.ugf_hz.apply(lambda v: pd.NA if v <= 0 else __import__("math").log10(v))
ok["logPower"] = ok.power_uW.apply(lambda v: pd.NA if v <= 0 else __import__("math").log10(v))
cols = ["WP", "LP", "WL", "LL", "WT", "LT", "IB"]
print("Correlation of inputs with outputs (valid rows):")
print(ok[cols + ["gain_db", "logUGF", "logPower"]].astype(float).corr().loc[cols, ["gain_db", "logUGF", "logPower"]].round(2).to_string())
