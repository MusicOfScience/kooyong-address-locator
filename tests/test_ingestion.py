from pathlib import Path
import pandas as pd

from backend.ingestion.loaders import load_table


def test_csv_ingestion(tmp_path: Path):
    p = tmp_path / "sample.csv"
    pd.DataFrame({"a": [1]}).to_csv(p, index=False)
    df = load_table(p)
    assert df.shape == (1, 1)


def test_missing_file_handling(tmp_path: Path):
    missing = tmp_path / "missing.csv"
    try:
        load_table(missing)
    except FileNotFoundError:
        assert True
    else:
        assert False
