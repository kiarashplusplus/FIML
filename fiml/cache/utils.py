"""
Cache utility functions

Shared utilities for cache operations
"""

from typing import List


def calculate_percentile(data: List[float], percentile: int) -> float:
    """
    Calculate percentile from data list
    
    Args:
        data: List of numeric values
        percentile: Percentile to calculate (0-100)
        
    Returns:
        Percentile value
    """
    if not data:
        return 0.0
    sorted_data = sorted(data)
    index = int(len(sorted_data) * percentile / 100)
    index = min(index, len(sorted_data) - 1)
    return sorted_data[index]
