# Изменения для переноса на Linux + Brave

Ниже список правок, которые нужно внести в проект, чтобы приложение корректно работало в Linux и использовало браузер Brave.

## 1) Убрать Windows-only звук (`winsound`)

Файл: `uis_sniper_gui.py`

- Удалить импорт `winsound`.
- Заменить `winsound.Beep(1000, 500)` на кроссплатформенный вариант:
  - простой системный bell: `print("\a", end="", flush=True)`, или
  - через `tkinter`: `self.root.bell()`, или
  - через внешний пакет (`playsound`, `simpleaudio`) при необходимости.

Почему: `winsound` доступен только в Windows, на Linux импорт упадёт сразу при запуске.

## 2) Добавить поддержку Brave в Selenium

Файл: `uis_sniper_gui.py` (методы `init_driver` в классах `UISSniperApp`, `TCSniperApp`, `EnrolledTermsApp`)

Сейчас драйвер создаётся только как Chrome:
- `webdriver.Chrome(...)`
- `ChromeDriverManager().install()`

Что изменить:
- Добавить настройку пути к бинарнику Brave:
  - Linux путь обычно: `/usr/bin/brave-browser` (иногда `/usr/bin/brave`).
- Перед созданием драйвера указать:
  - `options.binary_location = "/usr/bin/brave-browser"` (или путь из конфига).
- Использовать менеджер драйвера с типом Brave:
  - `from webdriver_manager.core.os_manager import ChromeType`
  - `ChromeDriverManager(chrome_type=ChromeType.BRAVE).install()`

Рекомендуемо:
- вынести создание драйвера в одну общую функцию/класс, чтобы не дублировать изменения в 3 местах.

## 3) Сделать кроссплатформенный скролл в Tkinter

Файл: `uis_sniper_gui.py`

Сейчас используется только:
- `main_canvas.bind_all("<MouseWheel>", ...)`

Для Linux нужно добавить обработку:
- `"<Button-4>"` (скролл вверх),
- `"<Button-5>"` (скролл вниз).

Почему: на Linux события колеса мыши часто приходят не как `MouseWheel`, а как `Button-4/5`.

## 4) Исправить путь хранения конфигурации для Linux

Файл: `uis_sniper_gui.py` (`get_config_path`)

Сейчас конфиг сохраняется рядом с исполняемым файлом:
- `smart_sniper_config.json` в директории `sys.executable`/скрипта.

Что лучше для Linux:
- хранить в пользовательской директории, например:
  - `~/.config/smart-sniper-czu/smart_sniper_config.json`
- создать директорию, если её нет.

Почему: при установке в системный путь (например `/opt` или `/usr/local/bin`) запись рядом с бинарником может быть недоступна по правам.

## 5) Обновить README под Linux/Brave

Файл: `README.md`

Обновить пункты:
- вместо `Smart_Sniper_CZU.exe` указать запуск Linux-версии (`python3 ...` или бинарник Linux);
- заменить требование "нужен Google Chrome" на "нужен Brave";
- добавить установку Brave и зависимостей Python для Linux;
- добавить примечание про ручной логин/MFA (актуально и для Linux).

## 6) Проверить зависимости/сборку под Linux

Файлы проекта сборки (если будут добавляться): `requirements.txt`, spec-файл PyInstaller и т.д.

Нужно:
- убедиться, что версии `selenium` и `webdriver-manager` поддерживают `ChromeType.BRAVE`;
- если планируется сборка, делать Linux-сборку (а не `.exe`);
- убрать/обновить комментарии про "насильные импорты для .exe", чтобы документация соответствовала Linux.

## 7) Минимальный план внедрения (порядок)

1. Вынести единый helper `create_browser_driver(browser="brave")`.
2. Подключить его во всех трёх `init_driver`.
3. Заменить `winsound` на кроссплатформенный сигнал.
4. Добавить Linux события скролла.
5. Перенести config в `~/.config/...`.
6. Обновить `README.md`.
7. Прогнать smoke-тест:
   - запуск GUI,
   - вход в UIS,
   - вход в Moodle,
   - запуск Outlook watcher (через web Outlook в Brave).

## Где в коде сейчас привязки к Windows/Chrome

Файл `uis_sniper_gui.py`:
- импорт `winsound`;
- `winsound.Beep(...)` в `TCSniperApp._check_and_book_times`;
- все три `init_driver` создают `webdriver.Chrome(...)` через `ChromeDriverManager()`;
- скролл только через `"<MouseWheel>"`.
