from __future__ import annotations

from typing import List

from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union
from svgpathtools import svg2paths2


def diagnose_svg_file(svg_path: str) -> str:
    """Diagnose an SVG file and return information about its contents."""
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        info = f"SVG file: {svg_path}\n"
        info += f"Root element: {root.tag}\n"
        
        # Count different element types
        elements = {}
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            elements[tag] = elements.get(tag, 0) + 1
        
        info += "Elements found:\n"
        for tag, count in elements.items():
            info += f"  {tag}: {count}\n"
        
        # Check for specific shape elements
        shape_elements = ['path', 'rect', 'circle', 'ellipse', 'polygon', 'polyline']
        found_shapes = []
        for shape in shape_elements:
            count = len(root.findall(f'.//{{http://www.w3.org/2000/svg}}{shape}'))
            if count > 0:
                found_shapes.append(f"{shape}: {count}")
        
        if found_shapes:
            info += f"Shape elements: {', '.join(found_shapes)}\n"
        else:
            info += "No shape elements found!\n"
        
        return info
        
    except Exception as e:
        return f"Error diagnosing SVG file {svg_path}: {str(e)}"


def parse_svg_path(svg_path: str) -> MultiPolygon:
    """Parse SVG file and convert to Shapely MultiPolygon."""
    try:
        paths, attributes, svg_attributes = svg2paths2(svg_path)
        
        polygons = []
        
        # Handle path elements
        for path in paths:
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
        
        # If no valid polygons found from paths, try to parse as basic shapes
        if not polygons:
            # Try to parse basic SVG shapes (rect, circle, ellipse, etc.)
            import xml.etree.ElementTree as ET
            tree = ET.parse(svg_path)
            root = tree.getroot()
            
            # Handle rectangle elements
            for rect in root.findall('.//{http://www.w3.org/2000/svg}rect'):
                x = float(rect.get('x', 0))
                y = float(rect.get('y', 0))
                width = float(rect.get('width', 0))
                height = float(rect.get('height', 0))
                
                if width > 0 and height > 0:
                    coords = [(x, y), (x + width, y), (x + width, y + height), (x, y + height), (x, y)]
                    polygon = Polygon(coords)
                    if polygon.is_valid:
                        polygons.append(polygon)
            
            # Handle circle elements
            for circle in root.findall('.//{http://www.w3.org/2000/svg}circle'):
                cx = float(circle.get('cx', 0))
                cy = float(circle.get('cy', 0))
                r = float(circle.get('r', 0))
                
                if r > 0:
                    # Create a polygon approximation of the circle
                    import math
                    num_points = 32
                    coords = []
                    for i in range(num_points + 1):
                        angle = 2 * math.pi * i / num_points
                        x = cx + r * math.cos(angle)
                        y = cy + r * math.sin(angle)
                        coords.append((x, y))
                    
                    polygon = Polygon(coords)
                    if polygon.is_valid:
                        polygons.append(polygon)
            
            # Handle ellipse elements
            for ellipse in root.findall('.//{http://www.w3.org/2000/svg}ellipse'):
                cx = float(ellipse.get('cx', 0))
                cy = float(ellipse.get('cy', 0))
                rx = float(ellipse.get('rx', 0))
                ry = float(ellipse.get('ry', 0))
                
                if rx > 0 and ry > 0:
                    # Create a polygon approximation of the ellipse
                    import math
                    num_points = 32
                    coords = []
                    for i in range(num_points + 1):
                        angle = 2 * math.pi * i / num_points
                        x = cx + rx * math.cos(angle)
                        y = cy + ry * math.sin(angle)
                        coords.append((x, y))
                    
                    polygon = Polygon(coords)
                    if polygon.is_valid:
                        polygons.append(polygon)
        
        if not polygons:
            raise ValueError(f"No valid polygons found in {svg_path}. "
                           f"Supported elements: <path>, <rect>, <circle>, <ellipse>. "
                           f"Please check that the SVG contains valid shape elements.")
        
        return MultiPolygon(polygons)
        
    except Exception as e:
        raise ValueError(f"Failed to parse SVG file {svg_path}: {str(e)}. "
                        f"Please ensure the file is a valid SVG with shape elements.")


def position_inner_shape_relative(
    inner: MultiPolygon, 
    outer: MultiPolygon, 
    position: str = "center"
) -> MultiPolygon:
    """
    Position inner shape relative to outer shape.
    
    Args:
        inner: Inner shape to position
        outer: Outer shape to position relative to
        position: Where to place inner shape. Options:
                 "center" (default), "top-left", "top-center", "top-right",
                 "middle-left", "middle-right", "bottom-left", "bottom-center", "bottom-right"
    
    Returns:
        Repositioned inner shape
    """
    from shapely.affinity import translate
    
    # Get bounds
    outer_bounds = outer.bounds  # (minx, miny, maxx, maxy)
    inner_bounds = inner.bounds
    
    outer_width = outer_bounds[2] - outer_bounds[0]
    outer_height = outer_bounds[3] - outer_bounds[1] 
    outer_center_x = outer_bounds[0] + outer_width / 2
    outer_center_y = outer_bounds[1] + outer_height / 2
    
    inner_width = inner_bounds[2] - inner_bounds[0]
    inner_height = inner_bounds[3] - inner_bounds[1]
    inner_center_x = inner_bounds[0] + inner_width / 2
    inner_center_y = inner_bounds[1] + inner_height / 2
    
    # Calculate target position based on position parameter
    if position == "center":
        target_x = outer_center_x
        target_y = outer_center_y
    elif position == "top-left":
        target_x = outer_bounds[0] + inner_width / 2
        target_y = outer_bounds[3] - inner_height / 2
    elif position == "top-center":
        target_x = outer_center_x
        target_y = outer_bounds[3] - inner_height / 2
    elif position == "top-right":
        target_x = outer_bounds[2] - inner_width / 2
        target_y = outer_bounds[3] - inner_height / 2
    elif position == "middle-left":
        target_x = outer_bounds[0] + inner_width / 2
        target_y = outer_center_y
    elif position == "middle-right":
        target_x = outer_bounds[2] - inner_width / 2
        target_y = outer_center_y
    elif position == "bottom-left":
        target_x = outer_bounds[0] + inner_width / 2
        target_y = outer_bounds[1] + inner_height / 2
    elif position == "bottom-center":
        target_x = outer_center_x
        target_y = outer_bounds[1] + inner_height / 2
    elif position == "bottom-right":
        target_x = outer_bounds[2] - inner_width / 2
        target_y = outer_bounds[1] + inner_height / 2
    else:
        raise ValueError(f"Unknown position: {position}")
    
    # Calculate translation needed
    dx = target_x - inner_center_x
    dy = target_y - inner_center_y
    
    # Apply translation
    return translate(inner, dx, dy)


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
