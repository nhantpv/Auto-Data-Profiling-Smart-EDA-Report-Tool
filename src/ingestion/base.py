from typing import Protocol
import pandas as pd


class DataReader(Protocol):
    suffixes: tuple
    def read(self, path: str) -> pd.DataFrame: ...
