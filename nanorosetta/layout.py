from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Literal, Sequence, Tuple

import numpy as np
from shapely.geometry import MultiPolygon, LineString
from shapely.ops import unary_union

Orientation = Literal["tangent", "upright"]


@dataclass
class PageSpec:
    doc_index: int
    page_index: int
    width_pt: float
    height_pt: float

    @property
    def aspect_ratio(self) -> float:
        return self.width_pt / self.height_pt if self.height_pt else 1.0


@dataclass
class Placement:
    page_global_index: int
    doc_index: int
    page_index: int
    center_xy_mm: Tuple[float, float]
    width_mm: float
    height_mm: float
    rotation_deg: float


def _offset_boundaries(region: MultiPolygon, offsets_mm: Sequence[float]) -> List[LineString]:
    # Approximate streamlines by boundaries offset inward from outer boundary
    boundaries: List[LineString] = []
    for off in offsets_mm:
        inset = region.buffer(-off)
        if inset.is_empty:
            continue
        geom = unary_union(inset)
        for poly in getattr(geom, "geoms", [geom]):
            if hasattr(poly, "exterior"):
                boundaries.append(LineString(poly.exterior.coords))
    return boundaries


def _arc_length_positions(path: LineString, step_mm: float) -> List[Tuple[float, float, float]]:
    coords = list(path.coords)
    if len(coords) < 2:
        return []
    # Cumulative arc-lengths
    seg_lengths = []
    for i in range(1, len(coords)):
        x0, y0 = coords[i - 1]
        x1, y1 = coords[i]
        seg_lengths.append(math.hypot(x1 - x0, y1 - y0))
    total = sum(seg_lengths)
    if total <= 0:
        return []
    positions: List[Tuple[float, float, float]] = []
    s = 0.0
    target = 0.0
    idx = 1
    while target <= total and idx < len(coords):
        # advance until we reach target along segments
        while idx < len(coords) and s + seg_lengths[idx - 1] < target:
            s += seg_lengths[idx - 1]
            idx += 1
        if idx >= len(coords):
            break
        # interpolate within segment
        remain = target - s
        seg_len = seg_lengths[idx - 1]
        t = 0.0 if seg_len == 0 else remain / seg_len
        x0, y0 = coords[idx - 1]
        x1, y1 = coords[idx]
        x = x0 + t * (x1 - x0)
        y = y0 + t * (y1 - y0)
        # local tangent angle
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
        positions.append((x, y, ang))
        target += step_mm
    return positions


def plan_layout_any_shape(
    pages: List[PageSpec],
    allowed_region_mm: MultiPolygon,
    nominal_height_mm: float,
    gap_mm: float,
    orientation: Orientation = "tangent",
    scale_min: float = 0.1,
    scale_max: float = 1.0,
    streamline_step_mm: float = 2.0,
    max_streamlines: int = 200,
) -> List[Placement]:
    placements: List[Placement] = []
    if not pages or allowed_region_mm.is_empty:
        return placements

    # Generate inward offsets as streamlines
    offsets = [i * streamline_step_mm for i in range(max_streamlines)]
    lines = _offset_boundaries(allowed_region_mm, offsets)

    page_cursor = 0
    page_count = len(pages)

    for ln in lines:
        if page_cursor >= page_count:
            break
        # Determine per-page width from aspect and nominal height
        spec = pages[page_cursor]
        height_mm = nominal_height_mm
        width_mm = spec.aspect_ratio * height_mm
        step = width_mm + gap_mm

        for x, y, ang in _arc_length_positions(ln, step_mm=step):
            spec = pages[page_cursor]
            height_mm = nominal_height_mm
            width_mm = spec.aspect_ratio * height_mm
            rot = 0.0
            if orientation == "tangent":
                rot = ang
            placement = Placement(
                page_global_index=page_cursor,
                doc_index=spec.doc_index,
                page_index=spec.page_index,
                center_xy_mm=(x, y),
                width_mm=width_mm,
                height_mm=height_mm,
                rotation_deg=rot,
            )
            placements.append(placement)
            page_cursor += 1
            if page_cursor >= page_count:
                break

    return placements
