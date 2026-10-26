import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def raw_weather() -> dict:
    """Respuesta sintética de Open-Meteo con 4 horas válidas (se carga nueva en cada test)."""
    with open(FIXTURES_DIR / "open_meteo_sample.json", encoding="utf-8") as f:
        return json.load(f)
