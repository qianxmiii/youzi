"""运单异常类型大类：港前 / 港后。"""

from __future__ import annotations

PHASE_PRE_PORT = "pre_port"
PHASE_POST_PORT = "post_port"

PHASE_LABELS_ZH: dict[str, str] = {
    PHASE_PRE_PORT: "港前",
    PHASE_POST_PORT: "港后",
}

DEFAULT_EXCEPTION_PHASE = PHASE_POST_PORT


def normalize_exception_phase(value: object | None) -> str:
    raw = str(value or "").strip().lower()
    if raw in (PHASE_PRE_PORT, "preport", "pre-port", "港前"):
        return PHASE_PRE_PORT
    if raw in (PHASE_POST_PORT, "postport", "post-port", "港后", ""):
        return PHASE_POST_PORT
    raise ValueError("phase_category 须为 pre_port（港前）或 post_port（港后）")


def exception_phase_label_zh(phase: str | None) -> str:
    key = (phase or DEFAULT_EXCEPTION_PHASE).strip()
    return PHASE_LABELS_ZH.get(key, PHASE_LABELS_ZH[PHASE_POST_PORT])
