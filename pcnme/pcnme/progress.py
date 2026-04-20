"""Progress bar helpers.

This module centralizes the optional dependency on tqdm.
If tqdm isn't installed, the code falls back to no-op progress objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Optional, TypeVar, overload

T = TypeVar("T")

try:
    from tqdm.auto import tqdm as _tqdm  # type: ignore
except Exception:  # pragma: no cover
    _tqdm = None


@dataclass
class _NullTqdm:
    total: Optional[int] = None

    def update(self, n: int = 1) -> None:  # noqa: D401
        """No-op update."""

    def close(self) -> None:  # noqa: D401
        """No-op close."""

    def set_postfix(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
        """No-op postfix."""

    def write(self, _msg: str) -> None:  # noqa: D401
        """No-op write."""

    def __enter__(self) -> "_NullTqdm":
        return self

    def __exit__(
        self,
        _exc_type: Optional[type[BaseException]],
        _exc: Optional[BaseException],
        _tb: Optional[Any],
    ) -> None:
        self.close()


@overload
def progress(iterable: Iterable[T], *, desc: str | None = None, total: int | None = None,
             unit: str = "it", leave: bool = True, **kwargs: Any) -> Iterable[T]:
    ...


@overload
def progress(iterable: None = None, *, desc: str | None = None, total: int | None = None,
             unit: str = "it", leave: bool = True, **kwargs: Any) -> Any:
    ...


def progress(
    iterable: Optional[Iterable[T]] = None,
    *,
    desc: Optional[str] = None,
    total: Optional[int] = None,
    unit: str = "it",
    leave: bool = True,
    **kwargs: Any,
):
    """Return a tqdm progress iterator (or a no-op fallback).

    - If `iterable` is provided, returns an iterable wrapper.
    - If `iterable` is None, returns a manual progress object with `.update()`.
    """

    if _tqdm is None:
        if iterable is not None:
            return iterable
        return _NullTqdm(total=total)

    if iterable is not None:
        return _tqdm(iterable, total=total, desc=desc, unit=unit, leave=leave, **kwargs)

    return _tqdm(total=total, desc=desc, unit=unit, leave=leave, **kwargs)
