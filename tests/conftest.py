import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture
def clean_csv_path():
    return str(FIXTURES_DIR / "clean_10rows.csv")

@pytest.fixture
def dirty_csv_path():
    return str(FIXTURES_DIR / "dirty_with_outliers.csv")
