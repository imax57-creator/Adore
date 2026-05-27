# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run the application:**
```
python main.py
```

**Run the full test suite:**
```
python run_all_tests.py
```
Reports are saved to `tests/tests_report_TIMESTAMP.md`.

**Run a single test module** (each exposes `run_all_checks() -> (bool, list[str])`):
```
python tests/test_data_integrity.py
python tests/test_algorithm_stability.py
```

## Architecture

### Controller pattern

`MainApp` (`app/main_app.py`) is the central controller and the only `ctk.CTk` window. All 5 views are instantiated once at startup and stacked in a `frames` dict — navigation is done via `show_frame(page_name)`. Views call `self.controller.*` for navigation, shared data, and the active `user_profile`.

**View stack:** `WelcomeView` → `NameView` → `QuizView` → `ResultsView` → (optional) `ExplorerView`

### Data flow

`MainApp.user_profile` (dict) accumulates state across the session:
- `QuizView` writes answers into `controller.user_profile["answers"]`
- `ResultsView` calls `calculate_recommendations()` and writes results back into `user_profile`
- `report_generator.generate_html_report()` reads the completed `user_profile` to render the Jinja2 HTML report

### DataManager (`app/data_manager.py`)

Loads all JSON files at startup and pre-processes jobs for scoring:
- Builds `_search_blob` / `_search_terms_list` per job (TF-IDF input)
- Computes `idf` map and `tag_profile_freq` via Monte-Carlo simulation
- Builds navigation indexes (`_sector_to_jobs`, `_interest_to_jobs`, `_theme_to_jobs`, `_education_level_to_jobs`)

**Always resolve ROME codes through `DataManager.get_job_by_code()`**, which applies `rome_alias_map`. Never access `_jobs_map` directly with a raw code.

### Scoring algorithm (`app/logic/questionnaire_logic.py`)

Two entry points:
- `calculate_recommendations()` — for the `jeune` quiz
- `calculate_reconversion_recommendations()` — for the `adulte` quiz; adds a transferability bonus when the user's past sector matches a job's sectors

Both use weighted TF-IDF, background noise subtraction, and a popularity bias penalty. Weights are loaded from `config/scoring.json` (not hardcoded).

### Threading rules

Both the popularity bias calculation (startup background thread) and the recommendation scoring (`ResultsView._calculate_recommendations_thread`) run off the main thread. **All GUI updates from these threads must go through `self.after(0, callback)`** — never touch tkinter widgets directly from a background thread.

### Data files (`data/` and `config/`)

| File | Purpose |
|---|---|
| `jobs_rome_enriched.json` | Master job objects (ROME v4.60, enriched) |
| `questions_jeune_v2.json` / `questions_adulte.json` | Question banks with tagged answer options |
| `tags_master.json` + `semantic_map.json` | Tag taxonomy and term expansion for scoring |
| `rome_alias_map.json` | Maps any ROME code → canonical master code |
| `navigation_*.json` | Pre-built navigation trees (sectors, interests, themes, hierarchy) |
| `popularity_bias.json` | **Auto-generated cache** — delete to force recalculation |
| `config/scoring.json` | Scoring weights (`tag_category_weights`, `popularity_bias_factor`, reconversion weights) |

`RefRomeJson/` contains the raw ROME v4.60 source files used by the `scripts/data_cleaning/` pipeline to build the enriched data files.

### UI theming

All colors, font definitions, and padding constants are centralized in `app/ui_theme.py`. Font objects must be created with `CTkFont(**ui_theme.FONT_DEFINITIONS["key"])` — never instantiate fonts outside a widget constructor (CTk limitation).

Mode-specific UI strings (jeune vs adulte) come from `data/texts.json` via `TextProvider.get_text(key, mode)`.
