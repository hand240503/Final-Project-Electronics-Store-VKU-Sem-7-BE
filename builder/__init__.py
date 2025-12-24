"""
Builder package for recommendation system calculations

Usage:
    from builder.item_similarity_calculator import (
        ItemSimilarityMatrixBuilder,
        load_all_ratings
    )
"""

__version__ = '1.0.0'
__author__ = 'Electronics Store VKU Team'

# Don't import here to avoid circular import when running as module
# Users should import directly from item_similarity_calculator

__all__ = [
    'ItemSimilarityMatrixBuilder',
    'load_all_ratings',
]