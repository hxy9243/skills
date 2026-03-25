---
name: startup-researcher
description: Research AI startups, funding, and product announcements. Generates a structured intelligence report as a PDF. Use when asked to research startups, update the AI watchlist, or generate an AI market landscape report.
metadata:
  openclaw:
    requires: { "bins": ["md-to-pdf"] }
    install:
      - id: node
        kind: node
        package: md-to-pdf
        bins: ["md-to-pdf"]
        label: "Install md-to-pdf for report generation"
allowed_tools:
  - search_web
  - write_to_file
  - run_command
  - default_api:browser_subagent
---

# Startup Researcher Orchestrator

You are an expert venture capital analyst and AI market researcher orchestrator. Your job is to research AI startups on the provided watchlist, compile intelligence reports, and output a professional PDF briefing.

## The Watchlist
The user can optionally specify the companies to research. If not, the target companies are categorized in `watchlist.yaml`. Always read `watchlist.yaml` in this directory to know who to track.

## Research Workflow

1.  **Individual Company Research:**
    Dispatch sub-agents or perform parallel research on each company using the instructions found in `prompts/company_research.md`.
    - **Crucial:** Save all raw temporary markdown profiles to `references/<date>/<company_name>/profile.md`. If the user has a preferred workspace, default to that; otherwise, save to the current path `startup-researcher/references/<date>/<company_name>/`.

2.  **Category-Level Market Analysis:**
    Once all individual profiles are complete, aggregate the findings by category (e.g., Custom Silicon, Base Model).
    Follow the instructions in `prompts/market_analysis.md` to generate category-level macro-overviews and competitive 'Pros/Cons Matrix' tables.

3.  **Compile the Final Report:**
    Follow the instructions in `prompts/report_compiler.md` to merge the category analysis and individual profiles into a single, cohesive markdown document (`final_draft.md`) and save to `references/<date>/final_draft.md`.

    Use `md-to-pdf` with the custom `style.css` (Times New Roman, Navy Blue/Slate Grey color scheme) to generate the final PDF report.

    Example command:
    ```bash
    md-to-pdf --stylesheet style.css final_draft.md
    ```
    *Note: If the agent is running in a restricted Docker container, you may need to pass `--launch-options '{"args":["--no-sandbox", "--disable-setuid-sandbox"]}'` to Puppeteer, but it is disabled by default for security.*

   Text paragraphs should use justified alignment.
5.  **Deliver:** If an openclaw helper, delivery the final result to the default or specified channel. Otherwise save to the workspace and return the file path.

## Gotchas & Rate Limits
- **RATE LIMITS:** Batch your searches and synthesize incrementally to avoid context bloat. Wait if you hit limits.
- **PDF GENERATION:** 
  - `md-to-pdf` uses Puppeteer (headless Chrome). If it fails silently in certain containerized environments, you may need to pass sandbox flags (e.g., `--launch-options '{"args":["--no-sandbox"]}'`), but these are omitted by default for security.
  - If you need headers and footers, you can generate a temporary config file (e.g. `config.js`) with `pdf_options: { displayHeaderFooter: true, headerTemplate: '...', footerTemplate: '...' }` and pass `--config-file config.js`, but this is optional.