# Как сгенерировать Allure-отчёт по демо-тестам

В `tests/demo/` лежат демо-тесты: на них видно, как выглядят в Allure Report 3 все статусы и
основные возможности отчёта. Им не нужны ни сеть, ни браузер, весь прогон занимает пару секунд.

Часть тестов **падает специально**, поэтому маркер `demo` исключён из обычных прогонов
(`-m "not demo"` в `addopts` в `pyproject.toml`). `make test`, `make api` и обычный `uv run pytest`
демо-тесты не запускают. Чтобы их запустить, маркер нужно указать явно: `-m demo`.

## Самый быстрый способ

```bash
make mark-open M=demo
```

Одна команда запускает демо-тесты, собирает отчёт и открывает его в браузере. Отчёт открывается,
даже если тесты упали, а они упадут: так задумано.

То же самое через `OPEN=1`:

```bash
make mark M=demo OPEN=1
```

## По шагам

Если нужно отдельно запустить тесты, собрать отчёт и открыть его:

```bash
make mark M=demo   # 1. запустить тесты: результаты пишутся в allure-results/
make report        # 2. собрать HTML-отчёт из allure-results/ в allure-report/
make open          # 3. открыть отчёт в браузере (локальный сервер, порт 2026)
```

Без `make`, теми же командами напрямую:

```bash
uv run pytest -m demo                  # 1. тесты
npx allure generate ./allure-results   # 2. отчёт
npx allure open ./allure-report        # 3. открыть
```

Дополнительные аргументы pytest передаются через `ARGS`, например параллельный запуск:

```bash
make mark-open M=demo ARGS="-n 2"
```

**Важно:** запускай демо по маркеру (`-m demo`), а не по пути. Команда
`uv run pytest tests/demo` не выполнит ни одного теста: путь не отменяет `-m "not demo"` из
`addopts`, а явный `-m` в командной строке отменяет.

## Что ожидать

15 тестов: **7 passed, 3 failed, 2 broken, 3 skipped**. Quality gate из `allurerc.mjs` падает
(`release`: ни одного падения, success rate не ниже 90%), поэтому команда завершается с ошибкой.
Для демо это нормально.

| Тест | Статус | Что показывает |
|---|---|---|
| `test_order_total_is_sum_of_items` | passed | вложенные шаги, JSON- и текстовое вложение |
| `test_discount_is_applied` (×3) | passed | параметризация: 3 отдельных теста, параметры в заголовке |
| `test_http_exchange_is_attached` | passed | HTTP-вьювер Allure 3 и curl-команда, замаскированный `Authorization` |
| `test_order_number_is_unique` | passed | параметр, исключённый из history id (`excluded=True`) |
| `test_passes_on_retry` | passed | flaky: падает с первой попытки, проходит на ретрае, вкладка **Retries** |
| `test_price_matches_catalog` | failed | упавший `assert`: ожидаемое и фактическое значение |
| `test_known_issue` | failed | сообщение с номером тикета, категория **Known issues**, ссылка issue |
| `test_strict_xpass` | failed | `XPASS(strict)`: баг починили, а пометка xfail осталась |
| `test_broken_by_test_code` | broken | исключение в коде теста (`KeyError`) |
| `test_broken_in_setup` | broken | падение фикстуры в setup, категория **Network / stand unavailable** |
| `test_skipped` | skipped | пропуск маркером `skip` с причиной |
| `test_skipped_at_runtime` | skipped | пропуск изнутри теста (`pytest.skip`) |
| `test_expected_failure` | skipped | `xfail`: известный баг, тест упал, как и ожидалось |

Падающая фикстура для `test_broken_in_setup` лежит в `tests/demo/conftest.py`.

## Что посмотреть в отчёте

После `make open` открывается `allure-report/index.html` со ссылками на отчёты плагинов. Основной
отчёт — **awesome**.

- **Дерево тестов:** Demo → Passed / Flaky / Failed / Broken / Skipped (epic → feature → story).
  Фильтры по статусу и поиск находятся над деревом.
- **Карточка теста:** заголовок, severity, шаги, вложения, ссылки (issue), параметры, описание
  (берётся из docstring теста).
- **Вложения:** открой `POST /api/v1/orders → 201` в `test_http_exchange_is_attached`, там
  просмотрщик запроса и ответа. Рядом вложение `curl` с готовой командой.
- **Retries:** у `test_passes_on_retry` видна первая, упавшая попытка.
- **Categories:** падения разложены по категориям из `allurerc.mjs`: Known issues, Network / stand
  unavailable, Product defects, Test defects.
- **Quality gate:** какие правила нарушены и почему.
- **Environment:** стенд, base URL, версии Python, ОС, pytest и httpx.
- **Графики:** статусы, severity, длительности. История и тренды (Status dynamics, Test base
  growth и другие) появляются после нескольких запусков: каждая сборка отчёта дописывает строку в
  `.allure/history.jsonl`.
- **dashboard:** отдельная страница с одними графиками.

## Краткая сводка без браузера

```bash
make run-summary
```

Пишет `docs/run-summary.md`: итоги, упавшие тесты, группы одинаковых ошибок.

## Уборка

```bash
make clean          # очистить allure-results/, allure-report/, test-results/
make clean FULL=1   # удалить эти папки целиком
rm -rf .allure      # стереть историю прогонов (тренды начнутся заново)
```
