# 0012 – Secrets stay with the user; deployment uses the user's own accounts

Date: 2026-10-30 · Status: Accepted

## Context
The app and the scripts (`build_kb.py`, `eval.py`, the manual checks) need `OPENAI_API_KEY` and `APP_PASSWORD`. Streamlit Community Cloud deploys from a GitHub repo, so the code must be on the user's GitHub account. The coding agent should never hold these credentials. A key pasted into chat or committed to git counts as leaked.

## Decision
- One accessor, `src/config.get_secret(name)`, reads the env var first, then a local `.env` (python-dotenv), then `st.secrets` on Cloud. Secret values are never logged, printed or included in error messages.
- Locally, the user types the key into `.env` in their own editor. `.env` and `.streamlit/secrets.toml` are gitignored. Only `.env.example` with placeholders is committed. A test checks the gitignore and scans the repo for `sk-…` strings.
- The agent can run scripts that read `.env` without seeing the key. The user can also run them with `! command`.
- On Cloud, the secrets go only in the app's Secrets settings.
- The user creates a private GitHub repo and signs in to Streamlit Cloud with GitHub. The agent never asks for a GitHub password or token. It pushes only through an existing `gh` login, and only after the user confirms.
- The OpenAI key is a dedicated project key with a monthly budget limit, revoked after grading.

## Consequences
- A leaked key would be limited to the budget cap and easy to revoke.
- Deployment needs a few manual steps from the user; they're listed in T12.
- The repo is private, but the deployed URL is public and protected only by `APP_PASSWORD`.
