import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from report.stats import attack_durations, diagnostic_criteria, recent_trend, symptom_cooccurrence
from report.visual import Visual

REPORT_DIR = Path(__file__).resolve().parent


@dataclass
class Report:
    clean: pd.DataFrame
    sections: list = field(default_factory=list)

    def summary(self) -> "Report":
        criteria = diagnostic_criteria(self.clean).set_index("criterion")
        trend = recent_trend(self.clean)
        duration = attack_durations(self.clean)

        start = self.clean["Datum"].min()
        end = self.clean["Datum"].max()
        months_span = (end.year - start.year) * 12 + (end.month - start.month) + 1

        total_headache_days = int(criteria.loc["Total headache days", "count"])
        total_headache_pct = int(criteria.loc["Total headache days", "pct"])

        mean_severity = self.clean["severity"].mean()
        std_severity = self.clean["severity"].std()

        severe_pct = int(criteria.loc["Severity >= 5", "pct"])
        nausea_pct = int(criteria.loc["Nausea", "pct"])
        pulsation_pct = int(criteria.loc["Pulsation", "pct"])
        light_pct = int(criteria.loc["Light", "pct"])

        lines = [
            f"Observation period: {months_span} months ({start:%b %Y}-{end:%b %Y}), "
            f"{total_headache_days} headache days recorded.",
            f"Frequency: {trend['baseline_days_per_month']:.1f} headache days/month "
            f"({total_headache_pct}% of tracked days).",
            f"Intensity: mean {mean_severity:.1f}/10 (SD {std_severity:.1f}); "
            f"moderate-to-severe (>=5) in {severe_pct}% of episodes.",
            f"Associated features: nausea {nausea_pct}%, pulsating quality {pulsation_pct}%, "
            f"photophobia {light_pct}%.",
            f"Recent trend (last {trend['months']} months vs. long-run average): "
            f"frequency {trend['recent_days_per_month']:.1f} vs. {trend['baseline_days_per_month']:.1f}/month, "
            f"intensity {trend['recent_severity']:.1f} vs. {trend['baseline_severity']:.1f}, "
            f"pulsating quality {trend['recent_pulsation_pct']:.0f}% vs. {trend['baseline_pulsation_pct']:.0f}%.",
            f"Attack duration (full period, {duration['total_attacks']} attacks, mean "
            f"{duration['mean_days']:.1f} days): "
            f"{duration['bins']['1']} lasted 1 day, {duration['bins']['2']} lasted 2 days, "
            f"{duration['bins']['3']} lasted 3 days, {duration['bins']['4']} lasted 4 days, "
            f"{duration['bins']['5+']} lasted 5+ days.",
        ]

        numbered = [f"{i}. {line}" for i, line in enumerate(lines, start=1)]
        self.sections.append(("Summary", "\n".join(numbered), False))
        return self

    def chart(self, visual: Visual) -> "Report":
        for title, path, caption in visual.charts:
            text = f"![]({path.name})\n\n{caption}"
            self.sections.append((title, text, False))
        return self

    def statistics(self) -> "Report":
        criteria_table = diagnostic_criteria(self.clean)
        cooccurrence_table = symptom_cooccurrence(self.clean)

        profile_caption = (
            "This table shows how often each migraine feature was present on a headache day. "
            "\"Total headache days\" is a share of all tracked days; every other row is a share "
            "of headache days specifically."
        )
        profile_text = f"{criteria_table.to_markdown(index=False)}\n\n{profile_caption}"
        self.sections.append(("Symptom Profile", profile_text, False))

        cooccurrence_caption = (
            "This matrix shows, for each pair of symptoms, how many headache days had both present "
            "at once. The diagonal is each symptom's own total count."
        )
        cooccurrence_text = f"{cooccurrence_table.to_markdown(index=False)}\n\n{cooccurrence_caption}"
        self.sections.append(("Symptom Co-occurrence", cooccurrence_text, True))
        return self

    def render(self, name: str = "report") -> Path:
        parts = []
        for title, text, page_break_before in self.sections:
            prefix = "\\newpage\n\n" if page_break_before else ""
            parts.append(f"{prefix}## {title}\n\n{text}")
        markdown = "\n\n".join(parts)
        md_path = REPORT_DIR / f"{name}.md"
        pdf_path = REPORT_DIR / f"{name}.pdf"
        md_path.write_text(markdown)

        subprocess.run(
            [
                "pandoc",
                str(md_path),
                "-o",
                str(pdf_path),
                f"--resource-path={REPORT_DIR}",
                "-V",
                "geometry:left=0.75in,right=0.75in,top=1in,bottom=1in",
            ],
            check=True,
        )
        return pdf_path
