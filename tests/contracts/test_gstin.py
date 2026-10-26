from docai.contracts.gstin import GST_STATE_CODES, gstin_checksum_char, is_valid_gstin


def test_state_code_table_covers_01_to_38_and_specials() -> None:
    for i in range(1, 39):
        assert f"{i:02d}" in GST_STATE_CODES
    assert "97" in GST_STATE_CODES
    assert "99" in GST_STATE_CODES


def test_gstin_checksum_roundtrip() -> None:
    body = "07AABCU9603R1Z"
    ch = gstin_checksum_char(body)
    full = body + ch
    assert is_valid_gstin(full)


def test_invalid_gstin_rejected() -> None:
    assert not is_valid_gstin("07AABCU9603R1Z0")
