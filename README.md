# Smart Sniper CZU

Smart Sniper объединяет:
- UIS Sniper (поиск и запись на экзамены),
- TC Sniper (резервации в Moodle),
- Enrolled Terms (сводка записанных терминов UIS/Moodle).

## Архитектура

Проект реорганизован в onion-слои:
- `smart_sniper/domain` — сущности и чистые правила,
- `smart_sniper/application` — use-cases и порты,
- `smart_sniper/infrastructure` — Selenium/конфиг/нотификации,
- `smart_sniper/presentation` — Tkinter UI.

Точка входа: `main.py` (также можно запускать `uis_sniper_gui.py`).

## Требования (Linux)

- Python 3.10+
- Brave Browser (по умолчанию используется Selenium через Brave)
- Tkinter (`python3-tk`)
- Пакеты Python:
  - `selenium`
  - `webdriver-manager`

## Запуск

```bash
python3 main.py
```

## CI/CD

- Workflow: `.github/workflows/ci-cd.yml`
- В CI выполняются:
  - установка зависимостей,
  - `pytest -q`,
  - `python -m compileall .`
- В CD собирается Debian-пакет через `scripts/build_deb.sh`.
- На теге формата `v*` workflow публикует `.deb` в GitHub Release.

Локальная сборка `.deb`:

```bash
bash scripts/build_deb.sh 0.1.0
```

## Поведение и данные

- Логика UI сохранена: те же окна, поля и сценарии запуска.
- Конфиг сохраняется в Linux: `~/.config/smart-sniper-czu/smart_sniper_config.json`.
- Для Outlook/Moodle вход часто завершается вручную (MFA/SAML/OAuth).

## Важно

- Не закрывай окно браузера во время активного снайпера.
- Использование на свой риск.
