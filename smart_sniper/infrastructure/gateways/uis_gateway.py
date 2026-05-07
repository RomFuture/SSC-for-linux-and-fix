import re
import time
from typing import Optional, Sequence

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from smart_sniper.application.ports import LoggerPort, UisGatewayPort
from smart_sniper.domain.models import ScanResult, Target
from smart_sniper.infrastructure.constants import UIS_LOGIN_URL


class SeleniumUisGateway(UisGatewayPort):
    def login(self, driver: WebDriver, username: str, password: str, logger: LoggerPort) -> bool:
        logger.log("🔵 Přihlašuji do UIS...")
        driver.get(UIS_LOGIN_URL)
        time.sleep(2)
        try:
            driver.find_element(By.XPATH, "//a[contains(@href, 'lang=cz')]").click()
            time.sleep(2)
        except Exception:
            pass
        try:
            driver.find_element(By.XPATH, "//div[@data-sysid='email']").click()
        except Exception:
            pass

        try:
            try:
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "credential_0"))
                )
                driver.find_element(By.ID, "credential_0").clear()
                driver.find_element(By.ID, "credential_0").send_keys(username)
                driver.find_element(By.ID, "credential_1").clear()
                driver.find_element(By.ID, "credential_1").send_keys(password)
                driver.find_element(By.ID, "credential_1").send_keys(Keys.RETURN)
            except Exception:
                logger.log("⚠️ Automatické vyplnění selhalo, zkus to ručně.")

            time.sleep(5)
            if len(driver.find_elements(By.ID, "credential_1")) > 0:
                logger.log("❗ Přihlášení asi neprošlo. Zkouším čekat na ruční vstup...")
                try:
                    WebDriverWait(driver, 60).until_not(
                        EC.presence_of_element_located((By.ID, "credential_1"))
                    )
                    return True
                except Exception:
                    return False
            return True
        except Exception:
            return False

    def navigate_to_exams(self, driver: WebDriver) -> bool:
        try:
            if "moje_studium" not in driver.current_url:
                try:
                    driver.find_element(By.PARTIAL_LINK_TEXT, "Portál studenta").click()
                    time.sleep(2)
                except Exception:
                    try:
                        driver.find_element(
                            By.XPATH, "//span[contains(text(), 'Moje studium')]"
                        ).click()
                        time.sleep(2)
                    except Exception:
                        pass
            try:
                driver.find_element(
                    By.XPATH, "//span[@data-sysid='prihlasovani-zkousky']/.."
                ).click()
            except Exception:
                driver.get("https://is.czu.cz/auth/student/terminy_seznam.pl?lang=cz")
            time.sleep(2)
            return True
        except Exception:
            return False

    def detect_study_info(self, driver: WebDriver) -> Optional[str]:
        try:
            try:
                titulek_elem = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "titulek"))
                )
                full_text = titulek_elem.text
            except Exception:
                full_text = driver.find_element(By.TAG_NAME, "body").text

            match = re.search(
                r"Studium\s*[-–—]?\s*(.+?)(?:,|$|\sobdobí)",
                full_text,
                re.IGNORECASE,
            )
            if not match:
                return None

            study_part = match.group(1).strip()
            study_part = study_part.split("[")[0].split("(")[0].strip()
            study_part = re.sub(r"\s+", " ", study_part)
            return study_part
        except Exception:
            return None

    def scan_subjects(self, driver: WebDriver) -> ScanResult:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "table_2")))
        rows = driver.find_elements(By.XPATH, "//table[@id='table_2']//tbody/tr")
        data_map = {}
        all_subjects = set()
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) > 9:
                subject = cells[4].text.strip()
                teacher = cells[9].text.strip()
                if subject:
                    all_subjects.add(subject)
                    if teacher:
                        if teacher not in data_map:
                            data_map[teacher] = set()
                        data_map[teacher].add(subject)
        return ScanResult(
            teacher_to_subjects={k: sorted(list(v)) for k, v in data_map.items()},
            all_subjects=sorted(list(all_subjects)),
        )

    def refresh_exam_table(self, driver: WebDriver) -> bool:
        try:
            driver.refresh()
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "table_2")))
            return True
        except TimeoutException:
            return False

    def get_registered_subject_rows(self, driver: WebDriver) -> list[str]:
        rows = []
        try:
            rows1 = driver.find_elements(By.XPATH, "//table[@id='table_1']//tbody/tr")
            for row in rows1:
                rows.append(row.text)
        except Exception:
            pass
        return rows

    def find_available_rows(self, driver: WebDriver, target: Target) -> list:
        xpath = f"//table[@id='table_2']//tr[contains(., '{target.subject}')]"
        if target.date:
            xpath += f"[contains(., '{target.date}')]"
        if target.teacher_filter:
            xpath += f"[contains(., '{target.teacher_filter}')]"
        return driver.find_elements(By.XPATH, xpath)

    def row_matches_blacklist(self, row, blacklist: Sequence[str]) -> bool:
        return any(token in row.text for token in blacklist)

    def has_registered_subject(self, my_subject_rows: Sequence[str], subject: str) -> bool:
        return any(subject in row_text for row_text in my_subject_rows)

    def unregister_subject(self, driver: WebDriver, subject: str, row) -> bool:
        row_to_unreg_xpath = f"//table[@id='table_1']//tr[contains(., '{subject}')]"
        try:
            row_to_unreg = driver.find_element(By.XPATH, row_to_unreg_xpath)
        except NoSuchElementException:
            return False

        try:
            unreg_btn = row_to_unreg.find_element(
                By.XPATH, ".//a[contains(@href, 'odhlasit_ihned=1')]"
            )
        except NoSuchElementException:
            return False

        try:
            unreg_btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", unreg_btn)
        try:
            driver.switch_to.alert.accept()
        except Exception:
            pass

        try:
            WebDriverWait(driver, 10).until(EC.staleness_of(row))
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "table_2")))
        except Exception:
            time.sleep(2)
        return True

    def register_from_row(self, driver: WebDriver, row, target: Target) -> bool:
        xpath = (
            ".//a[contains(@href, 'prihlasit_ihned=1')] | "
            ".//span[@data-sysid='small-arrow-right-double']/.."
        )
        try:
            btn = row.find_element(By.XPATH, xpath)
        except Exception:
            rows_retry = self.find_available_rows(driver, target)
            if not rows_retry:
                return False
            row = rows_retry[0]
            btn = row.find_element(By.XPATH, xpath)
        try:
            btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", btn)
        try:
            WebDriverWait(driver, 3).until(EC.alert_is_present())
            driver.switch_to.alert.accept()
        except Exception:
            pass
        return True

    def fetch_enrolled_exams(self, driver: WebDriver) -> list[str]:
        lines = []
        driver.get("https://is.czu.cz/auth/student/terminy_seznam.pl?lang=cz")
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "table_1")))
        rows = driver.find_elements(By.XPATH, "//table[@id='table_1']//tbody/tr")
        if not rows:
            return ["ℹ️ Nemáš zapsané žádné zkoušky."]
        lines.append(f"✅ Nalezeno termínů: {len(rows)}")
        lines.append("-" * 40)
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 9:
                kod = cells[2].text.strip()
                nazev = cells[3].text.strip()
                datum_cas = " ".join(cells[5].text.strip().split())
                mistnost = cells[6].text.strip()
                vypsal = cells[8].text.strip()
                lines.append(
                    f"📚 {kod} | {nazev}\n📅 {datum_cas}\n🏫 Místnost: {mistnost}\n👨‍🏫 Vyučující: {vypsal}\n"
                    + "-" * 40
                )
            elif len(cells) >= 6:
                kod = cells[2].text.strip()
                nazev = cells[3].text.strip()
                datum_cas = " ".join(cells[5].text.strip().split())
                lines.append(f"📚 {kod} | {nazev}\n📅 {datum_cas}\n" + "-" * 40)
            else:
                lines.append(f"📌 {row.text}\n" + "-" * 40)
        return lines

