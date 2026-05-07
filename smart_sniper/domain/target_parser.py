from typing import Iterable, List

from smart_sniper.domain.models import Target


def parse_targets(lines: Iterable[str]) -> List[Target]:
    targets: List[Target] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(";")
        subject = parts[0].strip() if parts else ""
        if not subject:
            continue
        date = parts[1].strip() if len(parts) > 1 else ""
        teacher_filter = parts[2].strip() if len(parts) > 2 else ""
        targets.append(
            Target(
                subject=subject,
                date=date,
                teacher_filter=teacher_filter,
                original_line=line,
            )
        )
    return targets


def parse_blacklist(raw_blacklist: str) -> List[str]:
    return [token.strip() for token in raw_blacklist.split(";") if token.strip()]

