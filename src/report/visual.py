from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from report.stats import SYMPTOM_COLUMNS, SHORT_LABELS

REPORT_DIR = Path(__file__).resolve().parent

SYMPTOM_COLORS = {
    "pulsation_stinging": "#d62728",
    "dull_pressing": "#9467bd",
    "nausea": "#2ca02c",
    "light_sensitivity": "#ff7f0e",
    "noise_sensitivity": "#1f77b4",
}


@dataclass
class Visual:
    clean: pd.DataFrame
    charts: list = field(default_factory=list)

    def severity_last_3_months(self) -> "Visual":
        df = self.clean
        end = df["Datum"].max()
        start = end - pd.DateOffset(months=3)
        window = df[(df["Datum"] > start) & (df["Datum"] <= end)]

        baseline = df["severity"].mean()
        headache_days = window[window["severity"].notna()]

        fig, ax = plt.subplots(figsize=(11, 5))
        ax.bar(headache_days["Datum"], headache_days["severity"], width=0.7, color="#4c72b0", zorder=2, label="Severity")
        ax.axhline(baseline, color="gray", linestyle="--", linewidth=1, label=f"Long-run avg ({baseline:.1f})")

        marker_y_start = 0.3
        for i, col in enumerate(SYMPTOM_COLUMNS):
            present = window[window[col] == True]
            if present.empty:
                continue
            ax.scatter(
                present["Datum"],
                [marker_y_start + i * 0.35] * len(present),
                color=SYMPTOM_COLORS[col],
                s=25,
                label=SHORT_LABELS[col].capitalize(),
                zorder=3,
            )

        ax.set_ylim(0, 10)
        ax.set_ylabel("Severity (0-10)")
        ax.set_xlabel("Date")
        ax.set_title("Migraine severity & symptoms - last 3 months")
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8)
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0, interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        path = REPORT_DIR / "severity_last_3_months.png"
        plt.savefig(path, dpi=150)
        plt.close(fig)

        caption = (
            "Bars show severity on each headache day over the last three months; "
            "the dashed line is her long-run average severity for comparison. "
            "Colored dots mark which symptoms were present that day."
        )
        self.charts.append(("Severity - Last 3 Months", path, caption))
        return self
