// Allure Report 3 config. Options were checked against the installed `allure` package (see package.json).
import { defineConfig } from "allure";

const env = process.env;

// Shared by the awesome report and the dashboard.
const charts = [
  { type: "currentStatus", title: "Current status" },
  { type: "statusDynamics", title: "Status dynamics", limit: 20 },
  { type: "testingPyramid", title: "Testing pyramid", layers: ["api", "ui"] },
  {
    type: "testResultSeverities",
    title: "Results by severity",
    levels: ["blocker", "critical", "normal", "minor", "trivial"],
  },
  { type: "statusTransitions", title: "Status transitions" },
  { type: "durations", title: "Durations by layer", groupBy: "layer" },
  { type: "durationDynamics", title: "Duration dynamics" },
  { type: "stabilityDistribution", title: "Stability by feature", groupBy: "feature", threshold: 90 },
  { type: "testBaseGrowthDynamics", title: "Test base growth" },
  { type: "statusAgePyramid", title: "Status age" },
];

export default defineConfig({
  name: "Autotests",
  output: "./allure-report",
  // Fixed port for `allure open`; without it Allure picks a random port every time.
  port: env.ALLURE_PORT ?? "2026",

  // Every report generation appends one line here. Keep the file between CI runs (cache) for trends.
  historyPath: "./.allure/history.jsonl",
  historyLimit: 30,
  flakyDetection: { historyDepth: 10 },

  // Applied only to tests that don't set these labels themselves.
  defaultLabels: {
    severity: "normal",
    owner: "unassigned",
  },

  // Each failed/broken test lands in the first matching category.
  categories: {
    rules: [
      {
        name: "Known issues (tracked in the bug tracker)",
        matchers: { message: /^[A-Z]+-\d+/ },
        groupBy: ["severity"],
      },
      {
        name: "Network / stand unavailable",
        matchers: { statuses: ["broken"], trace: /ConnectError|ConnectTimeout|ReadTimeout|net::ERR_/ },
        groupByMessage: true,
      },
      {
        name: "UI timeouts and locator problems",
        matchers: { statuses: ["failed", "broken"], message: /Locator expected|Timeout \d+ms exceeded/ },
        groupBy: ["layer"],
      },
      {
        name: "Product defects (assertion failed)",
        matchers: { statuses: ["failed"] },
        groupBy: ["layer", "owner"],
        expand: true,
      },
      {
        name: "Test defects (unexpected exception)",
        matchers: { statuses: ["broken"] },
        groupBy: ["layer"],
        groupByMessage: true,
      },
      {
        name: "Flaky tests",
        matchers: { flaky: true },
        groupBy: ["owner"],
      },
    ],
  },

  // Known issues and muted failures: marked in the report, not counted by the quality gate.
  resolutions: {
    knownIssuesPath: "./.allure/known-issues.json",
    // urlTemplate must contain exactly one %s. Replace it with the project's tracker.
    links: {
      tracker: { nameTemplate: "%s", urlTemplate: "https://tracker.example.com/browse/%s" },
    },
    rules: [
      // { resolution: "issue", issue: { id: "BUG-123", type: "tracker" }, messageRegexp: "^BUG-123", comment: "..." },
      // { resolution: "muted", messageRegexp: "ConnectError", comment: "External dependency is down" },
    ],
  },

  // `allure run` and `allure quality-gate` exit with 1 when a rule is broken.
  qualityGate: {
    rules: [
      { id: "fail-fast", fastFail: true, maxFailures: 10 },
      { id: "release", maxFailures: 0, minTestsCount: 1, successRate: 0.9 },
    ],
  },

  plugins: {
    awesome: {
      options: {
        reportName: "Autotests",
        reportLanguage: "en",
        groupBy: ["epic", "feature", "story"],
        charts,
      },
    },
    dashboard: {
      options: { reportName: "Autotests dashboard", layout: charts },
    },
    // Console summary of failed tests after the run.
    log: {
      options: { groupBy: "none", filter: ({ status }) => status === "failed" || status === "broken" },
    },
    // allure-report/csv/allure-results.csv
    csv: {
      options: { fileName: "allure-results.csv" },
    },
    // allure-report/testplan/testplan.json: rerun failed tests with ALLURE_TESTPLAN_PATH=<this file>.
    testplan: {
      options: { fileName: "testplan.json", filter: ({ status }) => status === "failed" || status === "broken" },
    },
  },
});
