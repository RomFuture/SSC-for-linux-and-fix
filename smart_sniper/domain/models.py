from dataclasses import dataclass, field
from datetime import time
from typing import Dict, List


@dataclass(frozen=True)
class Target:
    subject: str
    date: str = ""
    teacher_filter: str = ""
    original_line: str = ""

    def to_line(self) -> str:
        return f"{self.subject};{self.date};{self.teacher_filter}"


@dataclass(frozen=True)
class TimeWindow:
    start: time
    end: time


@dataclass(frozen=True)
class ScanResult:
    teacher_to_subjects: Dict[str, List[str]] = field(default_factory=dict)
    all_subjects: List[str] = field(default_factory=list)

