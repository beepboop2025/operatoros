"""
Cost Inflation Index (CII) table — base year 2001-02 = 100.

Used for computing indexed cost of acquisition for long-term capital gains
on assets acquired before 23 July 2024 (where the taxpayer may choose the
old 20%-with-indexation regime).

Source: CBDT notifications.  FY 2025-26 value is an estimate and will be
updated when the official notification is released.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional

# FY string → CII value
CII_TABLE: Dict[str, int] = {
    "2001-02": 100,
    "2002-03": 105,
    "2003-04": 109,
    "2004-05": 113,
    "2005-06": 117,
    "2006-07": 122,
    "2007-08": 129,
    "2008-09": 137,
    "2009-10": 148,
    "2010-11": 167,
    "2011-12": 184,
    "2012-13": 200,
    "2013-14": 220,
    "2014-15": 240,
    "2015-16": 254,
    "2016-17": 264,
    "2017-18": 272,
    "2018-19": 280,
    "2019-20": 289,
    "2020-21": 301,
    "2021-22": 317,
    "2022-23": 331,
    "2023-24": 348,
    "2024-25": 363,
    "2025-26": 377,   # estimated — update when CBDT notifies
}


class CIINotFoundError(ValueError):
    """Raised when a CII value is not available for the requested financial year."""

    def __init__(self, fy: str) -> None:
        self.fy = fy
        available = sorted(CII_TABLE.keys())
        super().__init__(
            f"CII data not available for FY {fy}. "
            f"Available range: {available[0]} to {available[-1]}."
        )


def get_cii(fy: str) -> int:
    """Return the CII value for a financial year string like '2023-24'.

    Raises ``CIINotFoundError`` if the FY is not in the table.
    """
    value = CII_TABLE.get(fy)
    if value is None:
        raise CIINotFoundError(fy)
    return value


def compute_indexed_cost(
    cost: Decimal,
    purchase_fy: str,
    sale_fy: str,
) -> Decimal:
    """Compute indexed cost of acquisition.

    Formula:
        indexed_cost = cost * (CII of sale FY / CII of purchase FY)

    Raises ``CIINotFoundError`` if either FY is missing from the CII table.
    """
    cii_purchase = get_cii(purchase_fy)
    cii_sale = get_cii(sale_fy)

    indexed = cost * Decimal(str(cii_sale)) / Decimal(str(cii_purchase))
    return indexed.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
