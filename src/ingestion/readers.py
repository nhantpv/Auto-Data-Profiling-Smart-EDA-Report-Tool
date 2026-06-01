import pandas as pd

_ENCODINGS = ["utf-8", "utf-8-sig", "latin-1"]


class CSVReader:
    suffixes = (".csv",)
    def read(self, path: str) -> pd.DataFrame:
        for enc in _ENCODINGS:
            try:
                return pd.read_csv(path, encoding=enc)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Cannot read {path} with encodings {_ENCODINGS}")


class ExcelReader:
    suffixes = (".xlsx", ".xls")
    def read(self, path: str) -> pd.DataFrame:
        return pd.read_excel(path)


class ParquetReader:
    suffixes = (".parquet",)
    def read(self, path: str) -> pd.DataFrame:
        return pd.read_parquet(path)
