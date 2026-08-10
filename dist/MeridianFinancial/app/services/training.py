"""Tier-3 learning: every correction captured as clean instruction/response JSONL.

Iteration 2 can run a periodic LoRA fine-tune from data/{user_id}/training/
corrections.jsonl. Iteration 1 only guarantees the capture is clean and
sufficient to train from (brief §12).
"""
from __future__ import annotations

import json

from app.core.config import get_settings


def append_training_example(user_id: int, *, description: str, merchant: str | None,
                            amount_minor: int, category_name: str) -> None:
    folder = get_settings().data_dir / str(user_id) / "training"
    folder.mkdir(parents=True, exist_ok=True)
    record = {
        "instruction": ("Categorize this personal-finance transaction into exactly "
                        "one category."),
        "input": {"description": description, "merchant": merchant,
                  "amount_minor": amount_minor},
        "output": {"category": category_name},
    }
    with open(folder / "corrections.jsonl", "a") as f:
        f.write(json.dumps(record) + "\n")
