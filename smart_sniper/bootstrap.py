from dataclasses import dataclass

from smart_sniper.application.use_cases import (
    FetchEnrolledTermsUseCase,
    RunTcSniperUseCase,
    RunUisDogUseCase,
    RunUisSniperUseCase,
    ScanUisDataUseCase,
)
from smart_sniper.infrastructure.browser_factory import SeleniumBrowserFactory
from smart_sniper.infrastructure.config_store import JsonConfigStore
from smart_sniper.infrastructure.gateways.moodle_gateway import SeleniumMoodleGateway
from smart_sniper.infrastructure.gateways.outlook_gateway import SeleniumOutlookGateway
from smart_sniper.infrastructure.gateways.uis_gateway import SeleniumUisGateway
from smart_sniper.infrastructure.notifier import SystemNotifier


@dataclass
class AppContainer:
    config_store: JsonConfigStore
    run_uis_sniper: RunUisSniperUseCase
    run_uis_dog: RunUisDogUseCase
    scan_uis_data: ScanUisDataUseCase
    run_tc_sniper: RunTcSniperUseCase
    fetch_enrolled_terms: FetchEnrolledTermsUseCase


def build_container(root=None) -> AppContainer:
    browser_factory = SeleniumBrowserFactory(use_brave=True)
    config_store = JsonConfigStore()
    uis_gateway = SeleniumUisGateway()
    outlook_gateway = SeleniumOutlookGateway()
    moodle_gateway = SeleniumMoodleGateway()
    notifier = SystemNotifier(root=root)
    return AppContainer(
        config_store=config_store,
        run_uis_sniper=RunUisSniperUseCase(browser_factory, uis_gateway, outlook_gateway),
        run_uis_dog=RunUisDogUseCase(browser_factory, uis_gateway),
        scan_uis_data=ScanUisDataUseCase(browser_factory, uis_gateway),
        run_tc_sniper=RunTcSniperUseCase(browser_factory, moodle_gateway, notifier),
        fetch_enrolled_terms=FetchEnrolledTermsUseCase(
            browser_factory, uis_gateway, moodle_gateway
        ),
    )

