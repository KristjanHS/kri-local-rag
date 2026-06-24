"""Utilities for handling vector-like objects with explicit, safe typing.

This module provides helpers to convert various embedding outputs into
plain Python lists of floats suitable for clients like Weaviate.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def to_float_list(vector_like: Any) -> list[float]:
    """Convert a vector-like object to a ``list[float]`` for the Weaviate client.

    ``SentenceTransformer.encode`` returns a numpy ndarray by default; ``np.asarray``
    coerces that (and CPU torch tensors, plain sequences, or scalars) uniformly,
    then we flatten to 1-D and hand back plain Python floats.
    """
    return np.asarray(vector_like, dtype=float).reshape(-1).tolist()
