"""GSTIN checksum and state-code helpers (pure, no I/O)."""

from __future__ import annotations

# Valid GST state/UT codes (2-digit), per Indian GST law.
GST_STATE_CODES: frozenset[str] = frozenset({f"{i:02d}" for i in range(1, 39)} | {"97", "99"})

_CHECKSUM_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def gstin_checksum_char(first14: str) -> str:
    """Return the 15th checksum character for the first 14 GSTIN characters."""
    if len(first14) != 14:
        raise ValueError("first14 must be exactly 14 characters")
    upper = first14.upper()
    total = 0
    for i, ch in enumerate(upper):
        if ch not in _CHECKSUM_CHARS:
            raise ValueError(f"invalid character in GSTIN: {ch}")
        val = _CHECKSUM_CHARS.index(ch)
        factor = (i % 2) + 1
        if factor == 1:
            total += val
        else:
            q, r = divmod(val * 2, 36)
            total += q + r
    rem = total % 36
    check = (36 - rem) % 36
    return _CHECKSUM_CHARS[check]


def is_valid_gstin(s: str) -> bool:
    """Return True if ``s`` is a well-formed GSTIN with valid checksum and state code."""
    if not s or len(s) != 15:
        return False
    upper = s.upper()
    if not upper.isalnum():
        return False
    state = upper[:2]
    if state not in GST_STATE_CODES:
        return False
    try:
        expected = gstin_checksum_char(upper[:14])
    except ValueError:
        return False
    return upper[14] == expected
