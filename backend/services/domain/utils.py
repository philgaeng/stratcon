#!/usr/bin/env python3
"""
Utility functions for domain-specific operations.
"""

from __future__ import annotations

from typing import Union
import pandas as pd


def normalize_month_year(month_year: Union[str, int, pd.Period]) -> str:
    """
    Normalize a month-year value to YYYY-MM format (with leading zero for month).
    
    This function handles various input formats:
    - Period objects: pd.Period("2025-09")
    - Strings: "2025-9", "2025-09", "2025-09-01"
    - Integers: 202509 (YYYYMM format)
    
    Args:
        month_year: Month-year value in various formats
        
    Returns:
        str: Normalized month-year string in YYYY-MM format (e.g., "2025-09")
        
    Examples:
        >>> normalize_month_year("2025-9")
        '2025-09'
        >>> normalize_month_year("2025-09")
        '2025-09'
        >>> normalize_month_year(pd.Period("2025-09"))
        '2025-09'
    """
    try:
        # Handle pandas Period objects
        if isinstance(month_year, pd.Period):
            return f"{month_year.year}-{month_year.month:02d}"
        
        # Handle string inputs
        if isinstance(month_year, str):
            # Try parsing as Period first (handles YYYY-MM, YYYY-M, etc.)
            try:
                period = pd.Period(month_year)
                return f"{period.year}-{period.month:02d}"
            except (ValueError, TypeError):
                # Fallback: try to parse manually
                parts = month_year.split('-')
                if len(parts) >= 2:
                    year = parts[0]
                    month = parts[1]
                    return f"{year}-{int(month):02d}"
                else:
                    # If it's a single value, try parsing as YYYYMM integer string
                    if month_year.isdigit() and len(month_year) == 6:
                        year = month_year[:4]
                        month = month_year[4:]
                        return f"{year}-{int(month):02d}"
        
        # Handle integer inputs (YYYYMM format)
        if isinstance(month_year, int):
            year = month_year // 100
            month = month_year % 100
            return f"{year}-{month:02d}"
        
        # If all else fails, try converting to string and parsing
        return normalize_month_year(str(month_year))
        
    except Exception:
        # Last resort: return as-is if normalization fails
        return str(month_year)

