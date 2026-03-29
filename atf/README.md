# ATF — AI Test Framework

An AI-powered test automation framework that takes a web application or BRD as input and generates manual scenarios, test cases, and Playwright (Python) automation scripts — with human review gates at every stage and git commit/push per scenario.

---

## Framework Structure

```
atf/
├── config/settings.yaml          # All config — models, git, browser, paths
├── prompts/                      # Claude prompt templates (stateless, schema-enforced)
│   ├── analyzer.md
│   ├── scenario_gen.md
│   ├── testcase_author.md
│   ├── automation_gen.md
│   └── healer.md
├── core/                         # Pipeline stages
│   ├── claude_runner.py          # Claude CLI subprocess (no API key)
│   ├── analyzer.py               # Stage 1 — BRD/URL → app_summary.json
│   ├── scenario_generator.py     # Stage 2 — app_summary → scenarios
│   ├── testcase_author.py        # Stage 3 — scenario → test case
│   ├── automation_generator.py   # Stage 4 — test case → Playwright script + locators
│   └── git_manager.py            # Commit + push per scenario
├── locators/                     # YAML per page (auto-created, version-tracked)
│   └── _registry.yaml            # Master index of all pages
├── pages/
│   └── base_page.py              # POM base — loads locators from YAML, hints healer
├── utils/
│   ├── human_loop.py             # 4 interactive gates (Approve/Edit/Regenerate/Skip)
│   ├── locator_store.py          # CRUD for locator YAML files
│   ├── file_utils.py
│   └── logger.py                 # Rich-colored console output
├── output/                       # All generated artifacts (committed to git)
│   ├── app_summary.json
│   ├── scenarios/
│   ├── testcases/
│   └── tests/
├── reports/
│   └── healing_log.json          # Healer audit trail
├── healer.py                     # Standalone CLI — user calls explicitly
├── runner.py                     # Main orchestrator
├── conftest.py                   # Pytest fixtures
└── pytest.ini
```

---

## Pipeline

```
Input (BRD / URL)
      │
      ▼
 Stage 1: Analyze          →  output/app_summary.json
      │
  ◆ Human Gate 1 ◆         →  Approve / Edit / Regenerate
      │
      ▼
 Stage 2: Scenario Gen     →  output/scenarios/sc-NNN.json  (all scenarios)
      │
  ◆ Human Gate 2 ◆         →  Approve / Edit / Delete / Regenerate
      │
      ▼  (loop per scenario)
 Stage 3: Test Case Auth   →  output/testcases/tc-NNN.json
      │
  ◆ Human Gate 3 ◆         →  Approve / Edit / Regenerate / Skip
      │
      ▼
 Stage 4: Automation Gen   →  output/tests/test_tc_NNN.py
                           →  locators/<page>.yaml
      │
  ◆ Human Gate 4 ◆         →  Approve / Edit / Regenerate / Skip
      │
      ▼
 Git commit + push         →  feat(sc-NNN): <scenario name>
      │
 Next scenario ────────────┘
```

---

## Setup

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Install Playwright browser
playwright install chromium

# 3. Ensure the claude CLI binary is on your PATH
which claude

# 4. Initialise a git repo (if not already done)
git init
git remote add origin <your-remote-url>

# 5. Set your base URL in config/settings.yaml
#    playwright.base_url: "https://yourapp.com"
```

---

## How to Use

### Run the full pipeline

```bash
# From a BRD file
python runner.py --brd docs/requirements.txt

# From a live URL
python runner.py --url https://yourapp.com

# Both BRD and URL
python runner.py --brd docs/brd.txt --url https://yourapp.com

# Override base URL for generated tests
python runner.py --url https://yourapp.com --base-url https://yourapp.com
```

### Resume after analysis (skip re-crawling)

```bash
python runner.py --resume
```

### CI mode — skip all human gates

```bash
python runner.py --brd docs/brd.txt --no-human
```

### Run generated Playwright tests

```bash
# All tests
pytest output/tests/

# With HTML report
pytest output/tests/ --html=reports/test_report.html

# By marker
pytest output/tests/ -m smoke
pytest output/tests/ -m regression
pytest output/tests/ -m negative
```

---

## Healer — Explicit Locator Repair

The healer is a **standalone CLI tool** called by the user when element locators break after UI changes. It is not part of the generation or test execution workflow.

```bash
# Scan a page and report all broken locators (no changes made)
python healer.py --scan --url https://yourapp.com/login

# Heal all locators on a page
python healer.py --page login_page --url https://yourapp.com/login

# Heal a single element
python healer.py --page login_page --element email_input --url https://yourapp.com/login
```

**Healing flow:**
1. Checks if the primary locator still resolves on the page
2. Tries existing fallback locators in order
3. If all fail — sends DOM snapshot to Claude to find a new locator
4. Verifies Claude's suggestion on the live page
5. Updates `locators/<page>.yaml` (bumps version, records heal timestamp)
6. Commits the healed locator file: `heal(locator): <page>.<element>`
7. Logs the change to `reports/healing_log.json`

---

## Locator Files

Each page has a YAML file under `locators/`. Example:

```yaml
# locators/login_page.yaml
page: login_page
url_pattern: /login
version: 1
last_healed: null
locators:
  email_input:
    primary:   "[data-testid='email']"
    fallback:  ["#email", "input[type='email']"]
    strategy:  css
    healed:    false

  submit_button:
    primary:   "[data-testid='login-btn']"
    fallback:  ["button[type='submit']"]
    strategy:  css
    healed:    false
```

Page objects load locators from these files at runtime — no selectors are hardcoded in test code.

---

## Git Commit Strategy

One commit per scenario, after human approval:

```
feat(atf)(sc-001): User login - happy path
  output/scenarios/sc-001.json
  output/testcases/tc-001.json
  output/tests/test_tc_001.py
  locators/login_page.yaml

heal(locator): login_page.submit_button
  locators/login_page.yaml
```

---

## Configuration

All settings live in `config/settings.yaml`:

| Section | Key | Description |
|---------|-----|-------------|
| `claude.models` | per stage | Model used for each pipeline stage |
| `claude.max_tokens` | per stage | Token ceiling per Claude call |
| `claude.cli_binary` | `claude` | Name of the Claude CLI binary on PATH |
| `git.remote` | `origin` | Git remote name |
| `git.branch` | `main` | Branch to push to |
| `git.auto_push` | `true` | Push after every commit |
| `playwright.browser` | `chromium` | Browser for tests and crawling |
| `playwright.headless` | `false` | Run browser visibly or headless |
| `playwright.base_url` | `""` | Base URL injected into generated tests |
| `human_loop.enabled` | `true` | Set `false` for CI mode |

---

## Token Optimization

| Strategy | Detail |
|----------|--------|
| One call per stage | Scenarios processed individually, never batched |
| Compress early | BRD/URL → `app_summary.json` once; only the summary passed downstream |
| Model tiering | Haiku for analysis/parsing · Sonnet for reasoning and code generation |
| Stateless prompts | No conversation history between calls — inject only required context |
| Schema-enforced output | JSON schema in every prompt eliminates re-prompting |
| DOM cap in healer | DOM snapshot capped at 8000 chars before sending to Claude |
