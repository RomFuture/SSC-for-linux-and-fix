import random
import time
from typing import Callable, Optional

from selenium.common.exceptions import StaleElementReferenceException, WebDriverException

from smart_sniper.application.dto import (
    EnrolledTermsCommand,
    TcSniperCommand,
    UisDogCommand,
    UisScanCommand,
    UisSniperCommand,
)
from smart_sniper.application.ports import (
    BrowserFactoryPort,
    LoggerPort,
    MoodleGatewayPort,
    NotifierPort,
    OutlookGatewayPort,
    UisGatewayPort,
)
from smart_sniper.domain.models import ScanResult
from smart_sniper.domain.time_matching import parse_time


class RunUisSniperUseCase:
    def __init__(
        self,
        browser_factory: BrowserFactoryPort,
        uis_gateway: UisGatewayPort,
        outlook_gateway: OutlookGatewayPort,
    ) -> None:
        self.browser_factory = browser_factory
        self.uis_gateway = uis_gateway
        self.outlook_gateway = outlook_gateway

    def execute(
        self,
        command: UisSniperCommand,
        logger: LoggerPort,
        on_target_enrolled: Optional[Callable[[str], None]] = None,
        on_study_info: Optional[Callable[[str], None]] = None,
    ) -> None:
        driver = self.browser_factory.create_driver()
        if not driver:
            return

        try:
            if not self.uis_gateway.login(
                driver,
                command.credentials.username,
                command.credentials.password,
                logger,
            ):
                logger.log("❌ Přihlášení selhalo.")
                return

            self.uis_gateway.navigate_to_exams(driver)
            detected_info = self.uis_gateway.detect_study_info(driver)
            if detected_info and on_study_info:
                on_study_info(detected_info)

            uis_handle = driver.current_window_handle
            active_checking_mode = not command.use_outlook
            outlook_handle = None
            if command.use_outlook:
                outlook_handle = self.outlook_gateway.open_and_wait_ready(driver, logger)
                if not outlook_handle:
                    return

            failsafe_counter = 0
            while not command.cancellation.is_cancelled():
                try:
                    check_uis = True
                    if command.use_outlook and not active_checking_mode:
                        driver.switch_to.window(outlook_handle)
                        found_mail = self.outlook_gateway.has_unread_subject_notification(
                            driver, command.targets
                        )
                        if found_mail:
                            logger.log("🚨 MAIL detekován! Přepínám do UIS!")
                            active_checking_mode = True
                            check_uis = True
                        else:
                            check_uis = False
                            time.sleep(5)

                    if not check_uis:
                        continue

                    if command.use_outlook:
                        driver.switch_to.window(uis_handle)

                    if not self.uis_gateway.refresh_exam_table(driver):
                        failsafe_counter += 1
                        logger.log("⚠️ Stránka se nenačítá...")
                        if failsafe_counter > 3:
                            logger.log("♻️ Restartuji navigaci...")
                            self.uis_gateway.navigate_to_exams(driver)
                            failsafe_counter = 0
                        continue

                    failsafe_counter = 0
                    my_reg_subjects = self.uis_gateway.get_registered_subject_rows(driver)
                    target_action_done = False

                    for target in list(command.targets):
                        if command.cancellation.is_cancelled():
                            break
                        rows = self.uis_gateway.find_available_rows(driver, target)
                        for row in rows:
                            try:
                                if self.uis_gateway.row_matches_blacklist(row, command.blacklist):
                                    continue

                                already_have_this_subject = self.uis_gateway.has_registered_subject(
                                    my_reg_subjects, target.subject
                                )
                                if already_have_this_subject:
                                    logger.log(
                                        f"⚠️ Nalezen lepší termín pro {target.subject}! Přehlašuji..."
                                    )
                                    if not self.uis_gateway.unregister_subject(
                                        driver, target.subject, row
                                    ):
                                        logger.log(
                                            f"⚠️ Nepodařilo se odhlásit původní termín pro {target.subject}."
                                        )
                                        continue
                                    rows_new = self.uis_gateway.find_available_rows(driver, target)
                                    if not rows_new:
                                        logger.log(
                                            "⚠️ Po odhlášení termín zmizel (někdo byl rychlejší?), pokračuji..."
                                        )
                                        continue
                                    row = rows_new[0]

                                logger.log(f"🔥 VOLNO: {target.subject}! Klikám...")
                                if self.uis_gateway.register_from_row(driver, row, target):
                                    logger.log(f"🎉 ZAPSÁNO: {target.subject}")
                                    if on_target_enrolled:
                                        on_target_enrolled(target.original_line)
                                    target_action_done = True
                                    break
                            except StaleElementReferenceException:
                                continue
                            except Exception:
                                continue
                        if target_action_done:
                            break

                    if not command.use_outlook:
                        time.sleep(random.uniform(3, 8))
                except WebDriverException:
                    logger.log("❌ Prohlížeč byl zřejmě zavřen.")
                    break
                except Exception as error:
                    logger.log(f"⚠️ Chyba v cyklu: {error}")
                    time.sleep(5)
        finally:
            try:
                driver.quit()
            except Exception:
                pass


class RunUisDogUseCase:
    def __init__(self, browser_factory: BrowserFactoryPort, uis_gateway: UisGatewayPort) -> None:
        self.browser_factory = browser_factory
        self.uis_gateway = uis_gateway

    def execute(self, command: UisDogCommand, logger: LoggerPort) -> None:
        driver = self.browser_factory.create_driver()
        if not driver:
            return
        try:
            if not self.uis_gateway.login(
                driver,
                command.credentials.username,
                command.credentials.password,
                logger,
            ):
                return

            self.uis_gateway.navigate_to_exams(driver)
            for target in command.targets:
                if command.cancellation.is_cancelled():
                    break
                logger.log(f"Hledám psa pro: {target.subject}")
                while not command.cancellation.is_cancelled():
                    found_action = False
                    rows = self.uis_gateway.find_available_rows(driver, target)
                    for row in rows:
                        if self.uis_gateway.row_matches_blacklist(row, command.blacklist):
                            continue
                        try:
                            dog = row.find_element(
                                "xpath",
                                ".//a[.//span[@data-sysid='terminy-pes'] or .//use[contains(@href, 'glyph1561')]]",
                            )
                            logger.log("🐶 Klikám na psa...")
                            driver.execute_script("arguments[0].click();", dog)
                            time.sleep(2)
                            driver.back()
                            self.uis_gateway.refresh_exam_table(driver)
                            found_action = True
                            logger.log("✅ Pes nastaven.")
                            break
                        except Exception:
                            pass
                    if not found_action:
                        break
            logger.log("Hotovo.")
        finally:
            try:
                driver.quit()
            except Exception:
                pass


class ScanUisDataUseCase:
    def __init__(self, browser_factory: BrowserFactoryPort, uis_gateway: UisGatewayPort) -> None:
        self.browser_factory = browser_factory
        self.uis_gateway = uis_gateway

    def execute(
        self,
        command: UisScanCommand,
        logger: LoggerPort,
        on_study_info: Optional[Callable[[str], None]] = None,
    ) -> Optional[ScanResult]:
        driver = self.browser_factory.create_driver()
        if not driver:
            return None
        try:
            if not self.uis_gateway.login(
                driver,
                command.credentials.username,
                command.credentials.password,
                logger,
            ):
                return None
            self.uis_gateway.navigate_to_exams(driver)
            detected = self.uis_gateway.detect_study_info(driver)
            if detected and on_study_info:
                on_study_info(detected)
            return self.uis_gateway.scan_subjects(driver)
        finally:
            try:
                driver.quit()
            except Exception:
                pass


class RunTcSniperUseCase:
    def __init__(
        self,
        browser_factory: BrowserFactoryPort,
        moodle_gateway: MoodleGatewayPort,
        notifier: NotifierPort,
    ) -> None:
        self.browser_factory = browser_factory
        self.moodle_gateway = moodle_gateway
        self.notifier = notifier

    def execute(self, command: TcSniperCommand, logger: LoggerPort) -> None:
        start_time = parse_time(command.start_time)
        end_time = parse_time(command.end_time)

        logger.log("⏳ Zapínám Chrome prohlížeč (může to chvíli trvat)...")
        driver = self.browser_factory.create_driver()
        if not driver:
            return
        try:
            logger.log("🌐 Jdu na Moodle Login...")
            self.moodle_gateway.open_login(driver)
            self.moodle_gateway.fill_username_if_present(driver, command.credentials.username)
            logger.log("⏳ Čekám na tvé přihlášení...")
            if not self.moodle_gateway.wait_until_logged_in(driver, command.cancellation):
                return

            self.moodle_gateway.open_tc_page(driver, command.tc_url)
            self.moodle_gateway.expand_change_buttons(driver, logger)
            logger.log("🚀 Spouštím smyčku hledání...")

            loop_count = 0
            while not command.cancellation.is_cancelled():
                loop_count += 1
                if loop_count % 15 == 0:
                    logger.log("🔄 Stále kontroluji termíny...")
                try:
                    self.moodle_gateway.open_tc_page(driver, command.tc_url)
                    self.moodle_gateway.expand_change_buttons(driver, logger)
                    time_links = self.moodle_gateway.find_time_links(driver)
                    if time_links and self.moodle_gateway.click_matching_time_link(
                        driver,
                        time_links,
                        start_time,
                        end_time,
                        logger,
                        self.notifier,
                        command.should_book,
                    ):
                        command.cancellation.cancel()
                        break

                    day_cells = self.moodle_gateway.find_day_cells(
                        driver, command.tc_filter, loop_count, logger
                    )
                    day_clicked = self.moodle_gateway.open_first_matching_day(
                        driver, day_cells, command.days, logger
                    )
                    if day_clicked and not command.cancellation.is_cancelled():
                        logger.log("⏳ Čekám na načtení detailu...")
                        links_after_open = self.moodle_gateway.wait_for_time_links_after_day_open(
                            driver, command.cancellation
                        )
                        if links_after_open and self.moodle_gateway.click_matching_time_link(
                            driver,
                            links_after_open,
                            start_time,
                            end_time,
                            logger,
                            self.notifier,
                            command.should_book,
                        ):
                            command.cancellation.cancel()
                            break
                        if not links_after_open:
                            logger.log("⚠️ Na detailu dne nevidím žádné časy k rezervaci/změně.")
                except Exception as error:
                    logger.log(f"Chyba cyklu: {error}")

                if not command.cancellation.is_cancelled():
                    time.sleep(2.5)
        finally:
            try:
                driver.quit()
            except Exception:
                pass


class FetchEnrolledTermsUseCase:
    def __init__(
        self,
        browser_factory: BrowserFactoryPort,
        uis_gateway: UisGatewayPort,
        moodle_gateway: MoodleGatewayPort,
    ) -> None:
        self.browser_factory = browser_factory
        self.uis_gateway = uis_gateway
        self.moodle_gateway = moodle_gateway

    def execute(
        self,
        command: EnrolledTermsCommand,
        uis_logger: LoggerPort,
        tc_logger: LoggerPort,
    ) -> None:
        if not command.credentials.username or not command.credentials.password:
            uis_logger.log("⚠️ Vyplň Login a Heslo nahoře!")
            tc_logger.log("⚠️ Vyplň Login a Heslo nahoře!")
            return

        driver = self.browser_factory.create_driver()
        if not driver:
            return
        try:
            uis_logger.log("🔵 Přihlašuji do UIS...")
            if self.uis_gateway.login(
                driver,
                command.credentials.username,
                command.credentials.password,
                uis_logger,
            ):
                uis_logger.log("🧭 Hledám zapsané zkoušky...")
                for line in self.uis_gateway.fetch_enrolled_exams(driver):
                    uis_logger.log(line)
            else:
                uis_logger.log("❌ Nelze se přihlásit do UIS.")

            if not command.tc_url:
                tc_logger.log("⚠️ Není nastavena URL pro Moodle test.")
                tc_logger.log("👉 Nejdříve spusť TC Sniper a zadej URL testu/kurzu.")
                return

            tc_logger.log("🌐 Přihlašuji do Moodle...")
            self.moodle_gateway.open_login(driver)
            self.moodle_gateway.fill_username_if_present(driver, command.credentials.username)
            tc_logger.log("❗ Prosím, dokonči ručně přihlášení (MFA)... čekám.")
            self.moodle_gateway.wait_until_logged_in(driver, timeout_seconds=60)
            tc_logger.log("🚀 Načítám Moodle přehled testů...")
            self.moodle_gateway.open_tc_page(driver, command.tc_url)
            terms = self.moodle_gateway.fetch_enrolled_terms(driver)
            if not terms:
                tc_logger.log("ℹ️ Nemáš rezervované žádné termíny.")
            for datum, cas, stav in terms:
                tc_logger.log(f"📅 {datum} | 🕒 {cas}\n📌 Stav: {stav}\n" + "-" * 35)
        except Exception as error:
            uis_logger.log(f"CHYBA: {error}")
            tc_logger.log(f"CHYBA: {error}")
        finally:
            uis_logger.log("🏁 Hotovo.")
            tc_logger.log("🏁 Hotovo.")
            try:
                driver.quit()
            except Exception:
                pass

