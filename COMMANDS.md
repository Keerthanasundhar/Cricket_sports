# Cricket Match Analyst: Command Reference

Run all commands from the project root:

```text
D:\Projects\cricket_analyst_project\cricket_analyst_project
```

Commands below use the project virtual environment directly, so activation is
optional.

## 1. First-time setup

### Create a virtual environment

```bat
python -m venv .venv
```

### Install dependencies

```bat
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Configure environment variables

Create a local environment file:

```bat
copy .env.example .env
```

Set your own values in `.env`:

```env
GROQ_API_KEY=your_groq_key
TAVILY_API_KEY=your_tavily_key
CRICKET_MODEL=openai/gpt-oss-120b
MAX_BUILD_ITERS=8
```

Never commit `.env` or paste API keys into source files.

## 2. Start the application

The project has a fixed Streamlit port configured in
[`.streamlit/config.toml`](./.streamlit/config.toml).

```bat
.venv\Scripts\python.exe -m streamlit run frontend.py
```

Open:

```text
http://localhost:8501
```

There is no separate backend command for normal use. The frontend starts the
MCP statistics subprocess when a question is submitted.

Stop Streamlit with:

```text
Ctrl+C
```

## 3. Database commands

### Generate synthetic data

```bat
.venv\Scripts\python.exe -m cricket_analyst.db --demo
```

This replaces the SQLite database with fictional demo matches and rewrites the
synthetic player CSV.

### Import Cricsheet JSON data

Place extracted JSON files under `data\cricsheet\json`, then run:

```bat
.venv\Scripts\python.exe -m cricket_analyst.db --cricsheet-dir data\cricsheet\json
```

### Import CSV match data

```bat
.venv\Scripts\python.exe -m cricket_analyst.db --matches matches.csv --deliveries deliveries.csv
```

### Download public Cricsheet archives

```bat
curl.exe -k -L --fail https://cricsheet.org/downloads/t20s_json.zip -o data\t20s_json.zip
curl.exe -k -L --fail https://cricsheet.org/downloads/odis_json.zip -o data\odis_json.zip
curl.exe -k -L --fail https://cricsheet.org/downloads/tests_json.zip -o data\tests_json.zip
```

Extract an archive with Python:

```bat
.venv\Scripts\python.exe -c "from pathlib import Path; import zipfile; src=Path('data/t20s_json.zip'); dst=Path('data/cricsheet/json'); dst.mkdir(parents=True,exist_ok=True); zipfile.ZipFile(src).extractall(dst)"
```

Repeat for the ODI and Test archives, then import:

```bat
.venv\Scripts\python.exe -m cricket_analyst.db --cricsheet-dir data\cricsheet\json
```

## 4. ChromaDB commands

### Index knowledge-base documents

```bat
.venv\Scripts\python.exe -m cricket_analyst.rag --ingest
```

This reads Markdown/text files from `knowledge_base\` and writes the local
vector index to `data\chroma\`.

## 5. Testing and validation

### Run the test suite

```bat
.venv\Scripts\python.exe -m pytest tests -q
```

### Check Python syntax

```bat
.venv\Scripts\python.exe -m compileall cricket_analyst frontend.py
```

### Check installed packages

```bat
.venv\Scripts\python.exe -m pip list
```

### Check Groq configuration without printing the key

```bat
.venv\Scripts\python.exe -c "import os; from dotenv import load_dotenv; load_dotenv(); print(bool(os.getenv('GROQ_API_KEY'))); print(os.getenv('CRICKET_MODEL'))"
```

## 6. Useful CLI commands

Ask one question through the command-line workflow:

```bat
.venv\Scripts\python.exe -m cricket_analyst.main "What are Virat Kohli's statistics?"
```

Ask a rules question:

```bat
.venv\Scripts\python.exe -m cricket_analyst.main "How does umpire's call work in DRS?"
```

Start the interactive CLI:

```bat
.venv\Scripts\python.exe -m cricket_analyst.main
```

Run the MCP server directly for integration debugging:

```bat
.venv\Scripts\python.exe -m cricket_analyst.mcp_server
```

## 7. Recommended refresh sequence

After downloading new real data:

```bat
.venv\Scripts\python.exe -m cricket_analyst.db --cricsheet-dir data\cricsheet\json
.venv\Scripts\python.exe -m cricket_analyst.rag --ingest
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m streamlit run frontend.py
```

## 8. Common problems

### Port 8501 is already in use

Stop the previous Streamlit process with `Ctrl+C`, then run the normal command
again. Do not change ports unless another application must use 8501.

### Groq API key missing

Confirm that `.env` exists in the project root and contains `GROQ_API_KEY`.
Restart Streamlit after editing `.env`.

### Groq model unavailable

Set `CRICKET_MODEL` to an active model available to your Groq account, then
restart Streamlit.

### Player not found

The player is not present in the currently imported database, or the name uses a
different data-source spelling. Import a dataset containing the player and retry.

### Chroma results are empty

Run the ingestion command:

```bat
.venv\Scripts\python.exe -m cricket_analyst.rag --ingest
```

## 9. Push the project to GitHub

Before pushing, make sure `.env` is never staged. The repository `.gitignore`
excludes secrets, virtual environments, generated databases, Chroma indexes, and
downloaded archives. If an API key was ever exposed or committed, revoke it in
the provider console and create a replacement before continuing.

Create an empty repository on GitHub, without adding a README, `.gitignore`, or
license because these files already exist locally. Then run these commands from
the project root:

```bat
git init
git branch -M main
git add .
git status
git commit -m "Initial cricket analyst project"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

Replace `YOUR_USERNAME` and `YOUR_REPOSITORY` with your GitHub account and
repository name. Use GitHub authentication (browser sign-in, Git Credential
Manager, or a fine-grained token); never put a token in the remote URL.

Before `git commit`, verify that `.env`, `data/cricket.db`, `data/chroma/`, and
the downloaded `.zip` archives do not appear in `git status`.
