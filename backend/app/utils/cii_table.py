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


def get_cii(fy: str) -> Optional[int]:
    """Return the CII value for a financial year string like '2023-24'.

    Returns ``None`` if the FY is not in the table.
    """
    return CII_TABLE.get(fy)


def compute_indexed_cost(
    cost: Decimal,
    purchase_fy: str,
    sale_fy: str,
) -> Optional[Decimal]:
    """Compute indexed cost of acquisition.

    Formula:
        indexed_cost = cost × (CII of sale FY / CII of purchase FY)

    Returns ``None`` if either FY is missing from the CII table.
    """
    cii_purchase = CII_TABLE.get(purchase_fy)
    cii_sale = CII_TABLE.get(sale_fy)

    if cii_purchase is None or cii_sale is None:
        return None

    indexed = cost * Decimal(str(cii_sale)) / Decimal(str(cii_purchase))
    return indexed.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
