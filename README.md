# Singapore Employment Contract Checker

Upload an employment contract (PDF) and see how 11 key terms compare with Singapore's Employment Act 1968 and Ministry of Manpower (MOM) guidance. Each term is marked **Consistent**, **Needs Attention** or **Unable to Assess**, with a quote from the contract (with page number) and an official citation. You can then ask questions about the contract.

**This is not legal advice.** It is a prototype to help you spot terms worth checking.

## Quick start

You need Python 3.11 and an OpenAI API key. Run everything from the repository root.

```bash
make setup    # creates .venv, installs dependencies, creates .env
```

Edit `.env`:

```
OPENAI_API_KEY=sk-...          # your OpenAI key
APP_PASSWORD=choose-a-password # what you'll type to sign in
LLM_MODEL=gpt-4o-mini          # Contract Health Check model (optional)
QA_LLM_MODEL=gpt-5.4-mini      # Ask Your Contract model (optional)
```

Then start the app:

```bash
make run      # opens http://localhost:8501
```

## Try it with the test contract

1. Sign in with your `APP_PASSWORD`.
2. Open **Contract Health Check** and upload `test_contract.pdf` (in the repository root).
3. Click **Analyze**. It takes about 15-20 seconds.
4. Read the report. This contract is deliberately problematic, so expect several **Needs Attention** results, for example:
   - Working hours: 48 hours a week, above the 44-hour limit
   - Overtime: 1.25×, below the 1.5× minimum
   - Annual leave: 5 days, below the 7-day first-year minimum
   - Deductions: uniforms, cash shortfalls and stock losses taken from salary

   Expand any term to see the quote, the reason, the official source and a question you could ask your employer.
5. Open **Ask Your Contract** and try a question, e.g. *"How much notice do I need to give to resign?"* or *"Can my employer deduct stock losses from my pay?"*. The app answers only from the contract and official sources, and says so when it can't.
6. Click **Clear contract & results** when you're done. Nothing is kept after your session ends.

More examples are in `sample_contracts/`: `clear_terms.pdf` (mostly Consistent), `missing_terms.pdf`, `ambiguous.pdf`, `heavy_deductions.pdf` and `varied_notice_leave.pdf`. All names and numbers in them are fictitious.

## Make commands

| Command | What it does |
|---|---|
| `make setup` | Create `.venv`, install dependencies, create `.env` from `.env.example` |
| `make run` | Start the app |
| `make test` | Run the test suite (offline; LLMs are stubbed) |
| `make eval` | Accuracy eval on the 5 sample contracts with the real model (a few cents, about 80 s) |
| `make samples` | Regenerate the sample contract PDFs |
| `make kb` | Rebuild the knowledge-base index (needs `OPENAI_API_KEY`, a few cents) |
| `make secrets-check` | Fail if `.env`, `secrets.toml` or an API key is tracked in git |
| `make clean` | Remove `.venv` and caches |
| `make help` | List all commands |

If `python3.11` isn't on your PATH, use `make setup PYTHON_BIN=python3`.

## Pages

- **Contract Health Check**: upload a PDF and get the 11-term report.
- **Ask Your Contract**: ask questions about the uploaded contract.
- **About Us** and **Methodology**: purpose, scope and how it works.

## Configuration

Settings are read from environment variables, then `.env`, then `st.secrets`.

| Name | Required | Notes |
|---|---|---|
| `OPENAI_API_KEY` | yes | OpenAI API key |
| `APP_PASSWORD` | yes | If unset, nobody can sign in |
| `LLM_MODEL` | no | Contract Health Check model. Default `gpt-4o-mini` |
| `QA_LLM_MODEL` | no | Ask Your Contract model. Default `gpt-5.4-mini` (ADR 0014) |

Never commit `.env` or `.streamlit/secrets.toml` (both are git-ignored).

## Deploy to Streamlit Community Cloud

1. Create a dedicated OpenAI project API key with a monthly budget limit.
2. Run `make secrets-check`.
3. Push the branch to a private GitHub repository.
4. At share.streamlit.io choose **New app**, pick the repo and branch, and set the main file to `app.py`.
5. Under **Advanced settings** choose Python 3.11 and paste the secrets:
   ```toml
   OPENAI_API_KEY = "..."
   APP_PASSWORD = "..."
   ```
6. Deploy. To rotate a key, edit the secrets in the app settings.

See `docs/adr/0012-secrets-and-deployment.md`.

## Knowledge base

The built index is committed in `data/knowledge_base/`, so you don't need to rebuild it to run the app. It holds the Employment Act 1968 and nine MOM guidance pages, listed in `sources.json`, snapshotted on 2026-10-30.

To refresh the sources:
- **Employment Act:** Singapore Statutes Online blocks automated fetching. Save the page from a browser to `data/knowledge_base/source/employment_act.html`, then run `.venv/bin/python scripts/act_html_to_text.py data/knowledge_base/source/employment_act.html data/knowledge_base/employment_act.txt`.
- **MOM pages:** run `.venv/bin/python scripts/fetch_mom.py`.
- Then run `make kb`.

## Accuracy eval

`make eval` runs the real model on the 5 sample contracts and exits 1 if any term is wrongly marked Consistent. Last run (2026-10-30, `gpt-4o-mini`, before ADR 0013 removed the category and salary inputs): 55/55 terms found, 52/55 statuses correct, 0 unsafe Consistent. See `docs/adr/0011-accuracy-eval.md`. The 2026-11-06 model comparison behind the per-page defaults is in `docs/adr/0014-model-per-use-case.md`; `make eval` uses `LLM_MODEL`.

## Known limitations

- A prototype, not legal advice.
- Contract text is sent to OpenAI. The app keeps nothing after the session, but hosting logs are outside its control.
- Text-based PDFs only (no scans), up to 40 pages, English only.
- Hours and overtime are checked for everyone. Part 4 of the Act only covers some employees (s 35), so managers, executives and higher earners may see flags that don't apply to them; the reason says so.
- Statuses can be over-cautious (Needs Attention where Consistent would be right).
- Probation is often Unable to Assess, as no dedicated official guidance is indexed.
- Confidentiality and non-compete are not assessed.
- The weekly-hours figure comes from the LLM and is shown so you can check it.
- Sources and salary ceilings are a 2026-10-30 snapshot and must be refreshed manually.
- The eval set is 5 synthetic contracts, so accuracy figures are indicative only.

## Project structure

```
app.py                  entry point, password gate, navigation
pages/                  health_check, ask_contract, about, methodology
src/                    document_parser, rag_pipeline, contract_analyser,
                        rules_engine, qa, llm, schemas, config, auth, ui
scripts/                build_kb, fetch_mom, act_html_to_text, eval
data/knowledge_base/    sources, passages and vector index
sample_contracts/       synthetic sample PDFs, expected.json, make_samples.py
test_contract.pdf       example contract for trying the app
tests/                  test suite (make test)
docs/adr/               decision records
docs/glossary.md        terms used in the code and UI
```
