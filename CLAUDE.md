# Tudor Watch Finder

## Project Overview
A Python tool to find Tudor watches at nearby US retailers. It scrapes Tudor's official retailer list, filters by distance from a zip code, and uses Bland AI to make automated phone calls to check inventory. It also uses Claude (Anthropic API) to summarize call transcripts.

## Architecture
- `config.py` — Watch definitions (WATCHES dict), search defaults, Bland AI config, call scripts
- `scraper.py` — Scrapes tudorwatch.com for US retailer listings. Key class: `TudorScraper`, data class: `Retailer`
- `filter.py` — Geocodes zip codes and filters retailers by distance. Key classes: `RetailerFilter`, `ZipCodeGeocoder`, `DistanceCalculator`
- `phone_caller.py` — Makes automated calls via Bland AI. Key classes: `BlandAICaller`, `InventoryChecker`. Enum: `InventoryStatus`
- `summarizer.py` — Summarizes call transcripts via Anthropic API (Claude Haiku)
- `website_scraper.py` — Checks retailer websites for stock (supplementary to phone calls)
- `api.py` — FastAPI web server with REST API and static HTML frontend
- `main.py` — CLI entry point
- `static/index.html` — Single-page web frontend (vanilla HTML/JS/CSS, no build step)

## How to Add a New Watch
1. Add the watch to the `WATCHES` dict in `config.py` with keys: `model`, `reference`, `case_size`, `case_material`, `dial`, `price`, `full_name`, `image`
2. Add a corresponding watch image to `static/` and reference it in the `image` field
3. The frontend (`static/index.html`) dynamically loads watches from `/api/watches`, so no frontend changes needed for basic additions
4. The phone caller reads from the watch config to build its call script, so calls will automatically use the correct watch details

## Code Style & Conventions
- Python 3.8+ with type hints
- Dataclasses for data models (`Retailer`, `CallResult`, `ZipCodeLocation`)
- Enums for statuses (`InventoryStatus`)
- No ORM — data is in-memory or JSON files
- FastAPI for the web layer, Pydantic for request validation
- Use `requests` for HTTP, `beautifulsoup4` for HTML parsing
- Keep imports at the top of files, group by stdlib / third-party / local

## Testing
- Run tests: `pytest tests/ -v`
- Tests must pass before any PR can be merged
- When adding new features, always add corresponding tests
- Use `pytest` fixtures for shared test data
- Mock external API calls (Tudor website, Bland AI, Anthropic, Zippopotam.us) — never make real HTTP requests in tests
- Test files mirror source structure: `tests/test_config.py`, `tests/test_filter.py`, etc.

## Key External Dependencies
- **Bland AI** (`https://api.bland.ai/v1`) — phone calls. API key via `BLAND_API_KEY` env var
- **Anthropic API** — transcript summarization. API key via `ANTHROPIC_API_KEY` env var
- **Zippopotam.us** (`https://api.zippopotam.us`) — zip code geocoding (free, no key needed)
- **Tudor website** (`tudorwatch.com`) — retailer data scraping

## Environment Variables
- `BLAND_API_KEY` — Required for phone calls
- `ANTHROPIC_API_KEY` — Required for transcript summarization

## Git Workflow
- Never push directly to `main` — always create a feature branch and open a PR
- Branch naming: `feature/<description>` or `fix/<description>`
- PRs must have passing tests before merge
- Keep commits focused and atomic
- Use `gh pr create` to open PRs

## What NOT to Do
- Don't hardcode API keys
- Don't make real HTTP requests in tests
- Don't modify `static/index.html` unless the change is specifically about the frontend
- Don't remove existing watches from `config.py` — only add new ones
- Don't change the `Retailer` dataclass fields without updating all consumers (scraper, filter, api, phone_caller)
