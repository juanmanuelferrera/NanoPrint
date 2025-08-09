from __future__ import annotations

from typing import List, Tuple

import numpy as np
from shapely.geometry import Polygon, MultiPolygon, LinearRing
from shapely.ops import unary_union
from svgpathtools import svg2paths


def _path_to_polygon(path, samples_per_curve: int = 50) -> Polygon:
    pts: List[Tuple[float, float]] = []
    for seg in path:
        for t in np.linspace(0, 1, samples_per_curve, endpoint=True):
            z = seg.point(t)
            pts.append((z.real, z.imag))
    if len(pts) < 3:
        return Polygon()
    ring = LinearRing(pts)
    if not ring.is_ccw:
        pts = list(reversed(pts))
    return Polygon(pts)


def load_svg_polygons(svg_path: str) -> MultiPolygon:
    paths, _ = svg2paths(svg_path)
    polys: List[Polygon] = []
    for p in paths:
        poly = _path_to_polygon(p)
        if not poly.is_empty and poly.is_valid:
            polys.append(poly)
    if not polys:
        return MultiPolygon([])
    merged = unary_union(polys)
    if isinstance(merged, Polygon):
        return MultiPolygon([merged])
    return merged


def boolean_allowed_region(outer: MultiPolygon, inners: List[MultiPolygon]) -> MultiPolygon:
    region = unary_union(outer)
    for inner in inners:
        region = region.difference(unary_union(inner))
    # Normalize
    if isinstance(region, Polygon):
        return MultiPolygon([region])
    return region
