import re
from pathlib import Path


SEED_FILE = Path(__file__).resolve().parents[2] / "database" / "migrations" / "0003_seed_base_data.sql"


def test_base_seed_only_writes_public_catalog_tables():
    sql = SEED_FILE.read_text(encoding="utf-8")
    inserted_tables = set(re.findall(r"INSERT\s+INTO\s+([a-z_]+)", sql, flags=re.IGNORECASE))

    assert inserted_tables == {"ea_tenant", "ea_platform", "ea_school"}
    assert "password" not in sql.lower()
    assert "000000" in sql


def test_base_seed_contains_the_public_school_catalog():
    sql = SEED_FILE.read_text(encoding="utf-8")
    school_rows = re.findall(r"^\s*\(\d+,\s+(?:4|5|9),\s+'", sql, flags=re.MULTILINE)

    assert len(school_rows) == 97
    assert "'超星'" in sql
    assert "'青书'" in sql
    assert "'尚学课堂'" in sql
