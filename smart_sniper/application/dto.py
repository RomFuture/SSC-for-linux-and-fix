from dataclasses import dataclass
from typing import List

from smart_sniper.application.cancellation import CancellationToken
from smart_sniper.domain.models import Target


@dataclass(frozen=True)
class Credentials:
    username: str
    password: str


@dataclass(frozen=True)
class UisSniperCommand:
    credentials: Credentials
    targets: List[Target]
    blacklist: List[str]
    use_outlook: bool
    cancellation: CancellationToken


@dataclass(frozen=True)
class UisDogCommand:
    credentials: Credentials
    targets: List[Target]
    blacklist: List[str]
    cancellation: CancellationToken


@dataclass(frozen=True)
class UisScanCommand:
    credentials: Credentials


@dataclass(frozen=True)
class TcSniperCommand:
    credentials: Credentials
    tc_url: str
    tc_filter: str
    days: List[str]
    start_time: str
    end_time: str
    should_book: bool
    cancellation: CancellationToken


@dataclass(frozen=True)
class EnrolledTermsCommand:
    credentials: Credentials
    tc_url: str

