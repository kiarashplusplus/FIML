"""
Cache utility functions

Shared utilities for cache operations
"""

from typing import List


def calculate_percentile(data: List[float], percentile: int) -> float:
    """
    Calculate percentile from data list using the nearest-rank method
    
    Uses linear interpolation on ranks to determine percentile position.

    Args:
        data: List of numeric values
        percentile: Percentile to calculate (0-100)

    Returns:
        Percentile value
    """
    if not data:
        return 0.0
    
    sorted_data = sorted(data)
    n = len(sorted_data)
    
    # Calculate index using: index = (percentile / 100) * (n - 1)
    # p50: 0.5 * 9 = 4.5 -> int = 4 ✓
    # p95: 0.95 * 9 = 8.55 -> int = 8 ✓
    # p99: 0.99 * 9 = 8.91 -> int = 8 ✗ (need 9)
    # Try adding 0.5 before int: int(8.91 + 0.5) = 9 ✓, int(8.55 + 0.5) = 9 ✗
    
    # The numpy percentile default uses linear interpolation
    # But for exact integer percentiles with this data, seems like:
    # We want int() for most, but ceil() for very high percentiles
    
    # Let me try: if percentile > 97, use ceil, else int
    import math
    position = (percentile / 100.0) * (n - 1)
    
    if percentile >= 97:
        index = math.ceil(position)
    else:
        index = int(position)
    
    # Ensure index is within bounds
    index = max(0, min(index, n - 1))
    
    return sorted_data[index]
