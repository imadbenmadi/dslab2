"""PCNME (Predictive Cloud-Native Mobile Edge) framework."""

from importlib.metadata import PackageNotFoundError, version


def __getattr__(name: str):
    if name == "__version__":
        try:
            return version("pcnme")
        except PackageNotFoundError:
            return "0.0.0"
    raise AttributeError(name)


__all__ = ["__version__"]
