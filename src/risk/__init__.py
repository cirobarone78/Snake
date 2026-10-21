"""Risk-management overlays (position sizing, stops).

These are rules applied to an *already-open* position, not forecasts. They
answer "given that I hold this, where do I manage risk?" — inputs for a human
decision, never a promise of outcome (VISION/CLAUDE.md).
"""

from __future__ import annotations

from src.risk.trailing_stop import (
    TrailingStopState,
    chandelier_stop,
    evaluate_position,
)

__all__ = [
    "TrailingStopState",
    "chandelier_stop",
    "evaluate_position",
]
