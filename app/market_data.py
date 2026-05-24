from __future__ import annotations

import json
from pathlib import Path

from app.config import settings
from app.models import CandidateMarket


def load_markets(path: Path | None = None) -> list[CandidateMarket]:
    market_path = path or settings.market_data_path
    with market_path.open("r", encoding="utf-8") as file:
        raw = json.load(file)
    return [CandidateMarket.model_validate(item) for item in raw]

