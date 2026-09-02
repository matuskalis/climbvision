import json
from typing import Any

from pydantic import BaseModel


def dumps_canonical(model: BaseModel) -> bytes:
    text = json.dumps(
        model.model_dump(mode="json"),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    return text.encode("utf-8") + b"\n"


def loads_json(data: bytes) -> Any:
    return json.loads(data)
