"""Clean pill status badges for Cadence enterprise UI."""

def get_status_badge_html(status: str, compact: bool = False) -> str:
    """Return clean pill badge HTML string for a given status."""
    st_upper = status.upper().strip()
    
    if st_upper in ["ON TRACK", "HEALTHY", "DONE", "PASSED"]:
        bg = "#F0FDF4"
        fg = "#15803D"
        border = "#BBF7D0"
        dot = "#22C55E"
    elif st_upper in ["AT RISK", "CAUTIOUS", "MEDIUM"]:
        bg = "#FFFBEB"
        fg = "#B45309"
        border = "#FDE68A"
        dot = "#F59E0B"
    elif st_upper in ["DELAYED", "CRITICAL", "BLOCKED", "HIGH", "FAILED"]:
        bg = "#FEF2F2"
        fg = "#B91C1C"
        border = "#FECACA"
        dot = "#EF4444"
    else:  # Open / Low / Neutral
        bg = "#F8FAFC"
        fg = "#475569"
        border = "#E2E8F0"
        dot = "#94A3B8"

    padding = "2px 8px" if compact else "4px 12px"
    font_size = "11px" if compact else "12px"

    return (
        f'<span style="background:{bg}; color:{fg}; border:1px solid {border}; '
        f'padding:{padding}; border-radius:999px; font-size:{font_size}; font-weight:700; '
        f'display:inline-flex; align-items:center; gap:6px; letter-spacing:0.04em;">'
        f'<span style="width:6px; height:6px; border-radius:50%; background:{dot}; flex-shrink:0;"></span>'
        f'{st_upper}'
        f'</span>'
    )
