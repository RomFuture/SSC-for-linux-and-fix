import os
import json
import time
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
        run_id = f"run-{int(time.time() * 1000)}"
        # #region agent log
        self._debug_log(
            run_id=run_id,
            hypothesis_id="H0",
            location="browser_factory.py:create_driver:entry",
            message="create_driver called",
            data={"use_brave": self.use_brave},
        )
        # #endregion
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
            # #region agent log
            self._debug_log(
                run_id=run_id,
                hypothesis_id="H1",
                location="browser_factory.py:create_driver:brave_path",
                message="Brave binary discovery result",
                data={"brave_path": brave_path, "brave_path_found": bool(brave_path)},
            )
            # #endregion
            if brave_path:
                options.binary_location = brave_path
                try:
                    # #region agent log
                    self._debug_log(
                        run_id=run_id,
                        hypothesis_id="H2",
                        location="browser_factory.py:create_driver:manager_brave",
                        message="Installing webdriver manager for Brave",
                        data={"chrome_type": "BRAVE"},
                    )
                    # #endregion
                    service = Service(
                        ChromeDriverManager(chrome_type=ChromeType.BRAVE).install()
                    )
                except Exception as error:
                    # #region agent log
                    self._debug_log(
                        run_id=run_id,
                        hypothesis_id="H2",
                        location="browser_factory.py:create_driver:manager_brave_error",
                        message="Brave webdriver_manager install failed",
                        data={"error_type": type(error).__name__, "error": str(error)},
                    )
                    # #endregion
                    raise
            else:
                # #region agent log
                self._debug_log(
                    run_id=run_id,
                    hypothesis_id="H3",
                    location="browser_factory.py:create_driver:manager_chrome_fallback",
                    message="Falling back to default Chrome webdriver manager",
                    data={"reason": "brave_binary_not_found"},
                )
                # #endregion
                service = Service(ChromeDriverManager().install())
        else:
            service = Service(ChromeDriverManager().install())

        try:
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as error:
            # #region agent log
            self._debug_log(
                run_id=run_id,
                hypothesis_id="H4",
                location="browser_factory.py:create_driver:webdriver_chrome_error",
                message="webdriver.Chrome creation failed",
                data={"error_type": type(error).__name__, "error": str(error)},
            )
            # #endregion
            raise
        try:
            driver.maximize_window()
        except Exception:
            pass
        # #region agent log
        self._debug_log(
            run_id=run_id,
            hypothesis_id="H4",
            location="browser_factory.py:create_driver:success",
            message="Driver created successfully",
            data={"binary_location": options.binary_location or ""},
        )
        # #endregion
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

    def _debug_log(
        self,
        run_id: str,
        hypothesis_id: str,
        location: str,
        message: str,
        data: dict,
    ) -> None:
        try:
            payload = {
                "sessionId": "769bb4",
                "runId": run_id,
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data,
                "timestamp": int(time.time() * 1000),
            }
            with open(
                "/home/romfuture/Projects/Personal/Smart-Sniper-CZU/.cursor/debug-769bb4.log",
                "a",
                encoding="utf-8",
            ) as debug_file:
                debug_file.write(json.dumps(payload, ensure_ascii=True) + "\n")
        except Exception:
            pass

