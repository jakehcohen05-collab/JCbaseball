"""JCBaseballLab evaluation engine.

The forward-looking layer on top of the descriptive PVI/HVI/DVI composites:

  projection  — descriptive index history  →  projected next-season index
  valuation   — projected index            →  WAR  →  dollars  →  surplus value
  teambuilder — roster of projected WARs    →  wins, needs, and best targets

All pure-Python, standard-library only, fully tested. Feed it your own data;
calibrate the documented constants; own the whole pipeline.
"""

__version__ = "0.1.0"

from . import aging, player, projection, teambuilder, valuation  # noqa: F401
