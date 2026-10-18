#!/usr/bin/env python3
"""Train and compare surrogate models for the 5T OTA dataset.

Inputs : the 7 sizing variables, log10-scaled.
Targets: DC gain (dB), log10(unity-gain frequency), log10(power).
Models : linear regression, random forest, small neural network (MLP).

Run from the folder containing dataset.csv:
    python3 train_models.py
    python3 train_models.py --learning-curve      # also show accuracy vs. training-set size

Needs: pip install --user scikit-learn matplotlib pandas numpy
"""
import argparse
import os

import matplotlib

matplotlib.use("Agg")  # save figures to files; no display needed
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

INPUTS = ["WP", "LP", "WL", "LL", "WT", "LT", "IB"]
TARGETS = ["gain_db", "log_ugf", "log_power"]


def load_data(path):
    df = pd.read_csv(path)
    ok = df[df.valid == 1]
    print(f"{len(ok)} valid rows")
    # Drop marginal designs: little headroom on M2, or barely any gain.
    ok = ok[(ok.vout - ok.vtail >= 0.1) & (ok.gain_db >= 10)].copy()
    print(f"{len(ok)} rows after the headroom/gain filter\n")
    X = np.log10(ok[INPUTS])
    y = pd.DataFrame(
        {
            "gain_db": ok.gain_db,
            "log_ugf": np.log10(ok.ugf_hz),
            "log_power": np.log10(ok.power_uW),
        }
    )
    return X, y


def make_models(seed):
    mlp = TransformedTargetRegressor(
        regressor=make_pipeline(
            StandardScaler(),
            MLPRegressor(hidden_layer_sizes=(64, 64), max_iter=3000, early_stopping=True, random_state=seed),
        ),
        transformer=StandardScaler(),
    )
    return {
        "linear": make_pipeline(StandardScaler(), LinearRegression()),
        "random_forest": RandomForestRegressor(n_estimators=300, random_state=seed, n_jobs=-1),
        "mlp": mlp,
    }


def evaluate(model, X_train, y_train, X_test, y_test):
    pred_test = model.predict(X_test)
    pred_train = model.predict(X_train)
    rows = []
    for j, target in enumerate(TARGETS):
        actual = y_test.iloc[:, j].values
        row = {
            "target": target,
            "r2_train": r2_score(y_train.iloc[:, j], pred_train[:, j]),
            "r2_test": r2_score(actual, pred_test[:, j]),
            # gain: error in dB. log targets: error in decades (powers of ten).
            "mae": mean_absolute_error(actual, pred_test[:, j]),
            "mean_pct_error": np.nan,
        }
        if target.startswith("log_"):
            true_vals = 10 ** actual
            row["mean_pct_error"] = 100 * np.mean(np.abs(10 ** pred_test[:, j] - true_vals) / true_vals)
        rows.append(row)
    return rows, pred_test


def plot_predictions(name, y_test, pred, outdir):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for j, target in enumerate(TARGETS):
        actual = y_test.iloc[:, j].values
        predicted = pred[:, j]
        ax = axes[j]
        ax.scatter(actual, predicted, s=6, alpha=0.5)
        lo, hi = min(actual.min(), predicted.min()), max(actual.max(), predicted.max())
        ax.plot([lo, hi], [lo, hi], "r--", linewidth=1)
        ax.set_xlabel(f"simulated {target}")
        ax.set_ylabel(f"predicted {target}")
        ax.set_title(f"{name}: {target}")
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, f"pred_vs_actual_{name}.png"), dpi=150)
    plt.close(fig)


def learning_curve(X_train, y_train, X_test, y_test, seed, outdir):
    """Test accuracy (mean R2 over the three targets) vs. number of training samples."""
    fractions = [0.1, 0.25, 0.5, 0.75, 1.0]
    order = np.random.RandomState(seed).permutation(len(X_train))
    sizes = [max(30, int(f * len(X_train))) for f in fractions]
    curves = {name: [] for name in make_models(seed)}
    for n in sizes:
        idx = order[:n]
        for name, model in make_models(seed).items():
            model.fit(X_train.iloc[idx], y_train.iloc[idx])
            pred = model.predict(X_test)
            curves[name].append(np.mean([r2_score(y_test.iloc[:, j], pred[:, j]) for j in range(len(TARGETS))]))
    print("\nLearning curve (mean test R2 over the three targets):")
    table = pd.DataFrame(curves, index=sizes)
    table.index.name = "training samples"
    print(table.round(3).to_string())
    fig, ax = plt.subplots(figsize=(6, 4.5))
    for name, values in curves.items():
        ax.plot(sizes, values, marker="o", label=name)
    ax.set_xlabel("training samples")
    ax.set_ylabel("mean test R2")
    ax.set_title("Accuracy vs. training-set size")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "learning_curve.png"), dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", default="dataset.csv")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--outdir", default="figures", help="folder for the plots")
    parser.add_argument("--learning-curve", action="store_true")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    X, y = load_data(args.data)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=args.seed)
    print(f"Training on {len(X_train)} rows, testing on {len(X_test)} rows\n")

    all_rows = []
    for name, model in make_models(args.seed).items():
        model.fit(X_train, y_train)
        rows, pred = evaluate(model, X_train, y_train, X_test, y_test)
        for row in rows:
            row["model"] = name
        all_rows.extend(rows)
        plot_predictions(name, y_test, pred, args.outdir)

    results = pd.DataFrame(all_rows)[["model", "target", "r2_train", "r2_test", "mae", "mean_pct_error"]]
    print("Results (mae is in dB for gain_db and in decades for the log targets):")
    print(results.round(3).to_string(index=False))
    results.to_csv("results_models.csv", index=False)
    print(f"\nSaved results_models.csv and plots in {args.outdir}/")

    if args.learning_curve:
        learning_curve(X_train, y_train, X_test, y_test, args.seed, args.outdir)


if __name__ == "__main__":
    main()
