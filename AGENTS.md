# Repository Guidelines

## Project Structure & Module Organization
- `app_backend/` houses the FastAPI service, domain logic under `utils/customize/`, and infrastructure adapters.
- `app_frontend/` contains the React UI; legacy Streamlit lives in `frontend/`.
- Specs and customization docs reside in `customize_docs/`; data samples and notebooks live in `datasets_*/` and `notebooks/`.
- Tests mirror modules: backend tests in `app_backend/tests/`; add new suites alongside the code they verify.

## Build, Test, and Development Commands
- `uv run uvicorn app_backend.app.main:app --reload` starts the local API with auto-reload.
- `pnpm --dir app_frontend dev` runs the React frontend (requires Node 18+, pnpm installed).
- `uv run pytest` executes backend unit tests; append `--cov` for coverage like the scaffolded pipeline.
- `python quickstart.py <project>` provisions the full stack via Pulumi for end-to-end validation.

## Coding Style & Naming Conventions
- Python: follow PEP 8 with type hints; prefer descriptive module names (`report_storage.py`, not `storage_utils.py`).
- React/TypeScript: camelCase for variables, PascalCase for components, colocate hooks under `src/api/`.
- Use f-strings for formatting, avoid inline comments unless clarifying domain intent.

## Testing Guidelines
- Pytest is the canonical backend framework; name files `test_<module>.py` and keep fixtures in `conftest.py`.
- Target ≥80% coverage on new backend modules; hit success/error branches in use cases and adapters.
- For frontend, add React Testing Library specs alongside components when behavior is nontrivial.

## Commit & Pull Request Guidelines
- Commits should follow present-tense summaries (e.g., `Add report storage adapter`).
- Reference related spec sections or tickets in the body; squash noisy WIP history before opening a PR.
- PRs must include: scope summary, testing evidence (`pytest`, UI screenshots if UX changes), and rollout considerations.

## Security & Configuration Tips
- Do not commit secrets; populate `.env` using the provided template and rely on Pulumi config for deployment secrets.
- When touching storage or networking code, review `infra/` Pulumi stacks and update IAM policies or routes in tandem.

## エージェント向け追加指示
- 可能な限り `utils/customize/` ディレクトリ配下のみを操作してください。
- 変更内容や仕様、進行状況は、customize_docs以下のmdに機能ごとに書いて欲しい。
- 日本語で返答してほしい。
- `utils/customize/`以下にクリーンアーキテクチャーに則って実装しているので、それを参考にして欲しい。