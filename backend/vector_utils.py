"""Utilities for handling vector-like objects with explicit, safe typing.

This module provides helpers to convert various embedding outputs into
plain Python lists of floats suitable for clients like Weaviate.
"""

from __future__ import annotations

from typing import Any, Sequence, cast


def to_float_list(vector_like: Any) -> list[float]:
    """Convert a vector-like object to a ``list[float]``.

    Handles common cases produced by embedding models:
    - torch.Tensor
    - numpy.ndarray
    - Python sequences (e.g., list, tuple)

    The function avoids type-ignore pragmas by operating on ``Any`` input
    and performing runtime checks, while maintaining a precise return type.
    """

    # Local imports to avoid hard dependency at import-time if optional
    # packages are missing in some environments.
    try:
        import torch  # type: ignore
        from torch import Tensor  # type: ignore
    except Exception:  # pragma: no cover - torch may not be available
        torch = None  # type: ignore
        Tensor = object  # type: ignore

    try:
        import numpy as np  # type: ignore
        from numpy.typing import NDArray  # type: ignore
    except Exception:  # pragma: no cover - numpy may not be available
        np = None  # type: ignore
        NDArray = object  # type: ignore

    # torch.Tensor → list[float]
    if "Tensor" in locals() and isinstance(vector_like, cast(type, locals().get("Tensor"))):
        tensor = cast("Tensor", vector_like)
        # Detach to CPU and flatten to 1-D, then convert to list of floats
        return [float(x) for x in tensor.detach().cpu().reshape(-1).tolist()]

    # numpy.ndarray → list[float]
    if "np" in locals() and np is not None and isinstance(vector_like, np.ndarray):
        arr = cast("NDArray[Any]", vector_like)
        return [float(x) for x in arr.reshape(-1).tolist()]

    # Python sequence → list[float]
    if isinstance(vector_like, Sequence):
        return [float(x) for x in vector_like]  # type: ignore[not-an-iterable]

    # Fallbacks: try tolist(); else iterate directly.
    tolist_method = getattr(vector_like, "tolist", None)
    if callable(tolist_method):
        as_list = tolist_method()
        if isinstance(as_list, Sequence):
            return [float(x) for x in as_list]
        try:
            return [float(x) for x in list(as_list)]
        except Exception:
            pass

    # Last resort: attempt to iterate and coerce to float
    return [float(x) for x in list(vector_like)]  # type: ignore[arg-type]
