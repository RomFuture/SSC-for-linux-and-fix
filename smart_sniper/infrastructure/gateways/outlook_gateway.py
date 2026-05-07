from typing import Optional, Sequence

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from smart_sniper.application.ports import LoggerPort, OutlookGatewayPort
from smart_sniper.domain.models import Target
from smart_sniper.infrastructure.constants import OUTLOOK_URL


class SeleniumOutlookGateway(OutlookGatewayPort):
    def open_and_wait_ready(self, driver: WebDriver, logger: LoggerPort) -> Optional[str]:
        driver.switch_to.new_window("tab")
        logger.log("📧 Otevírám Outlook v novém tabu...")
        driver.get(OUTLOOK_URL)
        outlook_handle = driver.current_window_handle
        logger.log("⏳ Čekám na tvé přihlášení do Outlooku (max 2 min)...")
        try:
            WebDriverWait(driver, 120).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='tree']"))
            )
            logger.log("✅ Outlook připraven. Sleduji poštu...")
            return outlook_handle
        except Exception:
            logger.log("❌ Outlook timeout. Konec.")
            return None

    def has_unread_subject_notification(
        self, driver: WebDriver, targets: Sequence[Target]
    ) -> bool:
        for target in targets:
            xpath = (
                "//div[@role='option' and contains(@aria-label, 'Unread') and "
                "(contains(@aria-label, 'Vypsání termínu') or contains(@aria-label, 'Uvolnění místa')) and "
                f"contains(@aria-label, '{target.subject}')]"
            )
            if driver.find_elements(By.XPATH, xpath):
                return True
        return False

