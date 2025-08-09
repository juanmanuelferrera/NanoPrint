PT_PER_INCH = 72.0
MM_PER_INCH = 25.4


def mm_to_pt(mm: float) -> float:
    return mm * PT_PER_INCH / MM_PER_INCH


def pt_to_mm(pt: float) -> float:
    return pt * MM_PER_INCH / PT_PER_INCH


def mm_to_px(mm: float, dpi: int) -> int:
    return int(round(mm / MM_PER_INCH * dpi))


def px_to_mm(px: int, dpi: int) -> float:
    return px * MM_PER_INCH / dpi
