"""
parser.py

Parses Gamma Engine [IB15] lines using explicit, per-label rules about
which fields are prices. This module never guesses based on magnitude
("numbers over 1000 are prices") — every label has a fixed, documented
set of price field positions.

Field positions below are 0-indexed into the list of fields that follow
the label (i.e. "field 2" in the spec's 1-indexed, label-inclusive
counting is index 0 here).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Which field positions (0-indexed, after the label) hold prices for
# each known label. An empty tuple means "no price conversion".
LABEL_PRICE_INDICES: Dict[str, Tuple[int, ...]] = {
    "R": (),
    "B": (0,),
    "Z": (0,),
    "M": (0,),
    "H": (0,),
    "E": (0, 1),
    "I": (0, 1),
    "LC": (0,),
    "GC": (0,),
    "LF": (0,),
    "GF": (0,),
    "U": (0, 1),
    "D": (0, 1),
    "FS": (0, 1),
    "FL": (0, 1),
}

KNOWN_LABELS = set(LABEL_PRICE_INDICES.keys())


@dataclass
class GammaLine:
    """A single parsed line from a Gamma Engine [IB15] block."""

    raw: str
    label: Optional[str] = None
    fields: List[str] = field(default_factory=list)
    price_indices: Tuple[int, ...] = ()
    is_valid: bool = True
    error: Optional[str] = None

    @property
    def is_blank(self) -> bool:
        return not self.raw.strip()


def parse_line(raw_line: str) -> GammaLine:
    """
    Parse a single raw line into a GammaLine.

    On any problem (unknown label, missing/invalid price field), the
    returned GammaLine has is_valid=False and a human-readable error,
    and the original raw text is preserved untouched so callers can
    choose to pass it through rather than corrupt it.
    """
    if not raw_line.strip():
        return GammaLine(raw=raw_line, is_valid=True)

    parts = [p.strip() for p in raw_line.split(",")]
    label = parts[0]
    fields = parts[1:]

    label_key = label.upper()
    if label_key not in KNOWN_LABELS:
        return GammaLine(
            raw=raw_line,
            label=label,
            fields=fields,
            is_valid=False,
            error=f"Unknown label '{label}'.",
        )

    price_indices = LABEL_PRICE_INDICES[label_key]

    for idx in price_indices:
        if idx >= len(fields):
            return GammaLine(
                raw=raw_line,
                label=label,
                fields=fields,
                price_indices=price_indices,
                is_valid=False,
                error=(
                    f"Label '{label}' expected a price at field position "
                    f"{idx + 2}, but the line does not have enough fields."
                ),
            )
        candidate = fields[idx]
        if not _is_valid_number(candidate):
            return GammaLine(
                raw=raw_line,
                label=label,
                fields=fields,
                price_indices=price_indices,
                is_valid=False,
                error=(
                    f"Label '{label}' expected a numeric price at field "
                    f"position {idx + 2}, but found '{candidate}'."
                ),
            )

    return GammaLine(
        raw=raw_line,
        label=label,
        fields=fields,
        price_indices=price_indices,
        is_valid=True,
    )


def parse_block(text: str) -> List[GammaLine]:
    """Parse a full multiline Gamma Engine [IB15] block into GammaLines."""
    lines = text.splitlines()
    return [parse_line(line) for line in lines if line.strip() != ""]


def _is_valid_number(text: str) -> bool:
    try:
        float(text)
        return True
    except ValueError:
        return False
