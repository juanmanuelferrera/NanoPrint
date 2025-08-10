from __future__ import annotations

from typing import List

from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union
from svgpathtools import svg2paths2


def parse_svg_path(svg_path: str) -> MultiPolygon:
    """Parse SVG file and convert to Shapely MultiPolygon."""
    paths, attributes, svg_attributes = svg2paths2(svg_path)
    
    polygons = []
    for path in paths:
        # Convert path to polygon coordinates
        coords = []
        for segment in path:
            if hasattr(segment, 'start'):
                coords.append((segment.start.real, segment.start.imag))
            if hasattr(segment, 'end'):
                coords.append((segment.end.real, segment.end.imag))
        
        if len(coords) >= 3:
            # Close the polygon
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            polygon = Polygon(coords)
            if polygon.is_valid:
                polygons.append(polygon)
    
    if not polygons:
        raise ValueError(f"No valid polygons found in {svg_path}")
    
    return MultiPolygon(polygons)


def boolean_allowed_region(outer: MultiPolygon, inners: List[MultiPolygon]) -> MultiPolygon:
    """Create allowed region by subtracting inner shapes from outer shape."""
    if outer.is_empty:
        raise ValueError("Outer shape is empty")
    
    # Validate that outer shape is larger than inner shapes
    outer_bounds = outer.bounds  # (minx, miny, maxx, maxy)
    outer_area = outer.area
    
    for i, inner in enumerate(inners):
        if inner.is_empty:
            continue
            
        inner_bounds = inner.bounds
        inner_area = inner.area
        
        # Check if inner shape is larger than outer shape
        if inner_area > outer_area * 0.95:  # Allow 5% tolerance
            raise ValueError(f"Inner shape {i} is too large relative to outer shape "
                           f"(inner area: {inner_area:.2f}, outer area: {outer_area:.2f})")
        
        # Check if inner shape extends beyond outer bounds
        if (inner_bounds[0] < outer_bounds[0] or inner_bounds[1] < outer_bounds[1] or
            inner_bounds[2] > outer_bounds[2] or inner_bounds[3] > outer_bounds[3]):
            raise ValueError(f"Inner shape {i} extends beyond outer shape bounds")
    
    # Create allowed region
    region = outer
    for inner in inners:
        region = region.difference(unary_union(inner))
    
    # Validate the resulting region
    if region.is_empty:
        raise ValueError("Allowed region is empty - inner shapes completely fill outer shape")
    
    if region.area < outer_area * 0.01:  # Less than 1% of original area
        raise ValueError(f"Allowed region is too small (area: {region.area:.2f}, "
                        f"original: {outer_area:.2f}) - insufficient space for pages")
    
    # Normalize
    if isinstance(region, Polygon):
        return MultiPolygon([region])
    return region
