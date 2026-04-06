from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class CrmEvent:
    event_type: str
    customer_key: str
    payload: dict[str, Any]
    created_at_utc: str


def log_event(
    crm_path: Path,
    event_type: str,
    customer_key: str,
    payload: dict[str, Any],
) -> None:
    crm_path.parent.mkdir(parents=True, exist_ok=True)
    ev = CrmEvent(
        event_type=event_type,
        customer_key=customer_key,
        payload=payload,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    line = json.dumps(asdict(ev), ensure_ascii=False) + "\n"
    with crm_path.open("a", encoding="utf-8") as f:
        f.write(line)
