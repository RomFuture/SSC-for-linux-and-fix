import os
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

from smart_sniper.application.ports import BrowserFactoryPort


class SeleniumBrowserFactory(BrowserFactoryPort):
    def __init__(self, use_brave: bool = True) -> None:
        self.use_brave = use_brave

    def create_driver(self) -> Optional[WebDriver]:
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--remote-allow-origins=*")
        options.add_argument("--disable-gpu")

        if self.use_brave:
            brave_path = self._discover_brave_binary()
            if brave_path:
                options.binary_location = brave_path
                try:
                    service = Service(
                        ChromeDriverManager(chrome_type=ChromeType.BRAVE).install()
                    )
                except Exception:
                    service = Service(ChromeDriverManager().install())
            else:
                service = Service(ChromeDriverManager().install())
        else:
            service = Service(ChromeDriverManager().install())

        try:
            driver = webdriver.Chrome(service=service, options=options)
        except Exception:
            driver = webdriver.Chrome(options=options)
        try:
            driver.maximize_window()
        except Exception:
            pass
        return driver

    def _discover_brave_binary(self) -> str:
        candidates = [
            os.getenv("BRAVE_BINARY_PATH", ""),
            "/usr/bin/brave-browser",
            "/usr/bin/brave",
        ]
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate
        return ""

