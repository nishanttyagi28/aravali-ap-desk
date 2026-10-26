"""One module per validation rule."""

from docai.validate.rules.duplicate import check_duplicate
from docai.validate.rules.gst_rate import check_gst_rates
from docai.validate.rules.gstin import check_gstin_checksum, check_gstin_state
from docai.validate.rules.lines import check_line_arithmetic
from docai.validate.rules.low_confidence import check_low_confidence
from docai.validate.rules.missing import check_missing_fields
from docai.validate.rules.round_off import check_round_off
from docai.validate.rules.tax_regime import check_tax_regime
from docai.validate.rules.totals import check_totals
from docai.validate.rules.vendor import check_vendor

__all__ = [
    "check_duplicate",
    "check_gst_rates",
    "check_gstin_checksum",
    "check_gstin_state",
    "check_line_arithmetic",
    "check_low_confidence",
    "check_missing_fields",
    "check_round_off",
    "check_tax_regime",
    "check_totals",
    "check_vendor",
]
