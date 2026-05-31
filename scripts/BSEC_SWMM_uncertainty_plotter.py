import os

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import numpy as np
import pandas as pd
import seaborn as sns


class SWMMVisualizer:
    def __init__(self, results_path, sensitivity_path, output_dir="figures"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        raw = pd.read_csv(results_path)

        # check # successful runs
        n_total = len(raw)
        self.df = raw[raw["status"] == "OK"].copy()
        n_ok = len(self.df)
        n_failed = n_total - n_ok
        print(f"[System]   {n_ok}/{n_total} runs OK"
              + (f", {n_failed} failed runs excluded" if n_failed else ""))

        # Force all output columns to numeric (belt-and-braces)
        output_cols = [c for c in self.df.columns
                       if c.startswith("max_depth_") or c.startswith("max_volume_")]
        self.df[output_cols] = self.df[output_cols].apply(pd.to_numeric, errors="coerce")

        # METRIC CONVERSION (ft to m)
        FT_TO_M = 0.3048
        for col in output_cols:
            if col.startswith("max_depth_"):
                self.df[col] = self.df[col] * FT_TO_M
            elif col.startswith("max_volume_"):
                self.df[col] = self.df[col] * (FT_TO_M ** 3)

        self.sens_df = pd.read_csv(sensitivity_path)
        self.sens_df["spearman_rho"] = pd.to_numeric(self.sens_df["spearman_rho"], errors="coerce")
        self.sens_df["p_value"]      = pd.to_numeric(self.sens_df["p_value"],      errors="coerce")

        # Node column lists, surface storage (-S) nodes only, no outfalls
        self.depth_cols = [
            c for c in self.df.columns
            if c.startswith("max_depth_") and "-S" in c and "Out" not in c
        ]
        self.volume_cols = [
            c for c in self.df.columns
            if c.startswith("max_volume_") and "-S" in c and "Out" not in c
        ]

        # Key nodes used for convergence plots
        self.stability_targets = [
            "max_depth_J748-S",
            "max_depth_J576-S",
            "max_depth_J640-S",
            "max_depth_J799-S",
        ]

    # ------------------------------------------------------------------
    # 1.  MAX DEPTH BOXPLOTS  (all surface nodes)
    # ------------------------------------------------------------------
    def plot_max_depth_boxes(self):
        print("[Plotting] Max Depth Boxplots...")
        melted = self.df.melt(
            value_vars=self.depth_cols,
            var_name="Node",
            value_name="Max Depth (m)",
        )
        melted["Node"] = melted["Node"].str.replace("max_depth_", "", regex=False)

        plt.figure(figsize=(18, 8))
        sns.boxplot(data=melted, x="Node", y="Max Depth (m)",
                    color="cornflowerblue", fliersize=1)
        plt.xticks(rotation=90, fontsize=6)
        plt.title("Max Depth Uncertainty Distribution (Surface Storage Nodes)")
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "max_depth_distribution.svg"), dpi=300)
        plt.close()

    # ------------------------------------------------------------------
    # 2.  BOOTSTRAP CONVERGENCE  — fixed title + correct 5/95 % label
    # ------------------------------------------------------------------
    def plot_convergence(self, n_bootstrap: int = 50, seed: int = 42):
        """
        For each stability-target node, repeatedly shuffle the run order
        (n_bootstrap times) and compute the cumulative mean after each run.

        Shaded band = 5th–95th percentile of cumulative means across all
        shuffles. Median convergence line runs through the centre.

        Interpretation:
          Narrow flat band  → statistic has converged, sample size sufficient.
          Wide/trending band → more runs needed.
        """
        print(f"[Plotting] Bootstrap Convergence Envelope (n_bootstrap={n_bootstrap})...")
        rng = np.random.default_rng(seed)

        fig, ax = plt.subplots(figsize=(10, 6))
        colors = sns.color_palette("tab10", len(self.stability_targets))

        for i, node in enumerate(self.stability_targets):
            if node not in self.df.columns:
                print(f"  [Warning] {node} not found — skipping")
                continue

            data   = self.df[node].dropna().values
            n_runs = len(data)
            if n_runs < 2:
                continue

            # n_bootstrap shuffles → cumulative mean paths
            boot_paths = np.zeros((n_bootstrap, n_runs))
            for b in range(n_bootstrap):
                shuffled       = rng.permutation(data)
                boot_paths[b]  = np.cumsum(shuffled) / (np.arange(n_runs) + 1)

            median_path = np.median(boot_paths, axis=0)
            lower       = np.percentile(boot_paths,  5, axis=0)
            upper       = np.percentile(boot_paths, 95, axis=0)
            x           = np.arange(1, n_runs + 1)
            label       = node.replace("max_depth_", "")
            c           = colors[i]

            # 5–95 % shaded envelope
            ax.fill_between(x, lower, upper,
                            color=c, alpha=0.18,
                            label=f"{label} — 5/95 % CI")

            # Median convergence line
            ax.plot(x, median_path,
                    color=c, lw=2,
                    label=f"{label} — median")

        ax.set_xlabel("Number of Samples", fontsize=11)
        ax.set_ylabel("Cumulative Mean Max Depth (m)", fontsize=11)
        ax.set_title(
            f"Convergence Stability — 5/95 % Bootstrap Envelope"
            f"  ({n_bootstrap} re-orderings)",
            fontsize=12,
        )
        ax.legend(title="Node ID", loc="upper right", fontsize=8,
                  ncol=2, framealpha=0.9)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "convergence_bootstrap.svg"), dpi=300)
        plt.close()
        print("  Saved → convergence_bootstrap.png")

    # ------------------------------------------------------------------
    # 3.  BOOTSTRAP CI ON MEAN DEPTH — all 126 surface nodes
    # ------------------------------------------------------------------
    def plot_bootstrap_mean_ci(self, n_bootstrap: int = 2000, seed: int = 42,
                                ci: float = 95.0):
        """
        For every surface node, bootstrap the mean max depth (n_bootstrap
        resamples with replacement) and plot the 5/95 % CI as an error bar
        alongside the observed mean.

        Nodes are sorted by observed mean depth so the figure reads as a
        ranked uncertainty profile across the system.

        This answers: "How precisely do our 100 runs estimate the true mean
        depth at each node, and which nodes have the widest uncertainty?"
        """
        print(f"[Plotting] Bootstrap Mean CI — all surface nodes "
              f"(n_bootstrap={n_bootstrap}, CI={ci}%)...")

        rng  = np.random.default_rng(seed)
        half = (100.0 - ci) / 2.0   # e.g. 2.5 for 95 % CI

        records = []
        for col in self.depth_cols:
            data = self.df[col].dropna().values
            if len(data) < 2:
                continue

            # Bootstrap resample with replacement
            boot_means = np.array([
                rng.choice(data, size=len(data), replace=True).mean()
                for _ in range(n_bootstrap)
            ])

            records.append({
                "node":       col.replace("max_depth_", ""),
                "obs_mean":   data.mean(),
                "ci_low":     np.percentile(boot_means, half),
                "ci_high":    np.percentile(boot_means, 100.0 - half),
                "ci_width":   np.percentile(boot_means, 100.0 - half)
                              - np.percentile(boot_means, half),
            })

        if not records:
            print("  [Warning] No data available — skipping.")
            return

        stats = pd.DataFrame(records).sort_values("obs_mean", ascending=True)

        n_nodes = len(stats)
        fig_h   = max(10, n_nodes * 0.18)
        fig, ax = plt.subplots(figsize=(9, fig_h))

        y_pos  = np.arange(n_nodes)
        colors = plt.cm.YlOrRd(
            (stats["obs_mean"] - stats["obs_mean"].min())
            / (stats["obs_mean"].max() - stats["obs_mean"].min() + 1e-9)
        )

        # Horizontal error bars (CI)
        ax.barh(y_pos,
                stats["ci_high"] - stats["ci_low"],
                left=stats["ci_low"],
                height=0.55,
                color=colors,
                alpha=0.45,
                label=f"{int(ci)} % bootstrap CI")

        # Observed mean marker
        ax.scatter(stats["obs_mean"], y_pos,
                   color="black", s=18, zorder=5,
                   label="Observed mean")

        ax.set_yticks(y_pos)
        ax.set_yticklabels(stats["node"], fontsize=6)
        ax.set_xlabel("Max Depth (m)", fontsize=11)
        ax.set_title(
            f"Bootstrap {int(ci)} % CI on Mean Max Depth\n"
            f"All Surface Storage Nodes  (sorted by mean depth, "
            f"n_bootstrap={n_bootstrap})",
            fontsize=11,
        )
        ax.legend(fontsize=9, loc="lower right")
        ax.grid(True, axis="x", alpha=0.3)
        plt.tight_layout()

        fname = "bootstrap_mean_ci_all_nodes.svg"
        plt.savefig(os.path.join(self.output_dir, fname), dpi=300)
        plt.close()
        print(f"  Saved → {fname}")

    # ------------------------------------------------------------------
    # 4.  MEAN vs CV SCATTER
    # ------------------------------------------------------------------
    def plot_uncertainty_scatter(self):
        print("[Plotting] Mean vs. CV Uncertainty Scatter...")
        stats = self.df[self.depth_cols].agg(["mean", "std"]).T
        stats["CV"] = stats["std"] / stats["mean"]
        stats.index = stats.index.str.replace("max_depth_", "", regex=False)

        plt.figure(figsize=(10, 7))
        sns.scatterplot(data=stats, x="mean", y="CV", color="cornflowerblue", alpha=0.6)
        for idx, row in stats.nlargest(5, "CV").iterrows():
            plt.text(row["mean"] + 0.005, row["CV"], idx, fontsize=8)

        plt.title("Uncertainty Map: Mean Max Depth vs. Relative Variability")
        plt.xlabel("Mean Max Depth (m)")
        plt.ylabel("Coefficient of Variation (CV)")
        plt.grid(True, alpha=0.2)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "uncertainty_scatter_mean_vs_cv.svg"), dpi=300)
        plt.close()

    # ------------------------------------------------------------------
    # 5.  GLOBAL CV HISTOGRAM
    # ------------------------------------------------------------------
    def plot_cv_overall_distribution(self):
        print("[Plotting] Overall CV Histogram...")
        stats = self.df[self.depth_cols].agg(['mean', 'std']).T
        cv_values = (stats['std'] / stats['mean']).dropna()

        plt.figure(figsize=(10, 6))
        sns.histplot(cv_values, kde=True, color='cornflowerblue', bins=20)
        plt.axvline(cv_values.median(), color='black', linestyle='--', label=f'Median CV: {cv_values.median():.3f}')
        plt.title("Global CV Distribution (Surface Nodes)")
        plt.xlabel("Coefficient of Variation (CV)")
        plt.legend()
        plt.savefig(os.path.join(self.output_dir, "cv_overall_histogram.svg"), dpi=300)
        plt.close()

    # ------------------------------------------------------------------
    # 6.  SENSITIVITY HEATMAPS
    # ------------------------------------------------------------------
    def plot_sensitivity_heatmaps(self):
        print("[Plotting] Sensitivity Heatmaps...")
        metric_keys = {"max_depth": "Max Depth (m)"}

        for metric_key, metric_label in metric_keys.items():
            mask = (
                    self.sens_df["output"].str.contains(metric_key, regex=False)
                    & self.sens_df["output"].str.contains("-S", regex=False)
                    & ~self.sens_df["output"].str.contains("Out", regex=False)
            )
            df_plot = self.sens_df[mask].copy().dropna(subset=["spearman_rho"])

            if df_plot.empty:
                print(f"  [Warning] No sensitivity data for {metric_label} — skipping")
                continue

            df_plot["node"] = df_plot["output"].str.replace(
                f"{metric_key}_", "", regex=False)

            # Pivot and then TRANSPOSE (.T) to put parameters on Y and nodes on X
            pivot = df_plot.pivot(index="node", columns="parameter",
                                  values="spearman_rho").T

            # Adjust figure size: wider now because nodes are on the bottom
            fig_w = max(18, len(pivot.columns) * 0.15)
            fig_h = max(6, len(pivot.index) * 0.4)

            plt.figure(figsize=(fig_w, fig_h))
            sns.heatmap(pivot.abs(), cmap="Blues", vmin=0, vmax=1,
                        linewidths=0.3,
                        cbar_kws={"label": "|Spearman ρ|"})

            plt.title(f"Sensitivity Heatmap — {metric_label}")
            plt.ylabel("Model Parameter")
            plt.xlabel("Storage Node ID")
            plt.xticks(rotation=90, fontsize=7)
            plt.yticks(fontsize=9)

            plt.tight_layout()
            fname = f"sensitivity_heatmap_{metric_key}.svg"
            plt.savefig(os.path.join(self.output_dir, fname), dpi=300)
            plt.close()
            print(f"  Saved → {fname}")
    # ------------------------------------------------------------------
    # Run all plots
    # ------------------------------------------------------------------
    def run_all(self):
        self.plot_max_depth_boxes()
        self.plot_convergence()
        self.plot_bootstrap_mean_ci()
        self.plot_uncertainty_scatter()
        self.plot_cv_overall_distribution()
        self.plot_sensitivity_heatmaps()
        print(f"\n[Done] All plots saved to: {os.path.abspath(self.output_dir)}")


# --- EXECUTION ---
if __name__ == "__main__":
    viz = SWMMVisualizer(
        results_path="../outputdata/UQ/uq_results.csv",
        sensitivity_path="../outputdata/UQ/uq_sensitivity.csv",
        output_dir="../figures/UQ/",
    )
    viz.run_all()