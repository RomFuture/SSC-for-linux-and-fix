import re
import time
from datetime import datetime, time as time_type
from typing import List, Sequence, Tuple

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from smart_sniper.application.ports import LoggerPort, MoodleGatewayPort, NotifierPort
from smart_sniper.domain.time_matching import matches_date
from smart_sniper.infrastructure.constants import MOODLE_LOGIN_URL


class SeleniumMoodleGateway(MoodleGatewayPort):
    def open_login(self, driver: WebDriver) -> None:
        driver.get(MOODLE_LOGIN_URL)

    def fill_username_if_present(self, driver: WebDriver, username: str) -> None:
        try:
            driver.find_element(By.ID, "username").send_keys(username)
        except Exception:
            pass

    def wait_until_logged_in(
        self, driver: WebDriver, cancellation=None, timeout_seconds: int = 180
    ) -> bool:
        loops = max(1, timeout_seconds // 2)
        for _ in range(loops):
            if cancellation and cancellation.is_cancelled():
                return False
            curr_url = driver.current_url.lower()
            if "login" not in curr_url and "oauth" not in curr_url and "saml" not in curr_url:
                return True
            time.sleep(2)
        return False

    def open_tc_page(self, driver: WebDriver, tc_url: str) -> None:
        driver.get(tc_url)

    def expand_change_buttons(self, driver: WebDriver, logger: LoggerPort) -> None:
        try:
            change_btn = driver.find_elements(
                By.XPATH,
                "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'změnit termín rezervace')] | "
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'změnit termín rezervace')] | "
                "//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'změnit termín rezervace')]",
            )
            if change_btn:
                logger.log("🔄 Detekován již rezervovaný termín! Rozbaluji menu pro změnu...")
                driver.execute_script("arguments[0].click();", change_btn[0])
                time.sleep(1)
        except Exception:
            pass

        try:
            change_btns = driver.find_elements(By.XPATH, "//span[@data-toggle='collapse']")
            for btn in change_btns:
                if btn.get_attribute("aria-expanded") == "false":
                    driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.3)
        except Exception:
            pass

    def find_time_links(self, driver: WebDriver) -> list:
        links = []
        for element in driver.find_elements(By.XPATH, "//a | //button"):
            try:
                text = (element.get_attribute("textContent") or "").strip().lower()
                if ("rezervovat" in text or "změnit" in text) and " - " in text and len(text) < 30:
                    links.append(element)
            except Exception:
                pass
        return links

    def click_matching_time_link(
        self,
        driver: WebDriver,
        links: list,
        start_time: time_type,
        end_time: time_type,
        logger: LoggerPort,
        notifier: NotifierPort,
        should_book: bool,
    ) -> bool:
        found_any_time = False
        for link in links:
            try:
                txt = (link.get_attribute("textContent") or "").strip()
                if " - " not in txt:
                    continue
                found_any_time = True
                ct_str = txt.split(" - ")[0].strip()
                candidate_time = datetime.strptime(ct_str, "%H:%M").time()
                if not (start_time <= candidate_time <= end_time):
                    continue
                logger.log(f"✅ Čas {ct_str} vyhovuje!")
                notifier.notify_slot_found()
                if should_book:
                    logger.log("🖱️ Odesílám požadavek na zapsání...")
                    href = link.get_attribute("href")
                    if href and not href.startswith("javascript"):
                        driver.get(href)
                    else:
                        driver.execute_script(
                            """
                            window.confirm = function() { return true; };
                            window.alert = function() { return true; };
                            if(typeof confirmTC !== 'undefined') { window.confirmTC = function() { return true; }; }
                            """
                        )
                        time.sleep(0.2)
                        driver.execute_script("arguments[0].click();", link)

                    time.sleep(2.5)
                    try:
                        confirm_btns = driver.find_elements(
                            By.XPATH, "//input[@type='submit' or @type='button'] | //button"
                        )
                        for btn in confirm_btns:
                            val = (btn.get_attribute("value") or btn.text or "").lower()
                            if any(
                                word in val
                                for word in [
                                    "ano",
                                    "yes",
                                    "pokračovat",
                                    "continue",
                                    "potvrdit",
                                    "confirm",
                                    "uložit",
                                    "save",
                                    "rezervovat",
                                ]
                            ):
                                logger.log(f"⚠️ Moodle vyžaduje extra potvrzení ('{val}')...")
                                driver.execute_script("arguments[0].click();", btn)
                                time.sleep(1)
                                break
                    except Exception:
                        pass

                    logger.log("🎉 Hotovo! Tvá akce byla dokončena.")
                return True
            except Exception:
                pass

        if found_any_time:
            logger.log(
                f"❌ Nalezené časy nevyhovují filtru ({start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')})."
            )
        return False

    def find_day_cells(self, driver: WebDriver, tc_filter: str, loop_count: int, logger: LoggerPort) -> list:
        tc_filter = tc_filter.strip().lower()
        target_div_id = None
        if tc_filter:
            h3_elements = driver.find_elements(By.TAG_NAME, "h3")
            for h3 in h3_elements:
                if tc_filter in h3.text.lower():
                    try:
                        href = h3.find_element(By.TAG_NAME, "a").get_attribute("href")
                        match = re.search(r"id=(\d+)", href)
                        if match:
                            target_div_id = f"test{match.group(1)}"
                            break
                    except Exception:
                        pass
            if target_div_id:
                return driver.find_elements(
                    By.CSS_SELECTOR, f"div#{target_div_id} td.alert.alert-success"
                )
            if loop_count == 1:
                logger.log(f"⚠️ Test s názvem '{tc_filter}' nenalezen, hledám ve všech...")
        return driver.find_elements(By.CSS_SELECTOR, "td.alert.alert-success")

    def open_first_matching_day(
        self, driver: WebDriver, day_cells: list, desired_days: Sequence[str], logger: LoggerPort
    ) -> bool:
        for cell in day_cells:
            try:
                links = cell.find_elements(By.TAG_NAME, "a")
                if not links:
                    continue
                link = links[0]
                text = (link.get_attribute("textContent") or "").strip()
                if "rezervovat" in text.lower() or "změnit" in text.lower():
                    continue
                href = link.get_attribute("href") or ""
                match = re.search(r"day=(\d{4}-\d{2}-\d{2})", href)
                href_date = match.group(1) if match else None
                for desired_day in desired_days:
                    if matches_date(desired_day, href_date, text):
                        logger.log(f"📅 Nalezen volný den: {text[:10]}...! Otevírám detail...")
                        if href and not href.startswith("javascript"):
                            driver.get(href)
                        else:
                            driver.execute_script("arguments[0].click();", link)
                        return True
            except Exception:
                pass
        return False

    def wait_for_time_links_after_day_open(self, driver: WebDriver, cancellation=None) -> list:
        time.sleep(2)
        try:
            buttons = driver.find_elements(By.XPATH, "//span[@data-toggle='collapse']")
            for btn in buttons:
                if btn.get_attribute("aria-expanded") == "false":
                    driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.5)
        except Exception:
            pass

        for _ in range(8):
            if cancellation and cancellation.is_cancelled():
                return []
            links = self.find_time_links(driver)
            if links:
                return links
            time.sleep(0.5)
        return []

    def fetch_enrolled_terms(self, driver: WebDriver) -> List[Tuple[str, str, str]]:
        rows_out: List[Tuple[str, str, str]] = []
        try:
            tables = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located(
                    (
                        By.XPATH,
                        "//h4[contains(text(), 'Vaše rezervované termíny')]/following-sibling::table[1]",
                    )
                )
            )
            for table in tables:
                rows = table.find_elements(By.TAG_NAME, "tr")
                if len(rows) <= 1:
                    continue
                for row in rows[1:]:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 4:
                        datum = cells[1].text.strip()
                        cas = cells[2].text.strip()
                        stav = cells[4].text.strip() if len(cells) > 4 else ""
                        rows_out.append((datum, cas, stav))
        except TimeoutException:
            return rows_out
        return rows_out

