"""Build docs/run-summary.md from raw Allure results of the last run.

Usage (from the project root):
    uv run python scripts/make_run_summary.py [--results-dir allure-results] [--output docs/run-summary.md]
        [--command "..."] [--scope "..."] [--env "..."]

Only *-result.json files are read. Exit code is 0 when the summary is written (whatever the test
statuses are) and 2 when there are no results to summarize.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean

STATUSES = ("passed", "failed", "broken", "skipped", "unknown")
SEVERITY_ORDER = ("blocker", "critical", "normal", "minor", "trivial")
NO_SEVERITY = "не задана"
NO_VALUE = "—"
MESSAGE_LIMIT = 300
# Results of one run start close to each other; a bigger gap means files from several runs.
RUN_GAP_MS = 10 * 60 * 1000
SAME_DURATION_TOLERANCE = 0.05
SAME_DURATION_MIN_TESTS = 3

SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*[:=]\s*)(?:bearer\s+|basic\s+)?\S+"),
    re.compile(r"(?i)(bearer\s+)[\w\-.~+/]+=*"),
    re.compile(
        r"(?i)((?:password|passwd|pwd|token|api[_-]?key|secret|access[_-]?key|client[_-]?secret)"
        r"['\"]?\s*[:=]\s*['\"]?)[^\s'\",;&]+"
    ),
)
UUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
HEX_RE = re.compile(r"\b(?:0x)?[0-9a-fA-F]{16,}\b")
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
# "path/file.py:42" (pytest location) or "('path/file.py', 42, ...)" (allure-pytest skip trace).
LOCATION_RES = (
    re.compile(r"""(?P<path>[^\s'"():]+(?: [^\s'"():]+)*\.py):(?P<line>\d+)"""),
    re.compile(r"""\('(?P<path>[^']+\.py)', (?P<line>\d+),"""),
)
SKIP_PREFIX = "Skipped: "


@dataclass(frozen=True)
class TestResult:
    name: str
    full_name: str
    status: str
    message: str
    trace: str
    severity: str
    module: str
    start: int | None
    stop: int | None
    history_id: str
    path: Path
    retries: int = 0

    @property
    def title(self) -> str:
        short_name = self.full_name.rsplit("#", 1)[-1]
        if not self.full_name:
            return self.name
        return self.full_name if self.name in ("", short_name) else f"{self.full_name} — {self.name}"

    @property
    def duration_ms(self) -> int | None:
        if self.start is None or self.stop is None:
            return None
        return self.stop - self.start


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize the last Allure run into a Markdown file.")
    parser.add_argument("--results-dir", type=Path, default=Path("allure-results"))
    parser.add_argument("--output", type=Path, default=Path("docs/run-summary.md"))
    parser.add_argument("--command", help="command that started the run, shown in the header")
    parser.add_argument("--scope", help="what the run covered, shown in the header")
    parser.add_argument("--env", help="environment / stand, shown in the header")
    return parser.parse_args(argv)


def mask_secrets(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(lambda match: f"{match.group(1)}***", text)
    return text


def label_values(raw: dict[str, object]) -> dict[str, str]:
    """First value of every label; Allure allows repeated labels (tags), only singular ones are used."""
    values: dict[str, str] = {}
    labels = raw.get("labels")
    if not isinstance(labels, list):
        return values
    for label in labels:
        if isinstance(label, dict) and isinstance(label.get("name"), str):
            values.setdefault(label["name"], str(label.get("value", "")))
    return values


def as_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def parse_result(path: Path) -> TestResult:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("top-level JSON is not an object")
    status = raw.get("status")
    if not isinstance(status, str):
        raise ValueError("no 'status' field")
    details = raw.get("statusDetails")
    details = details if isinstance(details, dict) else {}
    labels = label_values(raw)
    full_name = str(raw.get("fullName") or "")
    name = str(raw.get("name") or "")
    return TestResult(
        name=name,
        full_name=full_name,
        status=status if status in STATUSES else "unknown",
        message=str(details.get("message") or ""),
        trace=str(details.get("trace") or ""),
        severity=labels.get("severity", "").lower() or NO_SEVERITY,
        module=labels.get("package") or labels.get("parentSuite") or NO_VALUE,
        start=as_int(raw.get("start")),
        stop=as_int(raw.get("stop")),
        history_id=str(raw.get("historyId") or f"{full_name}::{name}"),
        path=path,
    )


def load_results(results_dir: Path) -> tuple[list[TestResult], list[tuple[Path, str]]]:
    results: list[TestResult] = []
    unreadable: list[tuple[Path, str]] = []
    for path in sorted(results_dir.glob("*-result.json")):
        try:
            results.append(parse_result(path))
        except (OSError, UnicodeDecodeError, ValueError) as error:
            unreadable.append((path, f"{type(error).__name__}: {error}"))
    return results, unreadable


def pick_latest(results: list[TestResult]) -> list[TestResult]:
    """Keep the last attempt (by start) of every test; earlier attempts are counted as retries."""
    attempts: dict[str, list[TestResult]] = defaultdict(list)
    for result in results:
        attempts[result.history_id].append(result)
    latest: list[TestResult] = []
    for group in attempts.values():
        last = max(group, key=lambda result: result.start or 0)
        latest.append(TestResult(**{**last.__dict__, "retries": len(group) - 1}))
    return latest


def first_line(text: str) -> tuple[str, int]:
    """First non-empty line and the number of other non-empty lines."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "", 0
    return lines[0], len(lines) - 1


def error_line(result: TestResult) -> tuple[str, int]:
    if result.message.strip():
        return first_line(result.message)
    error_lines = [line for line in result.trace.splitlines() if line.startswith("E ")]
    return first_line("\n".join(line[1:] for line in error_lines))


def short_message(result: TestResult) -> str:
    line, extra_lines = error_line(result)
    if not line:
        return NO_VALUE
    line = mask_secrets(line)
    if len(line) > MESSAGE_LIMIT:
        line = line[: MESSAGE_LIMIT - 1] + "…"
    return f"{line} (+{extra_lines} строк)" if extra_lines else line


def failure_location(result: TestResult, root: Path) -> str:
    for text in (result.trace, result.message):
        for pattern in LOCATION_RES:
            match = pattern.search(text)
            if match:
                path = Path(match["path"])
                if path.is_absolute() and path.is_relative_to(root):
                    path = path.relative_to(root)
                return mask_secrets(f"{path}:{match['line']}")
    return NO_VALUE


def group_key(result: TestResult) -> str:
    line, _ = error_line(result)
    if not line:
        return "(нет сообщения)"
    line = UUID_RE.sub("<uuid>", mask_secrets(line))
    line = HEX_RE.sub("<hex>", line)
    return NUMBER_RE.sub("<n>", line)


def skip_reason(result: TestResult) -> str:
    line, _ = first_line(result.message)
    return mask_secrets(line.removeprefix(SKIP_PREFIX)) or "(причина не указана)"


def run_groups(results: list[TestResult]) -> list[tuple[int, int]]:
    """Split start times into groups separated by gaps longer than RUN_GAP_MS."""
    starts = sorted(result.start for result in results if result.start is not None)
    if not starts:
        return []
    groups = [(starts[0], starts[0])]
    for start in starts[1:]:
        group_start, group_end = groups[-1]
        if start - group_end > RUN_GAP_MS:
            groups.append((start, start))
        else:
            groups[-1] = (group_start, start)
    return groups


def format_time(epoch_ms: int | None) -> str:
    if epoch_ms is None:
        return NO_VALUE
    return datetime.fromtimestamp(epoch_ms / 1000).astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def format_duration(duration_ms: int | None) -> str:
    if duration_ms is None:
        return NO_VALUE
    seconds = duration_ms / 1000
    if seconds < 60:
        return f"{seconds:.2f} с"
    minutes, seconds = divmod(seconds, 60)
    return f"{int(minutes)} мин {seconds:.0f} с"


def cell(text: str) -> str:
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def severity_rank(severity: str) -> int:
    return SEVERITY_ORDER.index(severity) if severity in SEVERITY_ORDER else len(SEVERITY_ORDER)


def status_table(header: str, rows: dict[str, Counter[str]]) -> list[str]:
    lines = [
        f"| {header} | " + " | ".join(STATUSES) + " | всего | доля passed |",
        "|---" * (len(STATUSES) + 3) + "|",
    ]
    for row_name, counts in rows.items():
        total = sum(counts.values())
        share = f"{counts['passed'] / total:.1%}" if total else NO_VALUE
        values = " | ".join(str(counts[status]) for status in STATUSES)
        lines.append(f"| {cell(row_name)} | {values} | {total} | {share} |")
    return lines


def observations(
    problems: list[TestResult], error_groups: list[list[TestResult]], retried: list[TestResult]
) -> list[str]:
    facts: list[str] = []
    if error_groups and len(error_groups[0]) >= 2:
        largest = error_groups[0]
        facts.append(
            f"{len(largest)} из {len(problems)} failed + broken тестов имеют одинаковое сообщение: "
            f"`{short_message(largest[0])}`."
        )
    durations = [d for d in (result.duration_ms for result in problems) if d is not None]
    if len(durations) >= SAME_DURATION_MIN_TESTS:
        average = mean(durations)
        close = [d for d in durations if abs(d - average) <= average * SAME_DURATION_TOLERANCE]
        if len(close) >= SAME_DURATION_MIN_TESTS:
            facts.append(
                f"У {len(close)} из {len(problems)} failed + broken тестов длительность отличается не более "
                f"чем на {SAME_DURATION_TOLERANCE:.0%} от средней ({format_duration(round(average))}): "
                "возможен общий таймаут."
            )
    if retried:
        names = ", ".join(f"{result.title} ({result.retries}, итог {result.status})" for result in retried)
        facts.append(f"У {len(retried)} тестов были ретраи, в сводке учтена последняя попытка: {names}.")
    return facts


def render(
    args: argparse.Namespace,
    results: list[TestResult],
    unreadable: list[tuple[Path, str]],
    raw_count: int,
) -> str:
    root = Path.cwd()
    starts = [result.start for result in results if result.start is not None]
    stops = [result.stop for result in results if result.stop is not None]
    first_start = min(starts) if starts else None
    last_stop = max(stops) if stops else None
    window = last_stop - first_start if first_start is not None and last_stop is not None else None

    warnings: list[str] = []
    groups = run_groups(results)
    if len(groups) > 1:
        bounds = "; ".join(f"{format_time(start)} … {format_time(end)}" for start, end in groups)
        warnings.append(
            f"Результаты похожи на смесь {len(groups)} прогонов (разрыв по start больше "
            f"{RUN_GAP_MS // 60000} мин): {bounds}. Ничего не отфильтровано."
        )
    if unreadable:
        warnings.append(f"Не удалось прочитать файлов: {len(unreadable)} (см. последний раздел).")

    out = ["# Сводка прогона", ""]
    out.append(f"- Сформировано: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z')}")
    out.append(f"- Директория результатов: `{args.results_dir}`")
    out.append(
        f"- Окно прогона: {format_time(first_start)} … {format_time(last_stop)} ({format_duration(window)})"
    )
    out.append(f"- Файлов *-result.json: {raw_count}, тестов после учёта ретраев: {len(results)}")
    for label, value in (("Команда", args.command), ("Область", args.scope), ("Окружение", args.env)):
        if value:
            out.append(f"- {label}: `{mask_secrets(value)}`")
    for warning in warnings:
        out.append(f"- **Предупреждение:** {warning}")

    out += ["", "## Итоги", ""]
    out += status_table("", {"Всего": Counter(result.status for result in results)})

    modules: dict[str, Counter[str]] = defaultdict(Counter)
    for result in results:
        modules[result.module][result.status] += 1
    out += ["", "## Сводка по модулям", ""]
    out += status_table("Модуль", dict(sorted(modules.items())))

    problems = sorted(
        (result for result in results if result.status in ("failed", "broken")),
        key=lambda result: (severity_rank(result.severity), result.title),
    )
    out += ["", "## Упавшие и сломанные тесты", ""]
    locations = {result.path: failure_location(result, root) for result in problems}
    # With --tb=line allure-pytest keeps only "E" lines, so the column is usually empty and is dropped.
    show_location = any(location != NO_VALUE for location in locations.values())
    if problems:
        headers = ["Тест", "Severity", "Статус", "Сообщение", "Длительность", "Ретраи", "Файл"]
        if show_location:
            headers.insert(4, "Не пройденная/Проваленная проверка")
        out.append("| " + " | ".join(headers) + " |")
        out.append("|---" * len(headers) + "|")
        for result in problems:
            row = [
                cell(result.title),
                result.severity,
                result.status,
                cell(short_message(result)),
                format_duration(result.duration_ms),
                str(result.retries),
                f"`{result.path.name}`",
            ]
            if show_location:
                row.insert(4, cell(locations[result.path]))
            out.append("| " + " | ".join(row) + " |")
    else:
        out.append("Нет.")

    by_error: dict[str, list[TestResult]] = defaultdict(list)
    for result in problems:
        by_error[group_key(result)].append(result)
    error_groups = sorted(by_error.values(), key=lambda group: (-len(group), group_key(group[0])))
    out += ["", "## Группы одинаковых ошибок", ""]
    if error_groups:
        for number, group in enumerate(error_groups, start=1):
            out.append(f"### {number}. {len(group)} тест(ов): `{cell(group_key(group[0]))}`")
            out.append("")
            out.append(f"Пример: `{cell(short_message(group[0]))}`")
            out.append("")
            out += [f"- {result.title}" for result in group]
            out.append("")
        out.pop()
    else:
        out.append("Нет.")

    facts = observations(problems, error_groups, [result for result in results if result.retries])
    if facts:
        out += ["", "## Наблюдения", ""]
        out += [f"- {fact}" for fact in facts]

    skipped = [result for result in results if result.status == "skipped"]
    out += ["", f"## Пропущенные тесты (skipped): {len(skipped)}", ""]
    if skipped:
        by_reason: dict[str, list[TestResult]] = defaultdict(list)
        for result in skipped:
            by_reason[skip_reason(result)].append(result)
        for reason, group in sorted(by_reason.items(), key=lambda item: (-len(item[1]), item[0])):
            out.append(f"- **{reason}** ({len(group)}):")
            out += [f"  - {result.title}" for result in sorted(group, key=lambda result: result.title)]
    else:
        out.append("Нет.")

    if unreadable:
        out += ["", "## Не удалось прочитать", ""]
        out += [f"- `{path.name}`: {mask_secrets(error)}" for path, error in unreadable]

    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    results_dir: Path = args.results_dir
    if not results_dir.is_dir():
        print(f"Results directory not found: {results_dir}. Run the tests first.", file=sys.stderr)
        return 2
    results, unreadable = load_results(results_dir)
    if not results and not unreadable:
        print(f"No *-result.json files in {results_dir}. Run the tests first.", file=sys.stderr)
        return 2

    summary = render(args, pick_latest(results), unreadable, raw_count=len(results) + len(unreadable))
    output: Path = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(summary, encoding="utf-8")
    print(f"Summary written to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
