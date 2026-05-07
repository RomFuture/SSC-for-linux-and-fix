from datetime import time
from typing import List, Optional, Protocol, Sequence, Tuple

from selenium.webdriver.remote.webdriver import WebDriver

from smart_sniper.domain.models import ScanResult, Target


class LoggerPort(Protocol):
    def log(self, message: str) -> None:
        ...


class ConfigStorePort(Protocol):
    def load(self) -> dict:
        ...

    def save(self, data: dict) -> None:
        ...


class BrowserFactoryPort(Protocol):
    def create_driver(self) -> Optional[WebDriver]:
        ...


class NotifierPort(Protocol):
    def notify_slot_found(self) -> None:
        ...


class UisGatewayPort(Protocol):
    def login(self, driver: WebDriver, username: str, password: str, logger: LoggerPort) -> bool:
        ...

    def navigate_to_exams(self, driver: WebDriver) -> bool:
        ...

    def detect_study_info(self, driver: WebDriver) -> Optional[str]:
        ...

    def scan_subjects(self, driver: WebDriver) -> ScanResult:
        ...

    def refresh_exam_table(self, driver: WebDriver) -> bool:
        ...

    def get_registered_subject_rows(self, driver: WebDriver) -> List[str]:
        ...

    def find_available_rows(self, driver: WebDriver, target: Target) -> list:
        ...

    def row_matches_blacklist(self, row, blacklist: Sequence[str]) -> bool:
        ...

    def has_registered_subject(self, my_subject_rows: Sequence[str], subject: str) -> bool:
        ...

    def unregister_subject(self, driver: WebDriver, subject: str, row) -> bool:
        ...

    def register_from_row(self, driver: WebDriver, row, target: Target) -> bool:
        ...

    def fetch_enrolled_exams(self, driver: WebDriver) -> List[str]:
        ...


class OutlookGatewayPort(Protocol):
    def open_and_wait_ready(self, driver: WebDriver, logger: LoggerPort) -> Optional[str]:
        ...

    def has_unread_subject_notification(self, driver: WebDriver, targets: Sequence[Target]) -> bool:
        ...


class MoodleGatewayPort(Protocol):
    def open_login(self, driver: WebDriver) -> None:
        ...

    def fill_username_if_present(self, driver: WebDriver, username: str) -> None:
        ...

    def wait_until_logged_in(self, driver: WebDriver, cancellation=None, timeout_seconds: int = 180) -> bool:
        ...

    def open_tc_page(self, driver: WebDriver, tc_url: str) -> None:
        ...

    def expand_change_buttons(self, driver: WebDriver, logger: LoggerPort) -> None:
        ...

    def find_time_links(self, driver: WebDriver) -> list:
        ...

    def click_matching_time_link(self, driver: WebDriver, links: list, start_time: time, end_time: time, logger: LoggerPort, notifier: NotifierPort, should_book: bool) -> bool:
        ...

    def find_day_cells(self, driver: WebDriver, tc_filter: str, loop_count: int, logger: LoggerPort) -> list:
        ...

    def open_first_matching_day(self, driver: WebDriver, day_cells: list, desired_days: Sequence[str], logger: LoggerPort) -> bool:
        ...

    def wait_for_time_links_after_day_open(self, driver: WebDriver, cancellation=None) -> list:
        ...

    def fetch_enrolled_terms(self, driver: WebDriver) -> List[Tuple[str, str, str]]:
        ...

