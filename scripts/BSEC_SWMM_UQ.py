"""
SWMM Uncertainty Quantification
Latin Hypercube Sampling
Peak Depth on surface nodes only
Outputs: uq_results.csv, uq_uncertainty.csv, uq_sensitivity.csv
"""

import argparse
import os
import tempfile
import warnings

import numpy as np
import pandas as pd
from scipy.stats import qmc, spearmanr

from swmm_api import SwmmInput
from pyswmm import Simulation, Nodes

# ---------------------------------------------------------------------------
# 1. CONFIGURATION & PARAMETERS
# ---------------------------------------------------------------------------

SURFACE_NODES: list[str] = []

PARAM_DEFS = [
    {"label": "SubcatchWidth", "param": "width", "mode": "multiplier", "low": 0.50, "high": 1.50},
    {"label": "%Imperv", "param": "imperv", "mode": "multiplier", "low": 0.80, "high": 1.20},
    {"label": "dstore_imperv_in", "param": "dstore_imperv", "mode": "absolute", "low": 0.08, "high": 0.20},
    {"label": "dstore_perv_in", "param": "dstore_perv", "mode": "absolute", "low": 0.07, "high": 0.40},
    {"label": "n_perv", "param": "N_perv", "mode": "absolute", "low": 0.10, "high": 0.80},
    {"label": "n_imperv", "param": "N_imperv", "mode": "absolute", "low": 0.01, "high": 0.04},
    {"label": "slope%", "param": "slope", "mode": "multiplier", "low": 0.50, "high": 1.50},
    {"label": "IMD", "param": "imd", "mode": "absolute", "low": 0.05, "high": 0.25},
]


# ---------------------------------------------------------------------------
# 2. LHS & INP EDITING
# ---------------------------------------------------------------------------

def build_lhs_samples(n_samples: int, seed: int = 42) -> pd.DataFrame:
    sampler = qmc.LatinHypercube(d=len(PARAM_DEFS), seed=seed)
    raw = sampler.random(n=n_samples)
    lows = np.array([p["low"] for p in PARAM_DEFS])
    highs = np.array([p["high"] for p in PARAM_DEFS])
    return pd.DataFrame(qmc.scale(raw, lows, highs), columns=[p["label"] for p in PARAM_DEFS])


def _resolve(pdef: dict, sampled: float, base_val: float) -> float:
    return base_val * sampled if pdef["mode"] == "multiplier" else sampled


def apply_sample(base_inp: SwmmInput, sample: dict) -> SwmmInput:
    inp = base_inp.copy()
    param_lookup = {p["param"]: (p, sample[p["label"]]) for p in PARAM_DEFS}
    subcatch_names = list(inp.SUBCATCHMENTS.keys()) if inp.SUBCATCHMENTS else []

    for name in subcatch_names:
        sc = inp.SUBCATCHMENTS[name]
        if "width" in param_lookup:
            sc.width = max(_resolve(*param_lookup["width"], sc.width), 0.1)
        if "imperv" in param_lookup:
            sc.imperviousness = min(max(_resolve(*param_lookup["imperv"], sc.imperviousness), 0.0), 100.0)
        if "slope" in param_lookup:
            sc.slope = max(_resolve(*param_lookup["slope"], sc.slope), 0.0001)

        if inp.SUBAREAS and name in inp.SUBAREAS:
            sa = inp.SUBAREAS[name]
            if "N_perv" in param_lookup:
                sa.n_perv = max(_resolve(*param_lookup["N_perv"], sa.n_perv), 0.01)
            if "N_imperv" in param_lookup:
                sa.n_imperv = max(_resolve(*param_lookup["N_imperv"], sa.n_imperv), 0.01)
            if "dstore_imperv" in param_lookup:
                sa.storage_imperv = max(_resolve(*param_lookup["dstore_imperv"], sa.storage_imperv), 0.0)
            if "dstore_perv" in param_lookup:
                sa.storage_perv = max(_resolve(*param_lookup["dstore_perv"], sa.storage_perv), 0.0)

        if inp.INFILTRATION and name in inp.INFILTRATION:
            inf = inp.INFILTRATION[name]
            if "imd" in param_lookup:
                inf.moisture_deficit_init = min(max(_resolve(*param_lookup["imd"], inf.moisture_deficit_init), 0.0),
                                                1.0)
    return inp


# ---------------------------------------------------------------------------
# 3. SIMULATION WITH NATIVE STATISTICS EXTRACTOR
# ---------------------------------------------------------------------------

def run_simulation(inp: SwmmInput) -> dict:
    results = {}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".inp", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        if inp.REPORT:
            inp.REPORT.update(
                {'INPUT': 'NO', 'CONTROLS': 'NO', 'SUBCATCHMENTS': 'NONE', 'NODES': 'NONE', 'LINKS': 'NONE'})

        inp.write_file(tmp_path)

        with Simulation(tmp_path, reportfile='', outputfile='') as sim:
            # 1. Initialize node objects
            node_obj = Nodes(sim)

            # 2. Run the simulation natively (replaces sim.execute())
            for step in sim:
                pass

            # 3. Extract statistics BEFORE the 'with' block closes the simulation
            for name in SURFACE_NODES:
                try:
                    results[f"max_depth_{name}"] = node_obj[name].statistics.get('max_depth', 0.0)
                except Exception:
                    results[f"max_depth_{name}"] = np.nan

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return results


# ---------------------------------------------------------------------------
# 4. MAIN UQ & ANALYSIS
# ---------------------------------------------------------------------------

def run_uq(inp_path: str, n_samples: int, seed: int):
    global SURFACE_NODES
    base_inp = SwmmInput.read_file(inp_path)

    if base_inp.STORAGE:
        SURFACE_NODES = [name for name in base_inp.STORAGE.keys() if name.endswith("-S")]

    print(f"[UQ] Surface nodes discovered: {len(SURFACE_NODES)}")
    if not SURFACE_NODES:
        warnings.warn("No storage nodes ending in '-S' found.")

    samples_df = build_lhs_samples(n_samples=n_samples, seed=seed)
    all_rows = []

    for i, row in samples_df.iterrows():
        sample = row.to_dict()
        print(f"[UQ] Run {i + 1:>4d}/{n_samples} ...", end=" ", flush=True)
        try:
            modified_inp = apply_sample(base_inp, sample)
            sim_results = run_simulation(modified_inp)
            status = "OK"
        except Exception as exc:
            sim_results = {}
            status = f"ERROR: {exc}"

        all_rows.append({"run_id": i + 1, "status": status, **sample, **sim_results})
        print(status)

    results_df = pd.DataFrame(all_rows)
    results_df.to_csv("outputdata/UQ/uq_results.csv", index=False)

    aggregated_uncertainty(results_df)
    sensitivity_analysis(results_df)


def aggregated_uncertainty(df: pd.DataFrame):
    df = df[df["status"] == "OK"]
    if df.empty: return

    cvs = []
    for node in SURFACE_NODES:
        col = f"max_depth_{node}"
        if col in df.columns:
            series = df[col].dropna()
            if len(series) > 1 and series.mean() > 0:
                cvs.append(series.std() / series.mean())

    if cvs:
        agg_df = pd.DataFrame([{
            "group": "surface_nodes",
            "metric": "max_depth",
            "mean_CV": round(np.mean(cvs), 4),
            "max_CV": round(np.max(cvs), 4),
            "min_CV": round(np.min(cvs), 4),
            "node_count": len(cvs),
        }])
        agg_df.to_csv("outputdata/UQ/uq_uncertainty.csv", index=False)


def sensitivity_analysis(df: pd.DataFrame):
    df = df[df["status"] == "OK"]
    if df.empty: return

    param_cols = [p["label"] for p in PARAM_DEFS]
    output_cols = [c for c in df.columns if c.startswith("max_depth_")]
    rows = []

    for param in param_cols:
        for output in output_cols:
            valid = df[[param, output]].dropna()
            if len(valid) > 2 and valid[param].nunique() > 1 and valid[output].nunique() > 1:
                rho, pval = spearmanr(valid[param], valid[output])
                rows.append({
                    "parameter": param,
                    "output": output,
                    "spearman_rho": round(rho, 4),
                    "p_value": round(pval, 4),
                })

    if rows:
        sens_df = pd.DataFrame(rows)
        sens_df["abs_rho"] = sens_df["spearman_rho"].abs()
        sens_df = sens_df.sort_values(["output", "abs_rho"], ascending=[True, False]).drop(columns="abs_rho")
        sens_df.to_csv("../outputdata/UQ/uq_sensitivity.csv", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SWMM UQ")
    parser.add_argument("--inp", required=True, help="Path to base SWMM .inp file")
    parser.add_argument("--n", type=int, default=500, help="LHS samples")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    run_uq(inp_path=args.inp, n_samples=args.n, seed=args.seed)