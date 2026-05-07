import re
from datetime import datetime, time


def parse_time(value: str) -> time:
    return datetime.strptime(value.strip(), "%H:%M").time()


def matches_date(user_input: str, href_date_str: str, cell_text: str) -> bool:
    normalized_input = user_input.strip().lower()
    if not href_date_str:
        if "." in normalized_input:
            return normalized_input in cell_text.lower()
        return re.match(r"^0?" + re.escape(normalized_input) + r"\b", cell_text) is not None

    y_raw, m_raw, d_raw = href_date_str.split("-")
    y, m, d = int(y_raw), int(m_raw), int(d_raw)
    valid_formats = [
        str(d),
        f"0{d}" if d < 10 else str(d),
        f"{d}.{m}.",
        f"{d:02d}.{m:02d}.",
        f"{d}.{m}.{y}",
        f"{d:02d}.{m:02d}.{y}",
        f"{y}-{m:02d}-{d:02d}",
    ]
    return normalized_input in valid_formats

