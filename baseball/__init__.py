"""Baseball analysis database.

A small, dependency-free toolkit for storing baseball box-score data in SQLite
and computing sabermetric statistics on top of it.
"""

__version__ = "0.1.0"

from . import analysis, db, sabermetrics, seed  # noqa: F401
