import pandas as pd

SYMPTOM_COLUMNS = ["pulsation_stinging", "dull_pressing", "nausea", "light_sensitivity", "noise_sensitivity"]
SHORT_LABELS = {
    "pulsation_stinging": "pulsation",
    "dull_pressing": "pressure",
    "nausea": "nausea",
    "light_sensitivity": "light",
    "noise_sensitivity": "noise",
}


def is_headache_day(clean: pd.DataFrame) -> pd.Series:
    # TODO: data cleaning: cant have a day without headache but symptoms
    is_headache_day = clean["severity"].notna()
    for col in SYMPTOM_COLUMNS:
        is_headache_day = is_headache_day | clean[col].fillna(False)
    return is_headache_day


def diagnostic_criteria(clean: pd.DataFrame) -> pd.DataFrame:
    headache_days = clean[is_headache_day(clean)]
    n = len(headache_days)
    total_days = len(clean)

    criteria = {
        "Severity >= 5": (headache_days["severity"] >= 5).sum(),
        "Pulsation": headache_days["pulsation_stinging"].sum(),
        "Pressure": headache_days["dull_pressing"].sum(),
        "Nausea": headache_days["nausea"].sum(),
        "Light": headache_days["light_sensitivity"].sum(),
        "Noise": headache_days["noise_sensitivity"].sum(),
    }

    rows = [{"criterion": "Total headache days", "count": n, "pct": round(n / total_days * 100)}]
    rows += [
        {"criterion": label, "count": int(count), "pct": round(count / n * 100)}
        for label, count in criteria.items()
    ]

    return pd.DataFrame(rows)


def recent_trend(clean: pd.DataFrame, months: int = 3) -> dict:
    df = clean.copy()
    df["month"] = df["Datum"].dt.to_period("M")
    df["headache_day"] = is_headache_day(df)

    baseline_days_per_month = df.groupby("month")["headache_day"].sum().mean()
    baseline_severity = df["severity"].mean()
    baseline_hd = df[df["headache_day"]]
    baseline_pulsation_pct = baseline_hd["pulsation_stinging"].fillna(False).sum() / len(baseline_hd) * 100

    end = df["Datum"].max()
    window = df[df["Datum"] > end - pd.DateOffset(months=months)]
    window_hd = window[window["headache_day"]]

    recent_days_per_month = window["headache_day"].sum() / months
    recent_severity = window_hd["severity"].mean()
    recent_pulsation_pct = window_hd["pulsation_stinging"].fillna(False).sum() / len(window_hd) * 100

    return {
        "months": months,
        "baseline_days_per_month": baseline_days_per_month,
        "recent_days_per_month": recent_days_per_month,
        "baseline_severity": baseline_severity,
        "recent_severity": recent_severity,
        "baseline_pulsation_pct": baseline_pulsation_pct,
        "recent_pulsation_pct": recent_pulsation_pct,
    }


def attack_durations(clean: pd.DataFrame) -> dict:
    df = clean.sort_values("Datum").reset_index(drop=True)
    df["headache_day"] = is_headache_day(df)
    df["run_id"] = (df["headache_day"] != df["headache_day"].shift()).cumsum()

    runs = df[df["headache_day"]].groupby("run_id").agg(length=("Datum", "count"))

    bins = {str(days): int((runs["length"] == days).sum()) for days in [1, 2, 3, 4]}
    bins["5+"] = int((runs["length"] >= 5).sum())

    return {
        "mean_days": runs["length"].mean(),
        "total_attacks": len(runs),
        "bins": bins,
    }


def symptom_cooccurrence(clean: pd.DataFrame) -> pd.DataFrame:
    matrix = pd.DataFrame(index=SYMPTOM_COLUMNS, columns=SYMPTOM_COLUMNS, dtype=int)
    for a in SYMPTOM_COLUMNS:
        for b in SYMPTOM_COLUMNS:
            matrix.loc[a, b] = int((clean[a].fillna(False) & clean[b].fillna(False)).sum())

    matrix = matrix.rename(index=SHORT_LABELS, columns=SHORT_LABELS)
    return matrix.reset_index(names="symptom")
