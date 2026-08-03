from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

# TODO: migrate towards yaml/pydantic driven
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "Migri.xlsx"
SHEET_NAME = "Data"


@dataclass
class DataProcessing:
    source_path: Path = DATA_PATH
    sheet_name: str = SHEET_NAME
    df: pd.DataFrame = field(default=None)
    clean: pd.DataFrame = field(default=None)

    def _boolean_flag(self, column: str, skip_values: tuple = ()) -> pd.Series:
        raw = self.df[column]
        is_one = raw == 1
        is_skip = raw.isin(skip_values)
        unexpected = raw[~(is_one | is_skip | raw.isna())]
        if not unexpected.empty:
            raise ValueError(f"{column} has unexpected values: {unexpected.tolist()}")

        flag = pd.Series(pd.NA, index=raw.index, dtype="boolean")
        flag[is_one] = True
        return flag

    def read(self) -> "DataProcessing":
        self.df = pd.read_excel(self.source_path, sheet_name=self.sheet_name)
        self.clean = self.df[["Datum"]].copy()
        return self

    def severity(self) -> "DataProcessing":
        numeric = pd.to_numeric(self.df["Kopfschmerz-Staerke"], errors="coerce")
        was_question_mark = self.df["Kopfschmerz-Staerke"] == "?"

        average = round(numeric.mean())
        numeric[was_question_mark] = average

        self.clean["severity"] = numeric
        return self

    def location(self) -> "DataProcessing":
        self.clean["pulsation_stinging"] = self._boolean_flag("Pulsierend/Stechend")
        self.clean["dull_pressing"] = self._boolean_flag("Dumpf_drueckend", skip_values=("UNLESERLICH",))
        return self

    def symptoms(self) -> "DataProcessing":
        self.clean["nausea"] = self._boolean_flag("Uebelkeit")
        self.clean["noise_sensitivity"] = self._boolean_flag("Laermscheu")
        self.clean["light_sensitivity"] = self._boolean_flag("Lichtscheu")
        return self
