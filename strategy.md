# Tech Stack for Aunalytics NL-to-SQL Project

This tech stack is designed to build a robust, **schema-agnostic fullstack web app** that translates natural language queries to SQL, as per the project statement.  
It emphasizes **learning opportunities** (fine-tuning LLMs, MLOps), scalability, and safety features like validation and error handling.  
We've prioritized open-source tools for cost-efficiency and educational value, while pushing boundaries with custom model adaptation over basic API wrappers.

## Frontend

- **Framework**: Next.js (with React and TypeScript)
- **Purpose**: Provides a modern, responsive UI for:
  - User query input (text box with auto-suggestions)
  - Results display (tables, charts, or text summaries)
  - Schema/SQLite file upload (drag-and-drop support)
  - Error messages and explanations (e.g., "Why this SQL?" or ambiguity suggestions)
  - Query history and schema viewer
- **Styling**: shadcn/ui (preferred for accessible, customizable components) or Tailwind CSS (for rapid prototyping)
- **Rationale**: Next.js enables server-side rendering for faster loads and easy API integration. TypeScript adds type safety, reducing bugs — great for learning best practices.

## Backend / API

- **Framework**: FastAPI (Python) — **preferred**  
  → async capabilities, automatic API docs (Swagger), type hints, seamless integration with ML/data libraries
- **Alternative**: Node.js + Express (if the team prefers JavaScript for full-stack consistency)
- **Responsibilities**:
  - Process natural language (NL) inputs
  - Run LLM inference for SQL generation
  - Validate and execute SQL queries
  - Perform schema introspection (e.g., list tables/columns)
  - Handle file uploads and dynamic SQLite connections
- **Rationale**: FastAPI's speed and Python ecosystem make it ideal for ML workflows and robust error handling/scalability.

## NL-to-SQL Core Engine

- **Base Model**:
  - Preferred: Qwen 2.5 Coder 7B Instruct (strong at code/SQL generation)
  - Alternative: Llama 3.1 8B Instruct (widely supported)
- **Techniques**:
  - Prompt engineering: Craft prompts with examples, rules, and schema context
  - Schema injection: Dynamically insert database schema (from SQLite PRAGMA) into prompts
  - Post-generation validation: Check generated SQL for syntax and schema compliance before execution
- **Optional Enhancement**: Fine-tuning using PEFT (LoRA or QLoRA) to improve accuracy on ambiguous or business-oriented queries (e.g., "workers in Chicago" variations)
- **Rationale**: Combines zero-shot prompting with fine-tuning to address intent inference, ambiguity, and precision on arbitrary datasets without hardcoding.

## Fine-Tuning Tools

- **Primary**: Unsloth — fastest and most memory-efficient for QLoRA on single GPUs; supports quick iterations
- **Alternatives**: Axolotl (flexible configs) or Llama-Factory (user-friendly interface)
- **Goal**: Adapt the model to phrasing variations, Aunalytics-style analytics questions (e.g., sales insights), and robustness to incomplete inputs
- **Rationale**: Demonstrates ML customization and boosts domain-specific execution accuracy

## Database Layer

- **Database**: SQLite (file-based, accessed via sqlite3 or SQLAlchemy ORM)
- **Key Features**:
  - Dynamic schema support: Auto-detect tables/columns on upload
  - No server required: Lightweight for demos and deployment
  - Easy file upload: Accept .sqlite or convert CSV/JSON to SQLite in-app
- **Fallback**: Use pandas for importing CSV/Excel files into SQLite tables
- **Rationale**: Matches the project statement — file-based, portable, schema-flexible. Enables testing with arbitrary relational datasets.

## Schema & Query Safety / Validation

- **Tools**:
  - sqlglot: Parse, validate, and rewrite SQL against the live schema (e.g., fix column mismatches)
  - Pydantic: Strict input/output validation and structured JSON responses
- **Custom Logic**:
  - Detect ambiguity (vague terms) and suggest corrections
  - Return user-friendly errors (e.g., "Table 'employees' not found — did you mean 'staff'?")
  - Prevent invalid SQL (injections, misleading queries) with safeguards
- **Rationale**: Ensures robust and user-friendly handling of incomplete/ambiguous inputs while balancing flexibility and precision.

## Training / Evaluation Data

- **Primary Datasets**: Spider (complex SQL queries) + BIRD (big/realistic benchmarks)
- **Augmentation**: Generate synthetic NL-SQL pairs via Ollama, Groq, or Grok API, tailored to business/analytics domains (e.g., finance, healthcare)
- **Metrics**:
  - Execution Accuracy (EX): Does the query run and return correct results?
  - Exact Match (EM): Does generated SQL match gold-standard?
  - Robustness: Success rate on rephrased queries (e.g., 5 variations per test)
- **Rationale**: Supports schema variety/complexity. Augmentation improves relevance to Aunalytics industries.

## Compute Resources

- **Primary**: Notre Dame CRC GPU clusters — free for students; ideal for fine-tuning (e.g., A100 GPUs)
- **Backup/Overflow**: Google Colab Pro, RunPod, or Lambda Labs ($0.40–$1.20/hr for A100/RTX 4090)
- **Rationale**: Leverages free academic resources with scalable paid options to avoid experiment bottlenecks.

## Experiment Tracking

- **Tool**: Weights & Biases (wandb) — free tier for logging runs, metrics, hyperparameters, sample queries/results
- **Rationale**: Essential for tracking fine-tuning progress, evaluating correctness/usability, and team collaboration/presentation evidence.

## Deployment

- **Primary**: Vercel — seamless for Next.js; handles frontend + API routes with auto-scaling
- **Alternatives**: Dockerize the app and deploy to Render, Railway, or Fly.io
- **Goal**: Easy hosting with GitHub CI/CD for automated builds/tests
- **Rationale**: Keeps deployment simple and demo-ready, focusing on the in-person presentation.

## Testing & Documentation

- **Frontend Testing**: Jest + React Testing Library (unit/integration tests for UI components and flows)
- **Backend Testing**: Pytest (API endpoints, validation, edge cases)
- **Documentation**:
  - Markdown files: README, architecture.md (diagrams via Draw.io or Excalidraw)
  - Jupyter notebooks: Evaluation (metrics, examples), trade-offs (flexibility vs. precision), limitations, Aunalytics use cases (non-tech users querying client data)
- **Rationale**: Thorough testing ensures reliability. Documentation demonstrates strong technical judgment.

## Optional / Stretch Features

- LangChain or LlamaIndex: For agentic workflows (refine ambiguous queries) or RAG on large schemas
- Streamlit: Quick internal prototypes/demos during development (e.g., test LLM prompts without full frontend)
- **Rationale**: Adds advanced learning (agents, multi-step queries) without overloading the core — implement if time allows.

## Recommended Team Structure (6 People)

To maximize efficiency and learning, divide roles clearly. Assume weekly stand-ups and GitHub for collaboration.

- **Team Lead / Project Manager + Documentation Lead** (1 person)  
  Owns: Timeline, milestones, repo management, task assignment, coordination  
  Handles: Presentation prep (diagrams, decisions, limitations, Aunalytics use cases, slides/demo)  
  Leads: Docs (README, architecture.md, eval notebook)  
  *Why one person?* Lightweight; suits strong communicators.

- **Frontend Team** (2 people)  
  Builds: Next.js UI (query form, uploads, results, errors, history, explanations)  
  Handles: Styling, responsiveness, user flows (suggestions), API integration (fetching, loading states)  
  *Tip*: Split — one on UI/UX, one on state/API.

- **Backend + Database Integration Team** (2 people)  
  Builds: FastAPI endpoints (introspection, NL → SQL → validate → execute)  
  Handles: SQLite (uploads, connections, execution), validation (sqlglot, Pydantic, ambiguity logic)  
  *Tip*: Split — one on API/execution, one on safety/edge cases.

- **AI / Model Team** (2 people)  
  Builds: NL-to-SQL logic (prompts, schema injection, inference via HF/Unsloth)  
  Handles: Fine-tuning (data prep with Spider/BIRD/synthetics, QLoRA on CRC/Colab, eval)  
  Tracks: Experiments (wandb), model deployment (local/HF)  
  *Tip*: Split — one on prompts/inference, one on fine-tuning/metrics.

This setup aligns with the project's open-ended scope — focusing on innovation while delivering a polished, demo-ready app.  
It promotes deep learning in AI, full-stack development, and system design. Let's iterate based on team feedback!

---
---

# Execution Roadmap
Start Date: March 1, 2026

---

## Week 1: March 1 – March 7

### Team 1 (Frontend) – Deliverables

- **Task 1: Initialize Next.js monorepo with TypeScript strict mode**
  - Tools: `npx create-next-app@latest` with `--typescript --eslint --tailwind --app` flags
  - Output Artifact: `/frontend/` directory with `tsconfig.json` (`strict: true`), `next.config.js`, `package.json`, `.eslintrc.json`
  - Definition of Done: `npm run build` completes with zero errors; `npm run dev` serves at `localhost:3000`; TypeScript strict mode enforced in `tsconfig.json`
  - Dependencies: None

- **Task 2: Install and configure shadcn/ui component library**
  - Tools: `npx shadcn-ui@latest init`, Tailwind CSS v3
  - Output Artifact: `frontend/components.json`, `frontend/lib/utils.ts`, `frontend/tailwind.config.ts` with shadcn preset, `frontend/app/globals.css` with CSS variables for theming
  - Definition of Done: `npx shadcn-ui@latest add button` installs successfully; a test `<Button>` renders in the browser at `localhost:3000`
  - Dependencies: Task 1

- **Task 3: Create static page layout scaffolding**
  - Tools: Next.js App Router, React, shadcn/ui `Card`, `Input`, `Button` components
  - Output Artifact: `frontend/app/page.tsx` (main query page), `frontend/app/layout.tsx` (root layout with sidebar nav), `frontend/components/QueryInput.tsx` (static text input), `frontend/components/ResultsPanel.tsx` (placeholder results area)
  - Definition of Done: All four files render without errors; layout visible at `localhost:3000` with a text input, submit button, and empty results card; Lighthouse accessibility score ≥ 90
  - Dependencies: Task 2

- **Task 4: Configure ESLint + Prettier with pre-commit hooks**
  - Tools: ESLint, Prettier, `husky`, `lint-staged`
  - Output Artifact: `frontend/.eslintrc.json`, `frontend/.prettierrc`, `frontend/.husky/pre-commit`, `frontend/package.json` updated with `lint-staged` config
  - Definition of Done: Running `git commit` on a malformatted `.tsx` file auto-formats it; `npm run lint` exits with code 0 on the existing codebase
  - Dependencies: Task 1

- **Task 5: Set up Jest + React Testing Library with initial test**
  - Tools: Jest, `@testing-library/react`, `@testing-library/jest-dom`, `ts-jest`
  - Output Artifact: `frontend/jest.config.ts`, `frontend/__tests__/QueryInput.test.tsx`
  - Definition of Done: `npm run test` executes; `QueryInput.test.tsx` asserts the input field renders and accepts text; test passes with exit code 0
  - Dependencies: Tasks 1, 3

### Team 2 (Backend + Database) – Deliverables

- **Task 1: Initialize FastAPI project with dependency management**
  - Tools: Python 3.11+, FastAPI, Uvicorn, `pip`, `pyproject.toml` or `requirements.txt`
  - Output Artifact: `/backend/` directory with `main.py`, `requirements.txt` (containing `fastapi>=0.110`, `uvicorn[standard]>=0.29`, `pydantic>=2.6`, `sqlalchemy>=2.0`, `sqlglot>=23.0`, `python-multipart>=0.0.9`), `backend/__init__.py`
  - Definition of Done: `uvicorn main:app --reload` starts; `GET /health` returns `{"status": "ok"}` with HTTP 200; Swagger UI accessible at `/docs`
  - Dependencies: None

- **Task 2: Define Pydantic request/response schemas**
  - Tools: Pydantic v2, Python type hints
  - Output Artifact: `backend/schemas.py` containing models: `NLQueryRequest(query: str, db_filename: str)`, `SQLResponse(sql: str, results: list[dict], columns: list[str], error: str | None)`, `SchemaIntrospectionResponse(tables: list[TableSchema])`, `TableSchema(name: str, columns: list[ColumnInfo])`, `ColumnInfo(name: str, type: str, nullable: bool, primary_key: bool)`
  - Definition of Done: `python -c "from schemas import *; print(NLQueryRequest.model_json_schema())"` prints valid JSON Schema; all models round-trip serialize/deserialize in a Pytest unit test
  - Dependencies: Task 1

- **Task 3: Implement SQLite file upload endpoint with dynamic connection**
  - Tools: FastAPI `UploadFile`, `sqlite3`, Python `pathlib`, `shutil`
  - Output Artifact: `backend/routers/upload.py` with `POST /api/upload` endpoint; `backend/db/` directory for storing uploaded `.sqlite` files
  - Definition of Done: `curl -F "file=@chinook.sqlite" http://localhost:8000/api/upload` returns `{"filename": "chinook.sqlite", "tables": ["albums", "artists", ...]}` with HTTP 201; uploaded file exists in `backend/db/chinook.sqlite`; rejects non-`.sqlite`/`.csv` files with HTTP 415
  - Dependencies: Tasks 1, 2

- **Task 4: Implement schema introspection endpoint using SQLite PRAGMA**
  - Tools: `sqlite3` `PRAGMA table_info()`, `PRAGMA table_list()`, FastAPI
  - Output Artifact: `backend/routers/schema.py` with `GET /api/schema/{db_filename}` endpoint
  - Definition of Done: `GET /api/schema/chinook.sqlite` returns JSON matching `SchemaIntrospectionResponse` with all tables, column names, types, and primary key flags from the Chinook database; returns HTTP 404 for non-existent files
  - Dependencies: Tasks 1, 2, 3

- **Task 5: Configure Pytest test suite with initial endpoint tests**
  - Tools: Pytest, `httpx` (for `TestClient`), FastAPI `TestClient`
  - Output Artifact: `backend/tests/conftest.py` (shared fixtures including test SQLite DB), `backend/tests/test_health.py`, `backend/tests/test_upload.py`
  - Definition of Done: `pytest backend/tests/ -v` runs; `test_health.py` asserts `GET /health` returns 200; `test_upload.py` asserts valid upload returns 201 and invalid file returns 415; all tests pass
  - Dependencies: Tasks 1, 3

### Team 3 (AI / Model) – Deliverables

- **Task 1: Set up Notre Dame CRC GPU cluster access and environment**
  - Tools: SSH, `module load` (CUDA 12.x, Python 3.11), `conda` or `venv`, SLURM job scheduler
  - Output Artifact: `ai/environment.yml` (conda env with `torch>=2.2`, `transformers>=4.40`, `unsloth>=2024.3`, `datasets>=2.18`, `wandb>=0.16`, `peft>=0.10`, `bitsandbytes>=0.43`), `ai/slurm/train_job.sh` (SLURM batch script requesting 1x A100 80GB, 32GB RAM, 8 CPU cores, 6hr wall time)
  - Definition of Done: `conda activate nlsql` on CRC head node succeeds; `python -c "import torch; print(torch.cuda.is_available())"` prints `True` on a GPU node; SLURM test job (`srun --gres=gpu:1 nvidia-smi`) completes and shows A100 GPU
  - Dependencies: None

- **Task 2: Download and verify Qwen 2.5 Coder 7B Instruct model weights**
  - Tools: Hugging Face `transformers`, `huggingface-cli download Qwen/Qwen2.5-Coder-7B-Instruct`
  - Output Artifact: Model weights cached in `~/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/`, verification script `ai/scripts/verify_model.py`
  - Definition of Done: `verify_model.py` loads tokenizer and model in 4-bit quantization (via `bitsandbytes`), runs inference on prompt `"SELECT * FROM"`, and prints a valid SQL completion; script exits with code 0; model size on disk ≤ 5GB (4-bit)
  - Dependencies: Task 1

- **Task 3: Download and preprocess Spider dataset**
  - Tools: Python, `datasets` library (`load_dataset("spider")`), `json`
  - Output Artifact: `ai/data/spider_train.json`, `ai/data/spider_dev.json` — each record containing `{"question": str, "query": str, "db_id": str, "schema": str}`; preprocessing script `ai/scripts/prep_spider.py`
  - Definition of Done: `prep_spider.py` outputs `spider_train.json` with 7,000+ training examples and `spider_dev.json` with 1,034 dev examples; each record has all four fields populated; `python -c "import json; d=json.load(open('ai/data/spider_train.json')); print(len(d))"` prints ≥ 7000
  - Dependencies: Task 1

- **Task 4: Download and preprocess BIRD dataset**
  - Tools: Python, BIRD benchmark download from official source, `json`, `sqlite3`
  - Output Artifact: `ai/data/bird_train.json`, `ai/data/bird_dev.json` in same schema as Spider; preprocessing script `ai/scripts/prep_bird.py`
  - Definition of Done: `prep_bird.py` outputs `bird_train.json` with 9,000+ training examples; each record includes `question`, `query`, `db_id`, and `schema` (extracted via `PRAGMA table_info` from BIRD's SQLite files); script exits with code 0
  - Dependencies: Task 1

- **Task 5: Initialize Weights & Biases project and logging config**
  - Tools: `wandb` Python SDK, `wandb login`
  - Output Artifact: `ai/wandb_config.py` (project name: `aunalytics-nlsql`, entity: team name, default tags: `["qwen2.5-7b", "qlora", "spider", "bird"]`), `.env` entry for `WANDB_API_KEY`
  - Definition of Done: `python ai/wandb_config.py` creates a test run in the `aunalytics-nlsql` W&B project visible at `wandb.ai/<entity>/aunalytics-nlsql`; run logs a dummy metric `{"test_metric": 1.0}` and completes; run visible in W&B dashboard
  - Dependencies: Task 1

---

## Week 2: March 8 – March 14

### Team 1 (Frontend) – Deliverables

- **Task 1: Build FileUpload component with drag-and-drop for .sqlite and .csv**
  - Tools: React, `react-dropzone`, shadcn/ui `Dialog`, `Progress` components, Next.js API route proxy
  - Output Artifact: `frontend/components/FileUpload.tsx`, `frontend/app/api/upload/route.ts` (proxy to FastAPI `POST /api/upload`)
  - Definition of Done: Drag-and-drop `.sqlite` file triggers upload via `POST /api/upload`; progress bar displays during upload; success toast shows table count; `.exe` files rejected client-side with error toast; component test in `__tests__/FileUpload.test.tsx` passes
  - Dependencies: Team 2 Week 1 Task 3 (`POST /api/upload` endpoint)

- **Task 2: Build SchemaViewer component using introspection API**
  - Tools: React, shadcn/ui `Accordion`, `Table`, `Badge` components, `swr` or `react-query` for data fetching
  - Output Artifact: `frontend/components/SchemaViewer.tsx`, `frontend/hooks/useSchema.ts`
  - Definition of Done: After file upload, `SchemaViewer` calls `GET /api/schema/{db_filename}` and renders an accordion with one section per table; each section lists columns with name, type, and PK badge; empty state shows "No database loaded"; unit test asserts accordion renders correct table count from mocked API response
  - Dependencies: Team 2 Week 1 Task 4 (`GET /api/schema/{db_filename}` endpoint)

- **Task 3: Implement QueryInput component with submission logic**
  - Tools: React `useState`/`useReducer`, shadcn/ui `Textarea`, `Button`, `Kbd` components
  - Output Artifact: `frontend/components/QueryInput.tsx` (updated from static to functional), `frontend/hooks/useQuerySubmit.ts`
  - Definition of Done: User types natural language query and presses Enter or clicks Submit; request sent as `POST /api/query` with `{query, db_filename}`; loading spinner shown during request; empty query submission prevented with inline validation; unit test verifies `onSubmit` callback fires with correct payload
  - Dependencies: None (uses mocked endpoint until Team 2 delivers)

- **Task 4: Create ResultsTable component for SQL query output**
  - Tools: React, shadcn/ui `Table`, `ScrollArea` components, `@tanstack/react-table` for column sorting/pagination
  - Output Artifact: `frontend/components/ResultsTable.tsx`
  - Definition of Done: Component accepts `{columns: string[], results: dict[], sql: string}` props; renders a sortable table with column headers and rows; displays "No results" for empty arrays; SQL string shown in a collapsible `<code>` block above the table; handles 1000+ row datasets without visible lag (virtual scroll via `@tanstack/react-virtual` if needed); unit test asserts 5-row mock data renders correctly
  - Dependencies: None

- **Task 5: Set up GitHub Actions CI pipeline for frontend**
  - Tools: GitHub Actions, Node.js 20, `actions/cache` for `node_modules`
  - Output Artifact: `.github/workflows/frontend-ci.yml`
  - Definition of Done: On every push to `main` or PR, CI runs `npm ci`, `npm run lint`, `npm run build`, `npm run test`; pipeline completes in < 3 minutes; badge in `README.md` shows build status; first green run visible in GitHub Actions tab
  - Dependencies: Week 1 Tasks 1, 4, 5

### Team 2 (Backend + Database) – Deliverables

- **Task 1: Implement CSV/JSON-to-SQLite conversion endpoint**
  - Tools: FastAPI `UploadFile`, `pandas` (`pd.read_csv`, `pd.read_json`), `sqlite3`, SQLAlchemy `create_engine`
  - Output Artifact: `backend/routers/upload.py` (extended to handle `.csv` and `.json`), `backend/services/converter.py` (CSV/JSON → SQLite conversion logic)
  - Definition of Done: `POST /api/upload` with a `.csv` file creates a new `.sqlite` file in `backend/db/` with a table matching the CSV columns; column types inferred via `pandas` dtype mapping; `POST /api/upload` with `.json` (array of objects) similarly creates a SQLite table; Pytest test `test_csv_upload` and `test_json_upload` pass with assertions on table schema
  - Dependencies: Week 1 Tasks 1–3

- **Task 2: Implement SQL execution endpoint with read-only safety**
  - Tools: FastAPI, `sqlite3`, `sqlglot` for SQL parsing
  - Output Artifact: `backend/routers/query.py` with `POST /api/execute` endpoint; `backend/services/executor.py`
  - Definition of Done: `POST /api/execute {"sql": "SELECT * FROM albums LIMIT 5", "db_filename": "chinook.sqlite"}` returns `{"columns": [...], "results": [...], "row_count": 5}`; `POST /api/execute {"sql": "DROP TABLE albums", ...}` returns HTTP 403 with `{"error": "Only SELECT statements are allowed"}`; `sqlglot.parse()` used to verify statement type; Pytest tests for SELECT (200), DROP (403), INSERT (403), and malformed SQL (400) all pass
  - Dependencies: Week 1 Tasks 1–4

- **Task 3: Implement sqlglot-based SQL validation service**
  - Tools: `sqlglot` (parse, transpile, validate), Python
  - Output Artifact: `backend/services/sql_validator.py` with functions: `validate_syntax(sql: str) -> bool`, `validate_against_schema(sql: str, schema: dict) -> list[str]`, `extract_tables_and_columns(sql: str) -> dict`
  - Definition of Done: `validate_syntax("SELCT * FORM users")` returns `False`; `validate_against_schema("SELECT name FROM employees", {"staff": ["name", "id"]})` returns `["Table 'employees' not found. Available: staff"]`; `extract_tables_and_columns("SELECT a.name, b.price FROM users a JOIN products b ON a.id = b.uid")` returns `{"users": ["name"], "products": ["price"]}`; 10+ Pytest unit tests covering edge cases pass
  - Dependencies: Week 1 Tasks 1, 2

- **Task 4: Add structured logging with correlation IDs**
  - Tools: Python `structlog`, `uuid4` for correlation IDs, FastAPI middleware
  - Output Artifact: `backend/middleware/logging.py` (FastAPI middleware injecting `X-Request-ID`), `backend/core/logger.py` (`structlog` configuration with JSON output)
  - Definition of Done: Every API request logs `{"request_id": uuid, "method": str, "path": str, "status_code": int, "duration_ms": float}` to stdout as JSON; logs visible in terminal during `uvicorn` run; `X-Request-ID` header returned in every HTTP response; Pytest test asserts middleware injects header
  - Dependencies: Week 1 Task 1

- **Task 5: Set up GitHub Actions CI pipeline for backend**
  - Tools: GitHub Actions, Python 3.11, `pip`, Pytest
  - Output Artifact: `.github/workflows/backend-ci.yml`
  - Definition of Done: On push to `main` or PR, CI runs `pip install -r requirements.txt`, `pytest backend/tests/ -v --tb=short`; pipeline completes in < 2 minutes; all existing tests pass; badge in `README.md`
  - Dependencies: Week 1 Task 5

### Team 3 (AI / Model) – Deliverables

- **Task 1: Build zero-shot prompt template for NL-to-SQL with schema injection**
  - Tools: Python, Jinja2 templating, `sqlite3` (`PRAGMA table_info`)
  - Output Artifact: `ai/prompts/nl_to_sql.j2` (Jinja2 template), `ai/services/prompt_builder.py` (function `build_prompt(question: str, schema: dict) -> str`)
  - Definition of Done: `build_prompt("Show all employees in Chicago", chinook_schema)` produces a prompt string containing: system instruction, full schema DDL, few-shot examples (3 NL-SQL pairs), and the user question; prompt length ≤ 2048 tokens measured via Qwen tokenizer; 5 unit tests in `ai/tests/test_prompt_builder.py` pass
  - Dependencies: Week 1 Tasks 1, 2

- **Task 2: Implement local inference pipeline with Qwen 2.5 Coder 7B**
  - Tools: `transformers`, `bitsandbytes` (4-bit quantization), `torch`, Hugging Face `AutoModelForCausalLM`
  - Output Artifact: `ai/services/inference.py` with function `generate_sql(prompt: str, max_tokens: int = 256) -> str`; `ai/config.py` (model name, quantization config, generation params: `temperature=0.1`, `top_p=0.95`, `max_new_tokens=256`)
  - Definition of Done: `generate_sql(build_prompt("List all albums", chinook_schema))` returns a string starting with `SELECT`; inference completes in < 10 seconds on A100 GPU; function extracts only the SQL portion from model output (strips explanation text); 3 integration tests in `ai/tests/test_inference.py` pass on GPU node
  - Dependencies: Week 1 Tasks 1, 2; this task's Task 1

- **Task 3: Build evaluation harness for Execution Accuracy (EX) metric**
  - Tools: Python, `sqlite3`, `json`, Spider dev set
  - Output Artifact: `ai/eval/evaluate_ex.py` with function `compute_execution_accuracy(predictions: list[dict], gold: list[dict], db_dir: str) -> float`
  - Definition of Done: Function executes both predicted and gold SQL against the target database; compares result sets (order-insensitive); returns accuracy as float [0.0, 1.0]; running on 50 Spider dev samples produces a baseline EX score; score logged to stdout and saved to `ai/eval/results/baseline_ex.json` with timestamp
  - Dependencies: Week 1 Tasks 3, 4 (Spider/BIRD data)

- **Task 4: Build evaluation harness for Exact Match (EM) metric**
  - Tools: Python, `sqlglot` (for SQL normalization), `json`
  - Output Artifact: `ai/eval/evaluate_em.py` with function `compute_exact_match(predictions: list[str], gold: list[str]) -> float`
  - Definition of Done: Function normalizes SQL (lowercase, remove whitespace, standardize aliases via `sqlglot.transpile`) before comparison; running on 50 Spider dev samples produces a baseline EM score; score saved to `ai/eval/results/baseline_em.json`; 5 unit tests covering edge cases (alias differences, whitespace, keyword casing) pass
  - Dependencies: Week 1 Tasks 3, 4

- **Task 5: Run baseline zero-shot evaluation on Spider dev set (first 200 samples)**
  - Tools: Python, CRC GPU node (A100), SLURM, `wandb`
  - Output Artifact: `ai/eval/results/baseline_spider_200.json` (per-sample predictions + scores), W&B run with logged EX and EM metrics
  - Definition of Done: SLURM job `sbatch ai/slurm/eval_baseline.sh` completes; `baseline_spider_200.json` contains 200 entries with fields `{question, gold_sql, predicted_sql, ex_correct: bool, em_correct: bool}`; aggregate EX and EM scores logged to W&B run titled `baseline-zero-shot-spider-200`; scores printed in job stdout
  - Dependencies: Tasks 1–4

---

## Week 3: March 15 – March 21

### Team 1 (Frontend) – Deliverables

- **Task 1: Build QueryHistory component with localStorage persistence**
  - Tools: React, shadcn/ui `ScrollArea`, `Card`, `Badge`, `localStorage` API
  - Output Artifact: `frontend/components/QueryHistory.tsx`, `frontend/hooks/useQueryHistory.ts`
  - Definition of Done: Each submitted query (NL text + generated SQL + timestamp) saved to `localStorage` under key `nlsql_history`; `QueryHistory` renders a scrollable list of past queries; clicking a history item re-populates the `QueryInput` field; "Clear History" button removes all entries; max 100 entries with FIFO eviction; unit test asserts storage read/write and re-population behavior
  - Dependencies: Week 2 Task 3

- **Task 2: Build ErrorDisplay component for user-friendly error rendering**
  - Tools: React, shadcn/ui `Alert`, `AlertDescription` components
  - Output Artifact: `frontend/components/ErrorDisplay.tsx`
  - Definition of Done: Component accepts `{error: string, suggestion?: string, sql?: string}` props; renders red alert with error message; if `suggestion` provided, renders amber alert with "Did you mean..." text; if `sql` provided, renders the failing SQL in a `<code>` block; unit test covers all three states (error only, error + suggestion, error + sql)
  - Dependencies: None

- **Task 3: Integrate frontend with FastAPI backend via environment-based API URL**
  - Tools: Next.js environment variables (`.env.local`), `fetch` API, `frontend/lib/api.ts`
  - Output Artifact: `frontend/.env.local` (`NEXT_PUBLIC_API_URL=http://localhost:8000`), `frontend/lib/api.ts` (typed functions: `uploadFile(file: File)`, `getSchema(dbFilename: string)`, `submitQuery(query: string, dbFilename: string)`, `executeSQL(sql: string, dbFilename: string)`)
  - Definition of Done: All four API functions call correct backend endpoints; each function handles HTTP errors and returns typed responses matching Pydantic schemas; `uploadFile` → 201, `getSchema` → 200, `submitQuery` → 200, `executeSQL` → 200 or 403; integration test with running backend confirms round-trip for file upload + schema fetch
  - Dependencies: Team 2 Week 1–2 endpoints

- **Task 4: Build SQLExplanation component ("Why this SQL?")**
  - Tools: React, shadcn/ui `Collapsible`, `Code` components, `highlight.js` or `prism-react-renderer` for SQL syntax highlighting
  - Output Artifact: `frontend/components/SQLExplanation.tsx`
  - Definition of Done: Component renders generated SQL with syntax highlighting (keywords in blue, strings in green, numbers in orange); collapsible section shows the raw NL query and schema context used; "Copy SQL" button copies to clipboard; unit test asserts syntax highlighting renders and clipboard API is called
  - Dependencies: None

- **Task 5: Implement responsive layout and dark mode toggle**
  - Tools: Tailwind CSS `dark:` variants, shadcn/ui `Switch` component, `next-themes`
  - Output Artifact: `frontend/components/ThemeToggle.tsx`, updated `frontend/app/layout.tsx` with `ThemeProvider`
  - Definition of Done: Toggle between light/dark themes via switch in header; preference persisted in `localStorage`; all components (QueryInput, ResultsTable, SchemaViewer, FileUpload) render correctly in both themes; no contrast ratio below 4.5:1 (WCAG AA); mobile layout (≤ 768px) stacks sidebar below main content; Lighthouse accessibility ≥ 90 in both themes
  - Dependencies: All prior frontend components

### Team 2 (Backend + Database) – Deliverables

- **Task 1: Implement NL-to-SQL orchestration endpoint**
  - Tools: FastAPI, Pydantic, `httpx` or direct Python import for AI service communication
  - Output Artifact: `backend/routers/query.py` with `POST /api/query` endpoint; `backend/services/orchestrator.py`
  - Definition of Done: `POST /api/query {"query": "Show all albums", "db_filename": "chinook.sqlite"}` calls: (1) schema introspection → (2) AI prompt building → (3) SQL generation → (4) SQL validation via `sqlglot` → (5) SQL execution; returns `{"sql": "SELECT ...", "results": [...], "columns": [...], "validation_warnings": [...]}` with HTTP 200; end-to-end Pytest test with mocked AI service passes
  - Dependencies: Week 2 Tasks 2, 3; Team 3 inference service

- **Task 2: Implement ambiguity detection and suggestion logic**
  - Tools: Python, `sqlglot`, `difflib.get_close_matches`, Pydantic
  - Output Artifact: `backend/services/ambiguity_detector.py` with function `detect_ambiguity(sql: str, schema: dict) -> AmbiguityResult`; `AmbiguityResult` model with fields `is_ambiguous: bool`, `suggestions: list[str]`, `confidence: float`
  - Definition of Done: `detect_ambiguity("SELECT * FROM employees", {"staff": ["name"]})` returns `{is_ambiguous: True, suggestions: ["Did you mean table 'staff'?"], confidence: 0.85}`; fuzzy matching threshold configurable (default: 0.6 similarity); handles column-level ambiguity (e.g., `"SELECT salary"` when column is `"annual_salary"`); 8+ Pytest tests covering table mismatches, column mismatches, exact matches, and no-match cases
  - Dependencies: Week 2 Task 3

- **Task 3: Add CORS middleware and API rate limiting**
  - Tools: FastAPI `CORSMiddleware`, `slowapi` (rate limiting based on IP)
  - Output Artifact: `backend/middleware/cors.py`, `backend/middleware/rate_limit.py`, updated `backend/main.py`
  - Definition of Done: `Access-Control-Allow-Origin` header set to `["http://localhost:3000"]` in dev (configurable via env var `ALLOWED_ORIGINS`); rate limit of 30 requests/minute per IP on `/api/query`; exceeding limit returns HTTP 429 with `{"error": "Rate limit exceeded"}`; Pytest test confirms CORS headers present and rate limit triggers after 30 rapid requests
  - Dependencies: Week 1 Task 1

- **Task 4: Implement Excel-to-SQLite conversion via pandas**
  - Tools: `pandas` (`pd.read_excel`), `openpyxl`, FastAPI
  - Output Artifact: `backend/services/converter.py` (extended for `.xlsx`/`.xls`); updated `backend/routers/upload.py`
  - Definition of Done: `POST /api/upload` with `.xlsx` file creates a SQLite DB with one table per Excel sheet; column types inferred from pandas dtypes; multi-sheet workbooks produce multiple tables named after sheet names; Pytest test with a 3-sheet `.xlsx` fixture asserts 3 tables created with correct schemas
  - Dependencies: Week 2 Task 1

- **Task 5: Write architecture.md with system diagram**
  - Tools: Markdown, Draw.io or Excalidraw (exported as PNG/SVG)
  - Output Artifact: `docs/architecture.md` with sections: System Overview, Component Diagram (Frontend ↔ API ↔ AI Service ↔ SQLite), API Endpoint Table (method, path, request/response schemas), Data Flow (NL → prompt → SQL → validate → execute → results), Technology Stack Table; `docs/diagrams/system_overview.png`
  - Definition of Done: `architecture.md` contains all five sections; system diagram shows all components with labeled arrows; API table lists all implemented endpoints with HTTP method, path, request body, and response schema; reviewed and merged via PR with ≥ 1 approval
  - Dependencies: All Week 1–2 backend work

### Team 3 (AI / Model) – Deliverables

- **Task 1: Design and generate synthetic NL-SQL training pairs via Ollama**
  - Tools: Ollama (local), Qwen 2.5 or Llama 3.1 via Ollama, Python, `json`
  - Output Artifact: `ai/scripts/generate_synthetic.py`, `ai/data/synthetic_train.json` (500+ NL-SQL pairs covering finance, healthcare, retail, HR domains)
  - Definition of Done: Each synthetic pair contains `{question, query, db_id, schema, domain}`; 5+ domain categories represented; 100+ pairs per domain; no duplicate questions; script reproducible with `--seed` flag; manual review of 20 random samples shows ≥ 90% syntactically valid SQL
  - Dependencies: Week 1 Tasks 1, 3, 4

- **Task 2: Prepare unified fine-tuning dataset in Alpaca/chat format**
  - Tools: Python, `datasets` library, `json`
  - Output Artifact: `ai/scripts/prepare_finetune_data.py`, `ai/data/finetune_train.jsonl`, `ai/data/finetune_val.jsonl`
  - Definition of Done: Merged Spider train + BIRD train + synthetic data into Alpaca chat format: `{"instruction": system_prompt_with_schema, "input": nl_question, "output": sql_query}`; train/val split 90/10; `finetune_train.jsonl` contains ≥ 15,000 examples; `finetune_val.jsonl` contains ≥ 1,500 examples; no data leakage between train and Spider/BIRD dev sets (verified by script assertion)
  - Dependencies: Week 1 Tasks 3, 4; Week 3 Task 1

- **Task 3: Configure Unsloth QLoRA fine-tuning script**
  - Tools: Unsloth, PEFT (LoRA config: `r=16`, `lora_alpha=32`, `target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]`, `lora_dropout=0.05`), `bitsandbytes` 4-bit
  - Output Artifact: `ai/training/train_qlora.py` with full training configuration; `ai/training/config.yaml` (hyperparams: `learning_rate=2e-4`, `batch_size=4`, `gradient_accumulation_steps=4`, `epochs=3`, `warmup_ratio=0.03`, `weight_decay=0.01`, `max_seq_length=2048`)
  - Definition of Done: `python ai/training/train_qlora.py --config ai/training/config.yaml --data ai/data/finetune_train.jsonl --output ai/models/qwen-nlsql-v1` initializes training without errors on CRC A100; first 100 steps complete with decreasing loss logged to W&B; training checkpoints saved every 500 steps to `ai/models/qwen-nlsql-v1/checkpoint-*/`
  - Dependencies: Task 2; Week 1 Tasks 1, 2

- **Task 4: Build Streamlit prototype for interactive prompt testing**
  - Tools: Streamlit, Python, `transformers`
  - Output Artifact: `ai/streamlit_app.py`
  - Definition of Done: `streamlit run ai/streamlit_app.py` launches at `localhost:8501`; UI has: (1) text area for NL query, (2) dropdown to select database, (3) editable prompt template, (4) "Generate SQL" button, (5) display of generated SQL + raw model output + token count + latency (ms); latency displayed per query; works with local Qwen model
  - Dependencies: Week 2 Tasks 1, 2

- **Task 5: Run baseline zero-shot evaluation on full Spider dev set (1034 samples)**
  - Tools: CRC A100 GPU, SLURM, Python, `wandb`
  - Output Artifact: `ai/eval/results/baseline_spider_full.json`, W&B run `baseline-zero-shot-spider-full`
  - Definition of Done: SLURM job completes within 4 hours; all 1,034 Spider dev samples evaluated; `baseline_spider_full.json` contains per-sample results; aggregate EX and EM scores logged to W&B; results broken down by difficulty (easy/medium/hard/extra) in W&B table; baseline EX documented in `ai/eval/results/README.md`
  - Dependencies: Week 2 Tasks 3, 4, 5

---

## Week 4: March 22 – March 28

### Team 1 (Frontend) – Deliverables

- **Task 1: Implement auto-suggestion dropdown for query input**
  - Tools: React, shadcn/ui `Command` (combobox), `useDebouncedValue` custom hook
  - Output Artifact: `frontend/components/QuerySuggestions.tsx`, `frontend/hooks/useSuggestions.ts`
  - Definition of Done: As user types in `QueryInput`, a dropdown shows: (1) table/column names from loaded schema matching input substring, (2) up to 5 recent queries from history matching prefix; suggestions appear after 300ms debounce; keyboard navigation (↑↓ Enter Esc) works; selecting a suggestion populates the input; dropdown dismissed on blur; unit test verifies debounce behavior and keyboard navigation
  - Dependencies: Week 2 SchemaViewer, Week 3 QueryHistory

- **Task 2: Build chart visualization component for numeric query results**
  - Tools: `recharts` library, React, shadcn/ui `Tabs` component
  - Output Artifact: `frontend/components/ResultsChart.tsx`
  - Definition of Done: When query results contain ≥ 1 numeric column and ≥ 1 string/date column, a "Chart" tab appears alongside the "Table" tab; auto-detects chart type: bar chart (categorical x-axis), line chart (date x-axis); user can toggle between chart and table views; chart renders with labeled axes, tooltips, and legend; component handles up to 500 data points without lag; unit test asserts chart renders for numeric data and hides for text-only results
  - Dependencies: Week 2 Task 4 (ResultsTable)

- **Task 3: Implement loading states and skeleton screens**
  - Tools: React, shadcn/ui `Skeleton` component
  - Output Artifact: `frontend/components/LoadingSkeleton.tsx`, updated `QueryInput.tsx`, `ResultsTable.tsx`, `SchemaViewer.tsx`
  - Definition of Done: During API calls, skeleton placeholders matching component dimensions shown in: ResultsTable (5 shimmer rows), SchemaViewer (3 accordion items), FileUpload (upload area pulse); submit button shows spinner and disables during query; all loading states accessible (aria-busy="true"); unit tests for each component assert skeleton visibility during loading state
  - Dependencies: All prior frontend components

- **Task 4: Add keyboard shortcuts for power users**
  - Tools: React, `useHotkeys` hook (from `react-hotkeys-hook`), shadcn/ui `Kbd` component
  - Output Artifact: `frontend/hooks/useKeyboardShortcuts.ts`, `frontend/components/ShortcutsDialog.tsx`
  - Definition of Done: `Ctrl+Enter` submits query; `Ctrl+K` focuses query input; `Ctrl+/` opens keyboard shortcuts dialog; `Escape` closes any open modal/dialog; shortcuts displayed in footer; shortcuts dialog lists all available shortcuts with descriptions; unit test asserts each shortcut triggers correct action
  - Dependencies: Week 2 Task 3

- **Task 5: End-to-end Cypress test for upload → query → results flow**
  - Tools: Cypress, `cypress-file-upload` plugin
  - Output Artifact: `frontend/cypress/e2e/query_flow.cy.ts`, `frontend/cypress.config.ts`, `frontend/cypress/fixtures/test.sqlite`
  - Definition of Done: Cypress test: (1) uploads `test.sqlite` via drag-and-drop, (2) verifies schema viewer shows expected tables, (3) types NL query "Show all records", (4) clicks Submit, (5) verifies results table renders with data rows, (6) verifies SQL explanation section is populated; test passes in headless mode (`npx cypress run`); added to CI pipeline
  - Dependencies: All prior frontend work; running backend

### Team 2 (Backend + Database) – Deliverables

- **Task 1: Implement FastAPI endpoint for NL-to-SQL with AI service integration**
  - Tools: FastAPI, `httpx` (async HTTP client), Pydantic, Python `asyncio`
  - Output Artifact: `backend/routers/query.py` (updated `POST /api/query`), `backend/services/ai_client.py` (async client to AI inference service)
  - Definition of Done: `POST /api/query {"query": "List all customers", "db_filename": "chinook.sqlite"}` orchestrates: schema fetch → prompt build → AI inference → SQL validation → execution → response; response includes `sql`, `results`, `columns`, `validation_warnings`, `latency_ms`; end-to-end test with real AI service returns valid SQL for Chinook database; latency_ms field accurately measures AI inference time
  - Dependencies: Team 3 Week 2 Task 2 (inference service)

- **Task 2: Build SQL injection prevention and query sanitization layer**
  - Tools: `sqlglot`, Python `re`, custom allowlist
  - Output Artifact: `backend/services/sql_sanitizer.py` with functions: `sanitize_sql(sql: str) -> str`, `detect_injection(sql: str) -> bool`, `is_safe_query(sql: str) -> tuple[bool, str]`
  - Definition of Done: `detect_injection("SELECT * FROM users; DROP TABLE users")` returns `True`; `detect_injection("SELECT * FROM users WHERE id = 1")` returns `False`; blocks: multi-statement queries, UNION-based injection attempts, comment-based injection (`--`, `/**/`), `LOAD_EXTENSION`, `ATTACH DATABASE`; 15+ Pytest tests covering OWASP SQL injection patterns all pass
  - Dependencies: Week 2 Task 3

- **Task 3: Implement connection pooling and concurrent database access**
  - Tools: SQLAlchemy `create_engine` with `pool_size`, `threading.Lock` for SQLite, Python `contextmanager`
  - Output Artifact: `backend/services/db_manager.py` with class `DatabaseManager` (methods: `get_connection(db_filename)`, `execute_query(db_filename, sql)`, `close_all()`)
  - Definition of Done: `DatabaseManager` maintains a dict of SQLite connections keyed by filename; thread-safe access via `threading.Lock` per database; connections auto-close after 5 minutes of inactivity (configurable via `DB_IDLE_TIMEOUT` env var); `execute_query` returns results within 50ms for simple SELECT on Chinook (benchmarked in test); Pytest test confirms concurrent access from 10 threads produces correct results without `OperationalError: database is locked`
  - Dependencies: Week 1 Tasks 1, 3

- **Task 4: Add request/response timing middleware and `/api/metrics` endpoint**
  - Tools: FastAPI middleware, Python `time.perf_counter`, `dataclasses`
  - Output Artifact: `backend/middleware/timing.py`, `backend/routers/metrics.py` with `GET /api/metrics`
  - Definition of Done: Every response includes `X-Response-Time-Ms` header; `GET /api/metrics` returns JSON with: `total_requests`, `avg_response_time_ms`, `p95_response_time_ms`, `requests_by_endpoint` (dict of path → count), `error_count`; metrics reset on server restart; Pytest test asserts header presence and metrics increment after requests
  - Dependencies: Week 2 Task 4

- **Task 5: Dockerize backend with docker-compose for local development**
  - Tools: Docker, `docker-compose`, Python 3.11-slim base image
  - Output Artifact: `backend/Dockerfile`, `docker-compose.yml` (root level, backend service + optional frontend service)
  - Definition of Done: `docker build -t nlsql-backend ./backend` succeeds; `docker-compose up backend` starts FastAPI on port 8000; `GET /health` returns 200 from container; `.sqlite` files persist via Docker volume mount (`./backend/db:/app/db`); container image size ≤ 500MB; `docker-compose down && docker-compose up` preserves uploaded databases
  - Dependencies: All prior backend work

### Team 3 (AI / Model) – Deliverables

- **Task 1: Launch QLoRA fine-tuning run on full dataset (Spider + BIRD + synthetic)**
  - Tools: Unsloth, PEFT, CRC A100 GPU (SLURM), `wandb`
  - Output Artifact: `ai/models/qwen-nlsql-v1/` (LoRA adapter weights), W&B run `qlora-v1-full-dataset`
  - Definition of Done: SLURM job `sbatch ai/slurm/train_full.sh` submits and runs for ≤ 8 hours on 1x A100; training loss decreases monotonically over 3 epochs (verified in W&B loss curve); final training loss < 0.5; LoRA adapter weights saved to `ai/models/qwen-nlsql-v1/adapter_model.safetensors`; W&B run logs: loss per step, learning rate schedule, GPU memory usage, throughput (samples/sec)
  - Dependencies: Week 3 Tasks 2, 3

- **Task 2: Evaluate fine-tuned model v1 on Spider dev set**
  - Tools: Python, `transformers`, `peft` (merge LoRA), CRC A100, `wandb`
  - Output Artifact: `ai/eval/results/finetuned_v1_spider.json`, W&B run `eval-finetuned-v1-spider`
  - Definition of Done: Load base Qwen model + LoRA adapter; run full Spider dev eval (1034 samples); `finetuned_v1_spider.json` contains per-sample predictions; EX and EM scores logged to W&B; comparison table in W&B: baseline vs. fine-tuned (overall and by difficulty); target: EX improvement ≥ 5% over zero-shot baseline
  - Dependencies: Task 1; Week 2 Tasks 3, 4

- **Task 3: Implement robustness evaluation (5 rephrasings per query)**
  - Tools: Python, Ollama or Groq API (for generating rephrasings), `json`
  - Output Artifact: `ai/eval/evaluate_robustness.py`, `ai/data/spider_dev_rephrasings.json` (50 Spider dev queries × 5 rephrasings = 250 total)
  - Definition of Done: `generate_rephrasings(question, n=5)` produces 5 semantically equivalent but syntactically different NL queries; `evaluate_robustness` computes: (1) per-query consistency (% of rephrasings producing correct SQL), (2) aggregate robustness score (mean consistency across all queries); results saved to `ai/eval/results/robustness_v1.json`; W&B table shows per-query breakdown
  - Dependencies: Task 1; Week 1 Task 1

- **Task 4: Expose model inference as a FastAPI microservice**
  - Tools: FastAPI, `transformers`, `peft`, `torch`, Uvicorn
  - Output Artifact: `ai/api/inference_server.py` with `POST /api/generate` endpoint accepting `{"prompt": str, "max_tokens": int}` and returning `{"sql": str, "tokens_used": int, "latency_ms": float}`; `ai/api/Dockerfile`
  - Definition of Done: `uvicorn ai.api.inference_server:app --port 8001` starts; `POST /api/generate {"prompt": "...", "max_tokens": 256}` returns generated SQL within 5 seconds on GPU; health check at `GET /health` returns model name and device; Docker container built and runs successfully; Pytest test confirms endpoint returns valid SQL for 3 test prompts
  - Dependencies: Week 2 Task 2; Task 1

- **Task 5: Conduct error analysis on baseline vs. fine-tuned predictions**
  - Tools: Python, `pandas`, Jupyter Notebook, `wandb` Tables
  - Output Artifact: `ai/notebooks/error_analysis_v1.ipynb`
  - Definition of Done: Notebook analyzes: (1) top 10 error categories (e.g., wrong table, wrong column, wrong JOIN, wrong aggregation, wrong WHERE clause), (2) confusion matrix of predicted vs. gold SQL structure types (SELECT/JOIN/GROUP BY/SUBQUERY), (3) difficulty-stratified accuracy (easy/medium/hard/extra), (4) 10 qualitative examples of failures with root cause annotations; all cells execute without errors; notebook committed to repo
  - Dependencies: Tasks 1, 2

---

## Week 5: March 29 – April 4

### Team 1 (Frontend) – Deliverables

- **Task 1: Implement multi-database session management in UI**
  - Tools: React Context API, `zustand` state management, shadcn/ui `Select` component
  - Output Artifact: `frontend/store/dbStore.ts` (zustand store), `frontend/components/DatabaseSelector.tsx`
  - Definition of Done: User can upload multiple `.sqlite`/`.csv` files; `DatabaseSelector` dropdown lists all uploaded databases; switching database triggers schema reload; active database name shown in header; query submissions use the selected database; zustand store persists selection across page navigation; unit test asserts store updates correctly on database switch
  - Dependencies: Week 2 Task 1 (FileUpload), Week 2 Task 2 (SchemaViewer)

- **Task 2: Add query result export functionality (CSV, JSON)**
  - Tools: `papaparse` (CSV export), native `JSON.stringify`, `Blob` API, shadcn/ui `DropdownMenu`
  - Output Artifact: `frontend/components/ExportButton.tsx`, `frontend/utils/export.ts`
  - Definition of Done: "Export" dropdown next to results table offers CSV and JSON options; CSV export produces valid file with headers matching column names; JSON export produces array of objects; files download with filename pattern `query_results_YYYYMMDD_HHMMSS.{csv,json}`; export disabled when no results present; unit test asserts CSV output matches expected format for 10-row mock data
  - Dependencies: Week 2 Task 4 (ResultsTable)

- **Task 3: Build SQL diff view for validation warnings**
  - Tools: `react-diff-viewer-continued`, React, shadcn/ui `Dialog`
  - Output Artifact: `frontend/components/SQLDiffView.tsx`
  - Definition of Done: When backend returns `validation_warnings` (e.g., column name corrected by `sqlglot`), a "View Changes" button appears; clicking opens a diff view showing original generated SQL vs. corrected SQL; additions highlighted in green, removals in red; diff view supports syntax highlighting; unit test asserts diff renders for a sample correction (e.g., `"employess"` → `"employees"`)
  - Dependencies: Team 2 Week 3 Task 2 (ambiguity detection)

- **Task 4: Implement toast notification system**
  - Tools: shadcn/ui `Toast`, `useToast` hook, React
  - Output Artifact: `frontend/components/ToastProvider.tsx` (wraps app), updated components to use `useToast`
  - Definition of Done: Toast notifications for: upload success (green), upload failure (red), query execution error (red with suggestion), rate limit exceeded (amber), copy-to-clipboard confirmation (blue); toasts auto-dismiss after 5 seconds; max 3 simultaneous toasts stacked vertically; unit test asserts toast appears and auto-dismisses
  - Dependencies: None

- **Task 5: Accessibility audit and ARIA compliance pass**
  - Tools: `@axe-core/react`, Lighthouse, manual screen reader testing (NVDA or VoiceOver)
  - Output Artifact: `frontend/reports/accessibility_audit.md`, updated components with ARIA attributes
  - Definition of Done: `axe-core` scan reports zero critical/serious violations; all interactive elements have `aria-label` or visible label; focus management correct for modal dialogs (trap focus, return focus on close); color contrast ≥ 4.5:1 for all text; `accessibility_audit.md` documents findings and fixes; Lighthouse accessibility ≥ 95
  - Dependencies: All prior frontend components

### Team 2 (Backend + Database) – Deliverables

- **Task 1: Implement query result caching with TTL**
  - Tools: Python `cachetools` (TTLCache), `hashlib` for cache key generation
  - Output Artifact: `backend/services/cache.py` with class `QueryCache` (methods: `get(key)`, `set(key, value, ttl)`, `invalidate(db_filename)`), updated `backend/services/orchestrator.py`
  - Definition of Done: Identical NL query + db_filename pair returns cached result (cache hit); cache key = `sha256(query + db_filename + schema_hash)`; TTL = 300 seconds (configurable via `CACHE_TTL` env var); cache invalidated on new file upload for that db_filename; `GET /api/metrics` reports `cache_hit_count` and `cache_miss_count`; Pytest test asserts: same query twice → second call < 5ms; upload invalidates cache
  - Dependencies: Week 3 Task 1 (orchestrator), Week 4 Task 4 (metrics)

- **Task 2: Add paginated query results endpoint**
  - Tools: FastAPI, Pydantic, SQL `LIMIT`/`OFFSET`
  - Output Artifact: `backend/routers/query.py` (updated), `backend/schemas.py` (add `PaginatedResponse` model with `page`, `page_size`, `total_rows`, `total_pages`, `results`)
  - Definition of Done: `POST /api/query` accepts optional `page` (default 1) and `page_size` (default 50, max 500) params; response includes pagination metadata; `total_rows` computed via `SELECT COUNT(*)` wrapper; `page` > `total_pages` returns empty results with correct metadata; Pytest tests for: page 1, last page, page beyond range, custom page_size
  - Dependencies: Week 4 Task 1

- **Task 3: Implement database file management endpoints**
  - Tools: FastAPI, Python `pathlib`, `os`
  - Output Artifact: `backend/routers/databases.py` with `GET /api/databases` (list all), `DELETE /api/databases/{filename}` (remove), `GET /api/databases/{filename}/info` (file size, table count, row counts)
  - Definition of Done: `GET /api/databases` returns `[{"filename": "chinook.sqlite", "size_bytes": 884736, "tables": 11, "uploaded_at": "2026-03-22T..."}]`; `DELETE` removes file and returns 204; `GET .../info` returns per-table row counts; deleting non-existent file returns 404; Pytest tests for all three endpoints pass
  - Dependencies: Week 1 Task 3

- **Task 4: Implement async background task for large file conversions**
  - Tools: FastAPI `BackgroundTasks`, Python `asyncio`, Pydantic
  - Output Artifact: `backend/services/background_converter.py`, updated `backend/routers/upload.py`, `backend/routers/tasks.py` with `GET /api/tasks/{task_id}`
  - Definition of Done: Files > 10MB trigger async conversion; `POST /api/upload` returns immediately with `{"task_id": uuid, "status": "processing"}`; `GET /api/tasks/{task_id}` returns `{"status": "processing|completed|failed", "progress_pct": int, "result": {...}}`; frontend can poll for completion; Pytest test with 15MB CSV fixture confirms async processing and status polling
  - Dependencies: Week 2 Task 1, Week 4 Task 3

- **Task 5: Write comprehensive API documentation with example requests**
  - Tools: FastAPI auto-generated OpenAPI, `backend/docs/api_examples.md`
  - Output Artifact: `backend/docs/api_examples.md` with curl examples for every endpoint, `backend/main.py` updated with OpenAPI metadata (title, description, version, tags)
  - Definition of Done: OpenAPI spec at `/openapi.json` includes descriptions for all endpoints, request/response schemas, and example values; `api_examples.md` has working `curl` commands for: upload, schema introspection, NL query, SQL execution, database management, metrics; each example includes expected response; all curl examples verified to work against running server
  - Dependencies: All prior backend endpoints

### Team 3 (AI / Model) – Deliverables

- **Task 1: Fine-tune model v2 with augmented dataset and adjusted hyperparameters**
  - Tools: Unsloth, PEFT (LoRA `r=32`, `lora_alpha=64`), CRC A100, `wandb`
  - Output Artifact: `ai/models/qwen-nlsql-v2/adapter_model.safetensors`, `ai/training/config_v2.yaml` (updated: `learning_rate=1e-4`, `epochs=5`, `batch_size=8`, `max_seq_length=3072`), W&B run `qlora-v2-augmented`
  - Definition of Done: Training completes on full augmented dataset (Spider + BIRD + 500 synthetic); final loss < 0.3; W&B comparison dashboard shows v1 vs. v2 training curves; adapter weights ≤ 200MB; training time logged in W&B; checkpoint saved every 1000 steps
  - Dependencies: Week 4 Task 1; Week 3 Task 2

- **Task 2: Evaluate model v2 on Spider dev set and compare to v1**
  - Tools: Python, `peft`, CRC A100, `wandb`
  - Output Artifact: `ai/eval/results/finetuned_v2_spider.json`, W&B comparison table `v1-vs-v2`
  - Definition of Done: Full Spider dev eval (1034 samples) for v2; W&B table compares: overall EX, overall EM, per-difficulty EX/EM for baseline, v1, v2; v2 EX improvement ≥ 3% over v1 (or documented root cause if not); `finetuned_v2_spider.json` committed to repo
  - Dependencies: Task 1

- **Task 3: Evaluate on BIRD dev set for cross-benchmark generalization**
  - Tools: Python, BIRD dev databases, CRC A100, `wandb`
  - Output Artifact: `ai/eval/results/finetuned_v2_bird.json`, W&B run `eval-v2-bird`
  - Definition of Done: BIRD dev set evaluated with v2 model; EX and EM computed; results broken down by database complexity (simple/moderate/challenging); comparison with Spider results to assess generalization; `finetuned_v2_bird.json` with per-sample results committed
  - Dependencies: Task 1; Week 1 Task 4

- **Task 4: Implement prompt variations for schema injection strategies**
  - Tools: Python, Jinja2, `ai/prompts/`
  - Output Artifact: `ai/prompts/nl_to_sql_ddl.j2` (full DDL), `ai/prompts/nl_to_sql_compact.j2` (table:columns shorthand), `ai/prompts/nl_to_sql_examples.j2` (with 5-shot examples), `ai/services/prompt_builder.py` (updated with `strategy` parameter)
  - Definition of Done: Three distinct prompt templates implemented; `build_prompt(question, schema, strategy="ddl"|"compact"|"examples")` produces correctly formatted prompts; comparative eval on 100 Spider dev samples: DDL vs. compact vs. examples strategy EX scores logged to W&B; best-performing strategy documented in `ai/prompts/README.md`
  - Dependencies: Week 2 Task 1

- **Task 5: Build model serving optimization benchmark**
  - Tools: Python, `torch`, `time`, `psutil`, `GPUtil`
  - Output Artifact: `ai/benchmarks/inference_benchmark.py`, `ai/benchmarks/results/inference_perf.json`
  - Definition of Done: Benchmark measures: (1) cold start time (model load), (2) warm inference latency (mean, p50, p95, p99 over 100 queries), (3) GPU memory usage (peak), (4) throughput (queries/sec); results for both 4-bit and 8-bit quantization logged; `inference_perf.json` contains all metrics; comparison table in W&B; target: p95 latency < 3 seconds on A100
  - Dependencies: Week 4 Task 4 (inference server)

---

## Week 6: April 5 – April 11

### Team 1 (Frontend) – Deliverables

- **Task 1: Implement real-time query status polling with progress indicator**
  - Tools: React, `setInterval` or `useSWR` with `refreshInterval`, shadcn/ui `Progress` component
  - Output Artifact: `frontend/hooks/useQueryStatus.ts`, updated `QueryInput.tsx`
  - Definition of Done: For long-running queries (> 2 seconds), UI shows: (1) animated progress bar, (2) elapsed time counter, (3) "Cancel" button (sends `DELETE /api/tasks/{task_id}`); polling interval 1 second; progress updates from backend `GET /api/tasks/{task_id}`; query completion triggers results display; unit test asserts polling starts after 2-second timeout and stops on completion
  - Dependencies: Team 2 Week 5 Task 4 (background tasks)

- **Task 2: Build multi-tab results workspace**
  - Tools: React, shadcn/ui `Tabs`, zustand state management
  - Output Artifact: `frontend/components/ResultsWorkspace.tsx`, `frontend/store/workspaceStore.ts`
  - Definition of Done: Each query result opens in a new tab (max 10 tabs); tabs show truncated NL query as label; active tab shows results table/chart; tabs closeable via X button; tab state persisted in zustand store; switching tabs instant (no re-fetch); unit test asserts tab creation, switching, and closing behavior
  - Dependencies: Week 2 Task 4, Week 4 Task 2

- **Task 3: Implement copy-to-clipboard for SQL and results**
  - Tools: `navigator.clipboard` API, React, shadcn/ui `Button` with icon
  - Output Artifact: `frontend/utils/clipboard.ts`, updated `SQLExplanation.tsx` and `ResultsTable.tsx`
  - Definition of Done: "Copy SQL" button on SQL explanation copies generated SQL; "Copy as CSV" button on results table copies tab-separated data with headers; "Copy as JSON" button copies results as JSON array; visual feedback (checkmark icon for 2 seconds) after copy; graceful fallback for browsers without clipboard API; unit tests for all three copy functions
  - Dependencies: Week 3 Task 4 (SQLExplanation)

- **Task 4: Performance optimization: code splitting and lazy loading**
  - Tools: Next.js `dynamic()` imports, React `Suspense`, `@next/bundle-analyzer`
  - Output Artifact: Updated component imports in `frontend/app/page.tsx`, `frontend/next.config.js` with bundle analyzer config, `frontend/reports/bundle_analysis.md`
  - Definition of Done: `ResultsChart`, `SQLDiffView`, `ShortcutsDialog` lazy-loaded with `dynamic()`; bundle analyzer report shows main JS bundle < 200KB gzipped; initial page load (Lighthouse Performance) ≥ 85; `bundle_analysis.md` documents bundle sizes before and after optimization with screenshots
  - Dependencies: All prior frontend components

- **Task 5: Write frontend integration tests covering all API interactions**
  - Tools: Jest, `msw` (Mock Service Worker) for API mocking, React Testing Library
  - Output Artifact: `frontend/__tests__/integration/api_integration.test.tsx`, `frontend/__tests__/mocks/handlers.ts` (MSW handlers)
  - Definition of Done: MSW handlers mock all backend endpoints (`/api/upload`, `/api/schema/*`, `/api/query`, `/api/execute`, `/api/databases`); integration tests cover: (1) upload → schema display flow, (2) query → results display flow, (3) error response → error display flow, (4) rate limit → toast notification flow; all tests pass; MSW handlers match current Pydantic schemas
  - Dependencies: All prior frontend + backend API contracts

### Team 2 (Backend + Database) – Deliverables

- **Task 1: Implement query explanation endpoint**
  - Tools: FastAPI, `sqlglot` (AST analysis), Python
  - Output Artifact: `backend/routers/explain.py` with `POST /api/explain` endpoint, `backend/services/sql_explainer.py`
  - Definition of Done: `POST /api/explain {"sql": "SELECT name, COUNT(*) FROM employees GROUP BY department"}` returns `{"explanation": "Retrieves employee names grouped by department with count per group", "tables_used": ["employees"], "operations": ["SELECT", "GROUP BY", "COUNT"], "complexity": "medium"}`; complexity levels: simple (1 table, no joins), medium (aggregation or 1 join), complex (subquery or 2+ joins); 10 Pytest tests covering each complexity level pass
  - Dependencies: Week 2 Task 3

- **Task 2: Add health check endpoint with dependency status**
  - Tools: FastAPI, `psutil`, Python `sqlite3`
  - Output Artifact: `backend/routers/health.py` (extended `GET /health`), returns `{"status": "ok", "uptime_seconds": int, "database_dir_accessible": bool, "databases_count": int, "ai_service_reachable": bool, "memory_usage_mb": float, "version": str}`
  - Definition of Done: `/health` checks: (1) `backend/db/` directory exists and is writable, (2) AI inference service responds at configured URL, (3) memory usage via `psutil`; returns HTTP 200 if all healthy, HTTP 503 if any dependency down; `version` reads from `backend/__version__.py`; Pytest test mocks AI service down → asserts 503 and `ai_service_reachable: false`
  - Dependencies: Week 4 Task 1

- **Task 3: Implement request validation middleware for all endpoints**
  - Tools: FastAPI `Depends`, Pydantic validators, custom exception handlers
  - Output Artifact: `backend/middleware/validation.py`, `backend/core/exceptions.py` (custom exception classes: `DatabaseNotFoundError`, `InvalidFileTypeError`, `SQLValidationError`, `AIServiceError`)
  - Definition of Done: All custom exceptions return structured JSON: `{"error": str, "error_code": str, "detail": dict | None, "request_id": str}`; `DatabaseNotFoundError` → HTTP 404; `InvalidFileTypeError` → HTTP 415; `SQLValidationError` → HTTP 422 with `detail` containing validation errors; `AIServiceError` → HTTP 502; global exception handler catches unhandled exceptions → HTTP 500 with sanitized message (no stack traces in production); Pytest tests for each exception type pass
  - Dependencies: Week 2 Task 4 (logging)

- **Task 4: Implement database usage analytics tracking**
  - Tools: FastAPI, Python `dataclasses`, `json`
  - Output Artifact: `backend/services/analytics.py` with class `UsageTracker`, `backend/routers/analytics.py` with `GET /api/analytics`
  - Definition of Done: Tracks per-database: query count, unique NL queries, most common tables queried, avg query latency, error count; `GET /api/analytics` returns full analytics; `GET /api/analytics/{db_filename}` returns per-database stats; data persisted to `backend/data/analytics.json` (survives server restart); Pytest test asserts counters increment after queries
  - Dependencies: Week 3 Task 1

- **Task 5: Load test backend with 50 concurrent users simulation**
  - Tools: `locust` load testing framework, Python
  - Output Artifact: `backend/tests/load/locustfile.py`, `backend/tests/load/results/load_test_report.md`
  - Definition of Done: Locust test simulates 50 concurrent users performing: file upload (10%), schema introspection (20%), NL query (50%), SQL execution (20%); test runs for 5 minutes; `load_test_report.md` documents: RPS achieved, p50/p95/p99 latency per endpoint, error rate, failure modes; target: ≥ 10 RPS with p95 < 2 seconds for `/api/query` (excluding AI inference time, using mocked AI); locust HTML report saved
  - Dependencies: All prior backend endpoints

### Team 3 (AI / Model) – Deliverables

- **Task 1: Implement few-shot example retrieval using TF-IDF similarity**
  - Tools: Python, `scikit-learn` (`TfidfVectorizer`, `cosine_similarity`), `json`
  - Output Artifact: `ai/services/example_retriever.py` with class `FewShotRetriever` (methods: `build_index(examples: list[dict])`, `retrieve(query: str, k: int = 3) -> list[dict]`)
  - Definition of Done: `FewShotRetriever` indexes NL questions from training data using TF-IDF; `retrieve("show employees in marketing")` returns 3 most similar NL-SQL pairs; retrieval latency < 50ms for 15,000-example index; retrieved examples improve prompt quality (verified by spot-checking 10 queries); Pytest tests assert correct k results returned and similarity scores are descending
  - Dependencies: Week 3 Task 2 (unified dataset)

- **Task 2: Integrate dynamic few-shot retrieval into prompt builder**
  - Tools: Python, Jinja2, `ai/services/example_retriever.py`
  - Output Artifact: `ai/prompts/nl_to_sql_dynamic.j2` (template with `{{few_shot_examples}}` block), updated `ai/services/prompt_builder.py` with `strategy="dynamic"`
  - Definition of Done: `build_prompt(question, schema, strategy="dynamic")` retrieves 3 similar examples and injects them into the prompt; prompt format: system instruction → schema DDL → 3 retrieved examples → user question; eval on 100 Spider dev samples shows EX ≥ static few-shot strategy; W&B comparison: static vs. dynamic few-shot EX/EM
  - Dependencies: Task 1; Week 5 Task 4

- **Task 3: Run full evaluation suite on v2 model with dynamic few-shot**
  - Tools: CRC A100, SLURM, Python, `wandb`
  - Output Artifact: `ai/eval/results/v2_dynamic_fewshot_spider.json`, `ai/eval/results/v2_dynamic_fewshot_bird.json`, W&B runs for both
  - Definition of Done: Full Spider dev (1034) and BIRD dev eval with dynamic few-shot prompting; results logged to W&B with comparison to all prior runs (baseline, v1, v2 static); best configuration identified and documented in `ai/eval/results/README.md`; aggregate results table: model × prompt strategy × dataset → EX, EM
  - Dependencies: Tasks 1, 2; Week 5 Tasks 1, 2

- **Task 4: Implement model output post-processing pipeline**
  - Tools: Python, `sqlglot`, `re`
  - Output Artifact: `ai/services/postprocessor.py` with functions: `extract_sql(raw_output: str) -> str`, `fix_common_errors(sql: str, schema: dict) -> str`, `normalize_sql(sql: str) -> str`
  - Definition of Done: `extract_sql` handles: markdown code blocks, explanation text before/after SQL, multiple SQL statements (takes first SELECT); `fix_common_errors` corrects: unquoted string literals, missing table aliases in JOINs, `GROUP BY` without all non-aggregated columns (via `sqlglot` rewrite); `normalize_sql` lowercases keywords, standardizes whitespace; 15+ Pytest tests covering each post-processing step pass
  - Dependencies: Week 2 Task 2

- **Task 5: Generate augmented rephrasings dataset for robustness training**
  - Tools: Groq API (Llama 3.1 70B for rephrasings), Python, `json`
  - Output Artifact: `ai/scripts/generate_rephrasings.py`, `ai/data/rephrasings_augment.jsonl` (2000 NL-SQL pairs: 400 base queries × 5 rephrasings)
  - Definition of Done: Each base query generates 5 rephrasings via Groq API with prompt: "Rephrase this database question 5 ways while preserving the exact meaning"; output format: `{"original": str, "rephrasings": [str], "sql": str, "db_id": str}`; manual review of 50 random rephrasings shows ≥ 95% semantic equivalence; script handles Groq rate limits with exponential backoff; reproducible with `--seed`
  - Dependencies: Week 3 Task 1

---

## Week 7: April 12 – April 18

### Team 1 (Frontend) – Deliverables

- **Task 1: Integrate frontend with AI inference service for end-to-end NL-to-SQL**
  - Tools: Next.js, `frontend/lib/api.ts`, React state management
  - Output Artifact: Updated `frontend/lib/api.ts` (add `generateSQL` function), updated `frontend/components/QueryInput.tsx` and `ResultsPanel.tsx`
  - Definition of Done: Full user flow works end-to-end: type NL query → submit → see loading → SQL displayed → results table populated → chart available if numeric; error states handled (AI timeout → retry button, validation error → suggestion shown); response latency displayed to user; tested with Chinook, Northwind, and a custom CSV-uploaded database; no console errors in browser DevTools
  - Dependencies: Team 2 Week 3 Task 1, Team 3 Week 4 Task 4

- **Task 2: Implement query comparison view (side-by-side results)**
  - Tools: React, shadcn/ui `ResizablePanelGroup`, `ResizablePanel`, zustand
  - Output Artifact: `frontend/components/ComparisonView.tsx`
  - Definition of Done: User can select two query result tabs and click "Compare"; opens side-by-side view with: left panel (query A results), right panel (query B results), diff highlights for differing values; panels resizable; comparison closeable; unit test asserts two-panel rendering with different datasets
  - Dependencies: Week 6 Task 2 (multi-tab workspace)

- **Task 3: Build onboarding tour for first-time users**
  - Tools: `driver.js` (lightweight tour library), React, shadcn/ui `Button`
  - Output Artifact: `frontend/components/OnboardingTour.tsx`, `frontend/hooks/useOnboarding.ts`
  - Definition of Done: On first visit (checked via `localStorage` flag), tour highlights: (1) file upload area, (2) schema viewer, (3) query input, (4) results area, (5) export button; each step has descriptive text; "Skip" and "Next" buttons; tour completion sets `localStorage` flag; "Restart Tour" option in settings; tour does not block UI interaction
  - Dependencies: All prior frontend components

- **Task 4: Implement frontend error boundary and crash reporting**
  - Tools: React Error Boundary, `frontend/components/ErrorBoundary.tsx`
  - Output Artifact: `frontend/components/ErrorBoundary.tsx`, `frontend/app/error.tsx` (Next.js error page), `frontend/app/global-error.tsx`
  - Definition of Done: Unhandled React errors caught by ErrorBoundary; fallback UI shows: "Something went wrong" message, error details in collapsible section, "Reload" button; `app/error.tsx` handles route-level errors; `global-error.tsx` handles root layout errors; error details logged to console with component stack; unit test triggers error in child component → asserts fallback renders
  - Dependencies: None

- **Task 5: Cross-browser testing and compatibility fixes**
  - Tools: Cypress, BrowserStack (or manual testing), Chrome, Firefox, Safari, Edge
  - Output Artifact: `frontend/reports/browser_compatibility.md`
  - Definition of Done: Full query flow tested on: Chrome 120+, Firefox 120+, Safari 17+, Edge 120+; `browser_compatibility.md` documents: (1) browsers tested with versions, (2) any rendering differences, (3) fixes applied (CSS prefixes, polyfills); no critical flow breakage on any browser; Cypress tests pass on Chrome and Firefox (via `cypress run --browser`)
  - Dependencies: All prior frontend work

### Team 2 (Backend + Database) – Deliverables

- **Task 1: Implement end-to-end integration tests with real AI service**
  - Tools: Pytest, `httpx`, FastAPI `TestClient`, real AI inference service
  - Output Artifact: `backend/tests/integration/test_e2e_query.py`, `backend/tests/integration/conftest.py`
  - Definition of Done: Integration tests run against FastAPI + real AI service (not mocked); test cases: (1) "List all albums" on Chinook → returns ≥ 1 row, (2) "Count employees by city" → returns aggregated results, (3) nonexistent table query → returns ambiguity suggestion, (4) invalid file → returns 404; tests marked with `@pytest.mark.integration` (skipped in CI, run manually); all 4 tests pass with real services running
  - Dependencies: Team 3 Week 4 Task 4 (inference server)

- **Task 2: Implement query timeout and circuit breaker for AI service**
  - Tools: `httpx` (timeout config), `tenacity` (retry with backoff), Python
  - Output Artifact: `backend/services/ai_client.py` (updated with timeout and retry logic), `backend/core/circuit_breaker.py`
  - Definition of Done: AI service calls timeout after 30 seconds (configurable via `AI_TIMEOUT_SECONDS` env var); on timeout, return HTTP 504 with `{"error": "AI service timed out"}`; retry up to 2 times with exponential backoff (1s, 2s); circuit breaker opens after 5 consecutive failures (returns 503 immediately for 60 seconds); Pytest tests: mock slow AI → assert 504; mock 5 failures → assert circuit opens → assert 503 on 6th call
  - Dependencies: Week 4 Task 1

- **Task 3: Benchmark database query execution performance**
  - Tools: Python `time.perf_counter`, `sqlite3`, `pytest-benchmark`
  - Output Artifact: `backend/tests/benchmarks/test_query_perf.py`, `backend/tests/benchmarks/results/query_benchmark.json`
  - Definition of Done: Benchmark suite measures: (1) simple SELECT (< 10ms target), (2) JOIN across 3 tables (< 50ms), (3) aggregation with GROUP BY (< 30ms), (4) 10,000-row table scan (< 100ms); run on Chinook + a synthetic 100K-row database; `query_benchmark.json` records mean, median, p95, p99 for each query type; all targets met; results committed to repo
  - Dependencies: Week 4 Task 3 (DatabaseManager)

- **Task 4: Implement WebSocket endpoint for streaming query progress**
  - Tools: FastAPI `WebSocket`, Python `asyncio`, `json`
  - Output Artifact: `backend/routers/ws.py` with `ws://localhost:8000/ws/query/{task_id}`
  - Definition of Done: WebSocket sends JSON messages: `{"stage": "schema_fetch|prompt_build|inference|validation|execution", "progress_pct": int, "message": str}`; client connects, receives stage updates in real-time; connection closes on completion with final result; connection closes with error message on failure; Pytest test using `websockets` library asserts message sequence for successful query
  - Dependencies: Week 5 Task 4

- **Task 5: Security audit: input sanitization and file upload safety**
  - Tools: Python, `python-magic` (file type verification), `pathlib`
  - Output Artifact: `backend/services/file_validator.py`, `backend/tests/security/test_upload_security.py`, `backend/reports/security_audit.md`
  - Definition of Done: File upload validates: (1) MIME type matches extension (via `python-magic`), (2) file size ≤ 50MB (configurable via `MAX_UPLOAD_SIZE_MB`), (3) filename sanitized (no path traversal: `../`, null bytes), (4) upload directory is not world-writable; `security_audit.md` documents: attack vectors tested, mitigations implemented, remaining risks; 10+ security-focused Pytest tests pass (path traversal, oversized file, wrong MIME type, null byte injection)
  - Dependencies: Week 1 Task 3

### Team 3 (AI / Model) – Deliverables

- **Task 1: Fine-tune model v3 with rephrasings-augmented dataset**
  - Tools: Unsloth, PEFT (LoRA `r=32`), CRC A100, `wandb`
  - Output Artifact: `ai/models/qwen-nlsql-v3/adapter_model.safetensors`, `ai/training/config_v3.yaml`, W&B run `qlora-v3-robust`
  - Definition of Done: Training dataset: Spider + BIRD + synthetic + rephrasings augmentation (≥ 17,000 examples); training completes in ≤ 10 hours; final loss < 0.25; W&B comparison: v1 vs. v2 vs. v3 loss curves; adapter weights saved and committed
  - Dependencies: Week 6 Task 5 (rephrasings dataset)

- **Task 2: Comprehensive evaluation of v3 on all benchmarks**
  - Tools: CRC A100, Python, `wandb`
  - Output Artifact: `ai/eval/results/v3_spider.json`, `ai/eval/results/v3_bird.json`, `ai/eval/results/v3_robustness.json`, W&B dashboard `model-comparison-v3`
  - Definition of Done: v3 evaluated on: (1) Spider dev full, (2) BIRD dev full, (3) robustness set (50 queries × 5 rephrasings); W&B dashboard shows: v3 vs. v2 vs. v1 vs. baseline for all metrics; robustness score (consistency across rephrasings) ≥ 80%; per-difficulty breakdown for Spider; best model version identified and documented
  - Dependencies: Task 1

- **Task 3: Hallucination detection and mitigation testing**
  - Tools: Python, `sqlglot`, custom test suite
  - Output Artifact: `ai/eval/hallucination_tests.py`, `ai/eval/results/hallucination_report.json`
  - Definition of Done: Test suite with 50 adversarial queries designed to trigger hallucinations: (1) queries about nonexistent tables (10 cases), (2) queries with plausible but wrong column names (10), (3) ambiguous aggregations (10), (4) cross-table queries with no valid join path (10), (5) queries requiring domain knowledge not in schema (10); `hallucination_report.json` records: per-case predicted SQL, whether hallucination detected (invalid table/column), hallucination rate; target: hallucination rate < 15% with post-processing; results logged to W&B
  - Dependencies: Week 6 Task 4 (post-processor); Task 1

- **Task 4: Implement model A/B testing framework**
  - Tools: Python, FastAPI, `random`, `wandb`
  - Output Artifact: `ai/services/ab_testing.py` with class `ModelSelector` (methods: `select_model(request_id: str) -> str`, `log_result(request_id, model_version, metrics)`), updated `ai/api/inference_server.py`
  - Definition of Done: `ModelSelector` randomly routes 50% of requests to v2 and 50% to v3; routing decision logged with `request_id`; per-model metrics tracked: latency, EX accuracy (when gold available), user feedback (if collected); `GET /api/ab_status` returns current allocation and accumulated metrics; Pytest test asserts approximately 50/50 split over 100 requests (within 40-60 range)
  - Dependencies: Week 4 Task 4; Tasks 1, 2

- **Task 5: Optimize inference latency via model compilation and caching**
  - Tools: `torch.compile()`, KV-cache optimization, `transformers` `GenerationConfig`
  - Output Artifact: `ai/services/inference_optimized.py`, `ai/benchmarks/results/optimization_perf.json`
  - Definition of Done: Compare latency: (1) baseline inference, (2) `torch.compile(mode="reduce-overhead")`, (3) with KV-cache reuse for same-schema queries; benchmark 100 queries for each config; `optimization_perf.json` records: p50, p95 latency and GPU memory for each config; target: ≥ 20% p95 latency reduction from baseline; best config documented and deployed to inference server
  - Dependencies: Week 5 Task 5

---

## Week 8: April 19 – April 25

### Team 1 (Frontend) – Deliverables

- **Task 1: Implement WebSocket client for real-time query progress**
  - Tools: React, native `WebSocket` API, zustand store
  - Output Artifact: `frontend/hooks/useWebSocket.ts`, updated `QueryInput.tsx` with real-time progress stages
  - Definition of Done: On query submission, frontend opens WebSocket to `ws://backend/ws/query/{task_id}`; progress bar updates per stage (schema_fetch → prompt_build → inference → validation → execution); each stage shows descriptive text; connection error gracefully falls back to HTTP polling; WebSocket disconnects on component unmount; unit test mocks WebSocket messages → asserts stage transitions
  - Dependencies: Team 2 Week 7 Task 4

- **Task 2: Build admin dashboard for monitoring query analytics**
  - Tools: React, `recharts`, shadcn/ui `Card`, `Table`, route `/admin`
  - Output Artifact: `frontend/app/admin/page.tsx`, `frontend/components/admin/QueryAnalytics.tsx`, `frontend/components/admin/SystemHealth.tsx`
  - Definition of Done: `/admin` page shows: (1) total queries chart (line, last 7 days), (2) queries per database (bar chart), (3) avg latency by endpoint (table), (4) error rate percentage, (5) system health status from `GET /health`; data fetched from `GET /api/analytics` and `GET /api/metrics`; auto-refreshes every 30 seconds; accessible only via direct URL (no nav link); unit test asserts charts render with mock data
  - Dependencies: Team 2 Week 5 Task 4 (analytics), Week 6 Task 2 (health)

- **Task 3: Implement query result pinning and annotations**
  - Tools: React, `localStorage`, shadcn/ui `Popover`, `Textarea`
  - Output Artifact: `frontend/components/PinnedResults.tsx`, `frontend/hooks/usePinnedResults.ts`
  - Definition of Done: Users can "pin" query results (saves NL query, SQL, results snapshot to localStorage); pinned results accessible from sidebar section; each pin supports a text annotation (e.g., "This was the correct query for monthly sales"); max 20 pins with FIFO eviction; "Unpin" button removes entry; pinned data includes timestamp; unit test asserts pin/unpin/annotation CRUD operations
  - Dependencies: Week 6 Task 2

- **Task 4: Performance profiling and optimization of ResultsTable for large datasets**
  - Tools: `@tanstack/react-virtual`, React Profiler, Chrome DevTools Performance tab
  - Output Artifact: Updated `frontend/components/ResultsTable.tsx` with virtualization, `frontend/reports/perf_profile.md`
  - Definition of Done: ResultsTable handles 10,000 rows without frame drops (≥ 30fps scroll); virtual scroll renders only visible rows (50-row window); `perf_profile.md` documents: (1) before/after render time for 10K rows, (2) memory usage before/after, (3) scroll FPS measurement; target: initial render < 200ms for 10K rows; sorting 10K rows < 500ms
  - Dependencies: Week 2 Task 4

- **Task 5: End-to-end Cypress test suite covering all major user flows**
  - Tools: Cypress, `cypress-file-upload`, running backend + AI service
  - Output Artifact: `frontend/cypress/e2e/full_suite.cy.ts` with test cases for: upload flow, query flow, error handling, history, export, schema viewer, dark mode, keyboard shortcuts
  - Definition of Done: 15+ Cypress test cases covering all major features; tests run against real backend (with mocked AI for speed); test suite completes in < 5 minutes; all tests pass in headless mode; added to CI pipeline with `cypress run` step; test results report generated
  - Dependencies: All prior frontend work

### Team 2 (Backend + Database) – Deliverables

- **Task 1: Implement graceful shutdown and connection cleanup**
  - Tools: FastAPI `@app.on_event("shutdown")`, Python `signal`, `atexit`
  - Output Artifact: `backend/core/lifecycle.py`, updated `backend/main.py`
  - Definition of Done: On SIGTERM/SIGINT: (1) stop accepting new requests, (2) wait up to 30 seconds for in-flight requests to complete, (3) close all SQLite connections via `DatabaseManager.close_all()`, (4) flush analytics data to `analytics.json`, (5) log shutdown completion; Pytest test: start server → send request → send SIGTERM → assert response completes and connections closed
  - Dependencies: Week 4 Task 3, Week 6 Task 4

- **Task 2: Implement database backup and snapshot endpoint**
  - Tools: FastAPI, Python `shutil`, `zipfile`, `pathlib`
  - Output Artifact: `backend/routers/databases.py` (extended with `POST /api/databases/{filename}/backup`), `backend/services/backup.py`
  - Definition of Done: `POST /api/databases/chinook.sqlite/backup` creates `backend/backups/chinook_20260419_143000.sqlite`; `GET /api/databases/{filename}/backups` lists all backups with timestamps and sizes; `POST /api/databases/{filename}/restore/{backup_id}` restores from backup; max 5 backups per database (oldest deleted); Pytest tests for create, list, restore, and max-limit eviction
  - Dependencies: Week 5 Task 3

- **Task 3: Stress test SQL execution with large datasets**
  - Tools: Python, `sqlite3`, `faker` (synthetic data generation), `pytest-benchmark`
  - Output Artifact: `backend/tests/benchmarks/test_large_dataset.py`, `backend/tests/fixtures/large_test.sqlite` (100K rows), `backend/tests/benchmarks/results/large_dataset_benchmark.json`
  - Definition of Done: Generate synthetic SQLite DB with: `users` (100K rows), `orders` (500K rows), `products` (10K rows); benchmark queries: (1) simple SELECT with WHERE (< 50ms), (2) 3-table JOIN (< 200ms), (3) GROUP BY with HAVING (< 100ms), (4) subquery (< 150ms), (5) LIKE pattern search (< 100ms); all benchmarks meet targets; results in `large_dataset_benchmark.json`
  - Dependencies: Week 7 Task 3

- **Task 4: Implement structured error logging to file with rotation**
  - Tools: Python `logging`, `logging.handlers.RotatingFileHandler`, `structlog`
  - Output Artifact: Updated `backend/core/logger.py`, log output to `backend/logs/app.log`
  - Definition of Done: JSON-structured logs written to `backend/logs/app.log`; log rotation: max 10MB per file, keep 5 rotated files; log levels: DEBUG in dev (`LOG_LEVEL=debug`), INFO in production; each log entry includes: timestamp, level, request_id, message, extra context; errors include stack trace; Pytest test asserts log file created and rotation triggers at 10MB
  - Dependencies: Week 2 Task 4

- **Task 5: API versioning strategy implementation**
  - Tools: FastAPI `APIRouter` with prefix, Pydantic
  - Output Artifact: `backend/api/v1/` directory with all existing routers moved under `/api/v1/` prefix; `backend/main.py` mounts versioned router
  - Definition of Done: All endpoints accessible at `/api/v1/query`, `/api/v1/upload`, etc.; legacy `/api/query` redirects to `/api/v1/query` with HTTP 308; OpenAPI docs at `/docs` show v1-prefixed endpoints; `backend/api/v1/__init__.py` includes all routers; all existing Pytest tests updated to use `/api/v1/` paths and pass
  - Dependencies: All prior backend routers

### Team 3 (AI / Model) – Deliverables

- **Task 1: Merge LoRA adapters into base model for faster inference**
  - Tools: `peft` (`merge_and_unload`), `transformers`, `safetensors`
  - Output Artifact: `ai/models/qwen-nlsql-v3-merged/` (full merged model weights in safetensors format)
  - Definition of Done: `merge_model.py` loads base Qwen 2.5 7B + v3 LoRA adapter → calls `model.merge_and_unload()` → saves merged weights to `ai/models/qwen-nlsql-v3-merged/`; verify merged model produces identical output to adapter model on 10 test queries (exact token match); inference latency ≤ adapter-based inference; model loadable without `peft` library
  - Dependencies: Week 7 Task 1

- **Task 2: Quantize merged model to GGUF format for CPU/edge deployment**
  - Tools: `llama.cpp` (`convert.py`, `quantize`), Python
  - Output Artifact: `ai/models/qwen-nlsql-v3.Q4_K_M.gguf`, `ai/scripts/convert_to_gguf.sh`
  - Definition of Done: Merged model converted to GGUF format; Q4_K_M quantization applied; GGUF file size ≤ 5GB; inference via `llama-cpp-python` produces valid SQL on 10 test queries; EX accuracy on 100 Spider dev samples within 2% of full-precision model; latency benchmark: CPU inference on 8-core machine < 15 seconds per query
  - Dependencies: Task 1

- **Task 3: Build comprehensive model evaluation report notebook**
  - Tools: Jupyter, `pandas`, `matplotlib`, `seaborn`, `wandb` API
  - Output Artifact: `ai/notebooks/model_evaluation_report.ipynb`
  - Definition of Done: Notebook contains: (1) training curves for all versions (v1, v2, v3), (2) EX/EM comparison table across all models × datasets × prompt strategies, (3) robustness score comparison, (4) hallucination rate comparison, (5) latency vs. accuracy trade-off scatter plot, (6) per-difficulty performance radar chart, (7) top 10 improvement examples (baseline wrong → v3 correct), (8) top 10 remaining failures with analysis; all cells execute without errors; notebook exported to PDF
  - Dependencies: All prior evaluation results

- **Task 4: Implement confidence scoring for generated SQL**
  - Tools: Python, `torch` (log probabilities), `transformers`
  - Output Artifact: `ai/services/confidence_scorer.py` with function `compute_confidence(model, tokenizer, prompt, generated_sql) -> float`
  - Definition of Done: Confidence score = mean token log probability of generated SQL, normalized to [0.0, 1.0]; high-confidence (> 0.8) queries have ≥ 90% EX accuracy on 100-sample test; low-confidence (< 0.5) queries have ≤ 50% EX accuracy; confidence score returned in inference API response; W&B plot: confidence vs. actual accuracy (scatter + calibration curve); Pytest test asserts score in valid range
  - Dependencies: Week 2 Task 2

- **Task 5: Load test AI inference service at target throughput**
  - Tools: `locust`, Python, CRC GPU node
  - Output Artifact: `ai/tests/load/locustfile.py`, `ai/tests/load/results/inference_load_report.md`
  - Definition of Done: Locust test sends concurrent NL-to-SQL requests to inference server; test configurations: 1, 5, 10, 20 concurrent users; test duration: 5 minutes per config; `inference_load_report.md` documents: (1) RPS achieved per concurrency level, (2) p50/p95/p99 latency, (3) GPU utilization, (4) memory usage, (5) error rate, (6) throughput ceiling; target: ≥ 2 RPS sustained at 10 concurrent users on single A100
  - Dependencies: Week 4 Task 4; Week 7 Task 5

---

## Week 9: April 26 – May 2

### Team 1 (Frontend) – Deliverables

- **Task 1: Implement natural language feedback loop ("This SQL is wrong")**
  - Tools: React, shadcn/ui `Dialog`, `Textarea`, `RadioGroup`, FastAPI integration
  - Output Artifact: `frontend/components/FeedbackDialog.tsx`, `frontend/hooks/useFeedback.ts`
  - Definition of Done: After viewing results, user can click "Report Issue" → dialog with: (1) radio group: "Wrong results", "Wrong table", "Wrong columns", "Other", (2) text area for correction, (3) optional correct SQL input; feedback sent via `POST /api/feedback` with `{query, generated_sql, feedback_type, correction, db_filename}`; confirmation toast on submit; unit test asserts dialog fields and submission payload
  - Dependencies: Team 2 feedback endpoint (cross-team)

- **Task 2: Build presentation-ready demo mode**
  - Tools: React, shadcn/ui `Switch`, custom hook, pre-loaded demo database
  - Output Artifact: `frontend/components/DemoMode.tsx`, `frontend/hooks/useDemoMode.ts`, `frontend/fixtures/demo_chinook.sqlite`
  - Definition of Done: "Demo Mode" toggle pre-loads Chinook database and auto-populates 5 example queries in a sidebar carousel: (1) "Show all albums by AC/DC", (2) "Count employees by city", (3) "Top 10 longest tracks", (4) "Total sales by country", (5) "Artists with more than 5 albums"; clicking example fills query input and auto-submits; demo mode disables file upload; visual banner "Demo Mode" shown; toggle stored in localStorage
  - Dependencies: All prior frontend components

- **Task 3: Implement print-friendly view for query results**
  - Tools: CSS `@media print`, React, `window.print()`
  - Output Artifact: `frontend/components/PrintView.tsx`, `frontend/styles/print.css`
  - Definition of Done: "Print Results" button generates print-optimized layout: NL query as header, generated SQL in monospace block, results table with proper page breaks, timestamp and database name in footer; hidden elements in print: navigation, query input, upload area; `@media print` rules in `print.css`; tested via Chrome print preview (no clipped content, readable font sizes); unit test asserts print-specific CSS classes applied
  - Dependencies: Week 2 Task 4

- **Task 4: Final UI polish pass: animations, micro-interactions, visual consistency**
  - Tools: `framer-motion` (animations), Tailwind CSS, shadcn/ui
  - Output Artifact: Updated components with animations, `frontend/lib/animations.ts`
  - Definition of Done: Animations added: (1) results table fade-in on load, (2) schema accordion expand/collapse slide, (3) toast slide-in from top-right, (4) query submit button pulse on hover, (5) skeleton shimmer effect; all animations respect `prefers-reduced-motion` media query; animation durations ≤ 300ms (no sluggish feel); Lighthouse Performance score ≥ 85 with animations enabled
  - Dependencies: All prior frontend components

- **Task 5: Generate Lighthouse CI report and document all metrics**
  - Tools: `@lhci/cli`, GitHub Actions, Lighthouse
  - Output Artifact: `.github/workflows/lighthouse-ci.yml`, `frontend/reports/lighthouse_final.md`
  - Definition of Done: Lighthouse CI runs on every PR; `lighthouse_final.md` documents final scores: Performance ≥ 85, Accessibility ≥ 95, Best Practices ≥ 90, SEO ≥ 90; scores for both mobile and desktop viewports; comparison table: Week 3 scores vs. final scores; all metrics above thresholds; CI fails PR if any metric drops below threshold
  - Dependencies: All prior frontend work

### Team 2 (Backend + Database) – Deliverables

- **Task 1: Implement user feedback collection endpoint**
  - Tools: FastAPI, Pydantic, `json`, Python
  - Output Artifact: `backend/routers/feedback.py` with `POST /api/feedback`, `backend/services/feedback_store.py`
  - Definition of Done: `POST /api/feedback {"query": "...", "generated_sql": "...", "feedback_type": "wrong_results", "correction": "...", "db_filename": "..."}` stores feedback to `backend/data/feedback.jsonl` (append-only); `GET /api/feedback` returns all feedback entries (paginated); `GET /api/feedback/stats` returns: total count, count by type, most common error type; each entry timestamped with `request_id`; Pytest tests for submit, list, and stats endpoints
  - Dependencies: None

- **Task 2: Implement end-to-end latency benchmarking for full query pipeline**
  - Tools: Python `time.perf_counter`, `pytest-benchmark`, FastAPI
  - Output Artifact: `backend/tests/benchmarks/test_pipeline_latency.py`, `backend/tests/benchmarks/results/pipeline_benchmark.json`
  - Definition of Done: Benchmark measures total latency and per-stage breakdown: (1) schema introspection, (2) prompt building, (3) AI inference, (4) SQL validation, (5) SQL execution; tested on 3 query complexity levels (simple, medium, complex) × 3 database sizes (small/medium/large); `pipeline_benchmark.json` records: per-stage mean/p95, total mean/p95; target: total p95 < 5 seconds (excluding AI inference); results visualized in table
  - Dependencies: All prior backend services

- **Task 3: Failure mode testing: network partitions and service unavailability**
  - Tools: Pytest, `unittest.mock`, `httpx`, `toxiproxy` (optional)
  - Output Artifact: `backend/tests/resilience/test_failure_modes.py`
  - Definition of Done: Test scenarios: (1) AI service unreachable → returns 502 with user-friendly error, (2) AI service slow (10s+) → timeout and 504, (3) SQLite database file corrupted → returns 500 with `"Database file is corrupted"`, (4) disk full → upload returns 507 with `"Insufficient storage"`, (5) concurrent requests to same DB → no deadlock (completes within 10s); all 5 tests pass; each test cleans up after itself
  - Dependencies: Week 7 Task 2

- **Task 4: Implement configuration management via environment variables**
  - Tools: `pydantic-settings`, Python, `.env` file
  - Output Artifact: `backend/core/config.py` with class `Settings(BaseSettings)`, `backend/.env.example`
  - Definition of Done: All configurable values managed via `Settings`: `AI_SERVICE_URL`, `AI_TIMEOUT_SECONDS`, `MAX_UPLOAD_SIZE_MB`, `CACHE_TTL`, `DB_IDLE_TIMEOUT`, `ALLOWED_ORIGINS`, `LOG_LEVEL`, `RATE_LIMIT_PER_MINUTE`; `.env.example` documents all variables with defaults and descriptions; `Settings` validates types (int, str, list) and raises clear error on invalid config; Pytest test loads `.env.example` → asserts all defaults parse correctly
  - Dependencies: All prior backend services

- **Task 5: Generate OpenAPI client SDK for frontend consumption**
  - Tools: `openapi-generator-cli`, FastAPI OpenAPI spec, TypeScript
  - Output Artifact: `frontend/lib/generated-api/` (TypeScript client), `scripts/generate-api-client.sh`
  - Definition of Done: `generate-api-client.sh` downloads OpenAPI spec from `/openapi.json` and generates TypeScript client with typed request/response interfaces; generated client replaces manual `api.ts` functions; all frontend API calls use generated client; generated types match Pydantic schemas; script added to CI (regenerate on backend changes); frontend builds with generated client
  - Dependencies: All prior backend endpoints

### Team 3 (AI / Model) – Deliverables

- **Task 1: Fine-tune model v4 incorporating feedback data and error patterns**
  - Tools: Unsloth, PEFT, CRC A100, `wandb`
  - Output Artifact: `ai/models/qwen-nlsql-v4/adapter_model.safetensors`, `ai/training/config_v4.yaml`, W&B run `qlora-v4-feedback`
  - Definition of Done: Training data augmented with: hard-negative mining from v3 errors (queries v3 got wrong → correct SQL as training examples), rephrasings dataset; total training examples ≥ 20,000; training completes ≤ 10 hours; final loss < 0.2; W&B shows v4 vs. v3 comparison; adapter saved
  - Dependencies: Week 8 Task 3 (evaluation report); Week 7 Task 1

- **Task 2: Final comprehensive evaluation of v4 (all benchmarks)**
  - Tools: CRC A100, Python, `wandb`
  - Output Artifact: `ai/eval/results/v4_final/` directory containing: `spider.json`, `bird.json`, `robustness.json`, `hallucination.json`, `confidence_calibration.json`; W&B dashboard `final-eval-v4`
  - Definition of Done: v4 evaluated on all benchmarks; target metrics: Spider EX ≥ 65%, BIRD EX ≥ 55%, robustness ≥ 85%, hallucination rate < 10%; all results logged to W&B with comparison to all prior versions; `ai/eval/results/README.md` updated with final numbers; if targets not met, documented with root cause analysis
  - Dependencies: Task 1

- **Task 3: Build model selection recommendation engine**
  - Tools: Python, `pandas`, statistical analysis
  - Output Artifact: `ai/analysis/model_recommendation.py`, `ai/analysis/recommendation_report.md`
  - Definition of Done: Script analyzes all evaluation results and recommends best model version for deployment based on: (1) overall EX accuracy, (2) robustness, (3) hallucination rate, (4) inference latency, (5) model size; `recommendation_report.md` contains: comparison matrix (all versions × all metrics), Pareto frontier analysis, final recommendation with justification; recommended model tagged in W&B
  - Dependencies: Task 2

- **Task 4: Implement model warm-up and health monitoring for inference server**
  - Tools: FastAPI, `torch`, Python `threading`, `psutil`, `GPUtil`
  - Output Artifact: Updated `ai/api/inference_server.py` with warm-up on startup, `GET /api/model/status`
  - Definition of Done: On server start, model loads and runs 3 warm-up queries (logs latency); `GET /api/model/status` returns: `{"model_version": "v4", "loaded": true, "gpu_memory_used_mb": int, "gpu_utilization_pct": float, "avg_latency_ms": float, "total_queries_served": int, "uptime_seconds": int}`; health check fails if GPU memory > 90% or avg latency > 10 seconds; Pytest test asserts warm-up completes and status endpoint returns valid data
  - Dependencies: Week 4 Task 4

- **Task 5: Create reproducibility package for all experiments**
  - Tools: Python, `wandb` (export), `json`, Markdown
  - Output Artifact: `ai/reproducibility/` containing: `requirements.txt` (pinned versions), `data_checksums.json` (SHA256 of all training/eval data files), `training_commands.md` (exact SLURM commands for each version), `wandb_run_ids.json` (mapping of version → W&B run IDs), `README.md` (reproduction instructions)
  - Definition of Done: A new team member can reproduce v4 training from scratch using only files in `ai/reproducibility/`; `data_checksums.json` verified against actual files (all match); `training_commands.md` contains copy-pasteable SLURM commands; `README.md` includes: prerequisites, step-by-step instructions, expected results (with tolerance ranges); reviewed by ≥ 1 team member
  - Dependencies: All prior AI work

---

## Week 10: May 3 – May 9

### Team 1 (Frontend) – Deliverables

- **Task 1: Implement server-side rendering optimization for initial page load**
  - Tools: Next.js App Router, React Server Components, `next/dynamic`
  - Output Artifact: Updated `frontend/app/page.tsx` (server component for initial data), `frontend/app/loading.tsx`
  - Definition of Done: Initial page load fetches database list server-side (no client-side loading spinner for initial data); `loading.tsx` provides instant skeleton while page hydrates; Time to First Byte (TTFB) < 200ms; Largest Contentful Paint (LCP) < 1.5 seconds; measured via Lighthouse in production build (`npm run build && npm start`)
  - Dependencies: All prior frontend work

- **Task 2: Implement PWA support for offline schema viewing**
  - Tools: `next-pwa`, Service Worker, `workbox`
  - Output Artifact: `frontend/next.config.js` (updated with PWA config), `frontend/public/manifest.json`, `frontend/public/sw.js`
  - Definition of Done: App installable as PWA on Chrome/Edge; app icon and splash screen configured in `manifest.json`; service worker caches: static assets, last-loaded schema, query history; offline mode shows cached schema and history (query submission disabled with "Offline" badge); Lighthouse PWA score ≥ 90
  - Dependencies: All prior frontend work

- **Task 3: Build deployment preview with Vercel**
  - Tools: Vercel CLI, `vercel.json`, GitHub integration
  - Output Artifact: `vercel.json` (build config, rewrites for API proxy), Vercel project linked to GitHub repo
  - Definition of Done: `vercel deploy` creates preview deployment; every PR gets automatic preview URL; `vercel.json` configures: (1) `/api/*` rewrites to backend service URL (env var `BACKEND_URL`), (2) build command `npm run build`, (3) output directory `.next`; preview deployment accessible and functional with live backend; deployment URL shared in PR comment via Vercel GitHub integration
  - Dependencies: All prior frontend work

- **Task 4: Create user documentation site with usage examples**
  - Tools: Next.js, Markdown, `next-mdx-remote`
  - Output Artifact: `frontend/app/docs/page.tsx`, `frontend/content/docs/` directory with: `getting-started.md`, `uploading-data.md`, `writing-queries.md`, `understanding-results.md`, `keyboard-shortcuts.md`
  - Definition of Done: `/docs` page renders documentation with sidebar navigation; each doc page has: title, description, step-by-step instructions with screenshots, example queries; search functionality within docs (client-side full-text search); docs build without errors; all internal links valid
  - Dependencies: All prior frontend features

- **Task 5: Final frontend test coverage report**
  - Tools: Jest, `--coverage` flag, Istanbul
  - Output Artifact: `frontend/reports/coverage_report.md`, `frontend/coverage/lcov-report/index.html`
  - Definition of Done: `npm run test -- --coverage` generates report; target coverage: ≥ 80% line coverage, ≥ 75% branch coverage for `components/` and `hooks/`; `coverage_report.md` lists: per-file coverage, uncovered lines, overall statistics; any files below 60% coverage identified with remediation plan; coverage report added to CI (visible in PR checks)
  - Dependencies: All prior frontend tests

### Team 2 (Backend + Database) – Deliverables

- **Task 1: Dockerize full application stack with docker-compose**
  - Tools: Docker, `docker-compose`, multi-stage builds
  - Output Artifact: `docker-compose.yml` (updated: frontend, backend, AI inference services), `frontend/Dockerfile`, `ai/api/Dockerfile`
  - Definition of Done: `docker-compose up` starts all 3 services: frontend (port 3000), backend (port 8000), AI inference (port 8001); services communicate via Docker network; health checks configured for all services; volumes persist database files and logs; `docker-compose down && docker-compose up` preserves state; total image sizes: frontend ≤ 300MB, backend ≤ 500MB, AI ≤ 10GB (includes model); documented in `docs/deployment.md`
  - Dependencies: Week 4 Task 5; Team 3 Week 4 Task 4

- **Task 2: Implement production configuration and security hardening**
  - Tools: FastAPI, `uvicorn` production settings, Python
  - Output Artifact: `backend/core/production.py`, updated `backend/Dockerfile` (production stage)
  - Definition of Done: Production config: (1) `uvicorn --workers 4 --limit-concurrency 100`, (2) CORS restricted to deployment domain, (3) rate limiting increased to 60 req/min, (4) debug mode disabled, (5) request body size limit 50MB, (6) HTTPS enforcement via `X-Forwarded-Proto` header check; security headers added: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`; Pytest test asserts security headers present
  - Dependencies: Week 3 Task 3, Week 9 Task 4

- **Task 3: Build cost estimation model for inference**
  - Tools: Python, `pandas`, GPU pricing data
  - Output Artifact: `backend/analysis/cost_model.py`, `docs/cost_analysis.md`
  - Definition of Done: `cost_model.py` calculates: (1) cost per query (GPU time × hourly rate), (2) monthly cost projections for: 100, 1,000, 10,000 queries/day, (3) comparison: CRC (free) vs. Colab Pro ($10/mo) vs. RunPod ($0.40/hr) vs. Lambda Labs ($1.20/hr); `cost_analysis.md` contains: pricing table, break-even analysis, recommendation for each usage tier; calculations verified manually for 3 scenarios
  - Dependencies: Team 3 Week 8 Task 5

- **Task 4: Implement monitoring dashboard data endpoints**
  - Tools: FastAPI, Python `psutil`, `GPUtil` (if GPU available)
  - Output Artifact: `backend/routers/monitoring.py` with `GET /api/monitoring/system` and `GET /api/monitoring/queries`
  - Definition of Done: `/api/monitoring/system` returns: CPU usage, memory usage, disk usage, active connections, uptime; `/api/monitoring/queries` returns: queries per minute (last hour), error rate (last hour), avg latency trend (last hour, 1-min buckets), top 5 slowest queries; data suitable for frontend dashboard consumption; Pytest tests with mocked system data
  - Dependencies: Week 5 Task 4, Week 6 Task 4

- **Task 5: Production readiness checklist and sign-off**
  - Tools: Markdown, manual testing
  - Output Artifact: `docs/production_readiness.md`
  - Definition of Done: Checklist covers: (1) all endpoints tested with valid and invalid inputs, (2) error handling for all failure modes documented, (3) security audit findings resolved, (4) performance benchmarks meet targets, (5) logging captures all critical events, (6) backup/restore verified, (7) deployment instructions step-by-step, (8) rollback procedure documented, (9) environment variables documented in `.env.example`, (10) API documentation complete and accurate; each item checked and signed off with date and tester name
  - Dependencies: All prior backend work

### Team 3 (AI / Model) – Deliverables

- **Task 1: Deploy recommended model version to inference server**
  - Tools: FastAPI, `transformers`, `peft` (or merged model), Docker
  - Output Artifact: Updated `ai/api/inference_server.py` with recommended model version, `ai/api/Dockerfile` (production build)
  - Definition of Done: Inference server loads recommended model (from Week 9 recommendation); Docker image builds successfully with model weights baked in; `GET /health` returns model version and "ready" status; 10 test queries return valid SQL; server starts within 60 seconds (model loading); documented in `ai/api/README.md`
  - Dependencies: Week 9 Task 3

- **Task 2: Implement model fallback chain (primary → quantized → API)**
  - Tools: Python, `transformers`, `llama-cpp-python`, Groq API (as ultimate fallback)
  - Output Artifact: `ai/services/model_fallback.py` with class `ModelChain` (methods: `generate(prompt) -> SQLResult`)
  - Definition of Done: Fallback chain: (1) try GPU-loaded full model → (2) if OOM or unavailable, use GGUF quantized model on CPU → (3) if CPU inference fails, call Groq API with Llama 3.1 70B; each fallback logged with reason; latency and model used included in response; Pytest test: mock GPU failure → assert CPU model used; mock both failures → assert Groq API called; all three levels produce valid SQL
  - Dependencies: Week 8 Task 2 (GGUF model); Week 1 Task 2

- **Task 3: Create Jupyter notebook for Aunalytics use case demonstrations**
  - Tools: Jupyter, Python, `pandas`, `matplotlib`
  - Output Artifact: `ai/notebooks/aunalytics_demo.ipynb`
  - Definition of Done: Notebook demonstrates 3 Aunalytics-relevant scenarios: (1) finance — "Show quarterly revenue trends" on synthetic financial DB, (2) healthcare — "Count patients by diagnosis" on synthetic health DB, (3) retail — "Top 10 products by sales volume" on synthetic retail DB; each scenario includes: sample database creation, NL query, generated SQL, results table, visualization; synthetic databases created inline with `faker`; all cells execute without errors
  - Dependencies: Week 9 Task 2

- **Task 4: Build model performance monitoring and alerting**
  - Tools: Python, `wandb` alerts, `structlog`
  - Output Artifact: `ai/services/model_monitor.py` with class `PerformanceMonitor`
  - Definition of Done: Monitor tracks rolling metrics (last 100 queries): mean latency, error rate, confidence score distribution; alerts triggered when: (1) mean latency > 5 seconds (W&B alert), (2) error rate > 10% (log CRITICAL), (3) confidence score drops below 0.5 for > 20% of queries (W&B alert); `GET /api/model/metrics` returns current rolling metrics; Pytest test asserts alerts fire when thresholds exceeded
  - Dependencies: Week 8 Task 4; Week 9 Task 4

- **Task 5: Write final AI/Model technical report**
  - Tools: Markdown, W&B exports, Jupyter
  - Output Artifact: `docs/ai_technical_report.md`
  - Definition of Done: Report contains: (1) model selection rationale (Qwen 2.5 7B vs. alternatives), (2) fine-tuning methodology (dataset composition, QLoRA config, training curves), (3) evaluation results summary (EX, EM, robustness, hallucination rates across all versions), (4) prompt engineering strategies compared, (5) inference optimization results, (6) cost analysis, (7) limitations and future work, (8) reproducibility instructions; report ≥ 2000 words; all claims supported by W&B metrics; peer-reviewed by ≥ 1 team member
  - Dependencies: All prior AI work

---

## Week 11: May 10 – May 16

### Team 1 (Frontend) – Deliverables

- **Task 1: Final integration testing with production Docker stack**
  - Tools: Cypress, Docker, `docker-compose`
  - Output Artifact: `frontend/cypress/e2e/production_smoke.cy.ts`, `scripts/run_e2e_docker.sh`
  - Definition of Done: `run_e2e_docker.sh` spins up full `docker-compose` stack → waits for health checks → runs Cypress suite against `http://localhost:3000`; smoke tests: upload → query → results → export → history; all tests pass against Dockerized services; script exits with code 0 on success, non-zero on failure; test run completes in < 10 minutes
  - Dependencies: Team 2 Week 10 Task 1

- **Task 2: Build presentation demo script with pre-loaded scenarios**
  - Tools: React, TypeScript, Cypress (for scripted demo recording)
  - Output Artifact: `frontend/demo/scenarios.ts` (5 scripted scenarios with NL queries and expected outputs), `frontend/demo/README.md` (demo script for in-person presentation)
  - Definition of Done: 5 demo scenarios documented with: (1) setup steps, (2) NL queries to type, (3) expected SQL output, (4) expected results, (5) talking points for presenter; `scenarios.ts` exports demo data for auto-population; `README.md` includes: timing per scenario (total < 15 minutes), backup plan if live demo fails (screenshots), Q&A preparation; dry-run completed successfully
  - Dependencies: All prior frontend work

- **Task 3: Deploy frontend to Vercel production**
  - Tools: Vercel CLI, GitHub Actions, `vercel --prod`
  - Output Artifact: Production URL on Vercel, `.github/workflows/deploy-production.yml`
  - Definition of Done: `vercel --prod` deploys frontend to production URL; CI/CD pipeline: merge to `main` → auto-deploy to Vercel; environment variables configured: `NEXT_PUBLIC_API_URL` pointing to deployed backend; production site loads with < 2 second LCP; SSL certificate active (HTTPS); deployment URL documented in `README.md`
  - Dependencies: Week 10 Task 3

- **Task 4: Create video walkthrough of application features**
  - Tools: Screen recording (OBS or Loom), Markdown
  - Output Artifact: `docs/demo_video_script.md` (timestamped script), video file or link
  - Definition of Done: Video script covers: intro (30s), file upload (1 min), schema exploration (1 min), NL queries — 3 examples of increasing complexity (3 min), results visualization (1 min), error handling demo (1 min), advanced features (history, export, dark mode) (2 min); total < 10 minutes; script includes exact words to say and UI actions; video recorded (or scheduled for recording)
  - Dependencies: All prior frontend work

- **Task 5: Final README.md update with project overview, setup instructions, and screenshots**
  - Tools: Markdown, screenshots
  - Output Artifact: Updated root `README.md`
  - Definition of Done: README contains: (1) project title and one-line description, (2) architecture diagram (embedded PNG), (3) tech stack table with versions, (4) setup instructions (prerequisites, clone, install, run — for frontend, backend, AI service), (5) Docker setup instructions, (6) 3+ screenshots of key features (upload, query, results), (7) API documentation link, (8) team member credits; all setup instructions verified by following from scratch on clean machine
  - Dependencies: All prior work across all teams

### Team 2 (Backend + Database) – Deliverables

- **Task 1: Deploy backend to Render/Railway/Fly.io**
  - Tools: Render (or Railway/Fly.io) CLI, Docker, GitHub integration
  - Output Artifact: Deployed backend URL, `render.yaml` (or equivalent IaC config)
  - Definition of Done: Backend deployed and accessible at public URL; `GET /health` returns 200; CORS configured for Vercel frontend domain; environment variables set via platform dashboard (not committed); auto-deploy on push to `main`; SSL active; deployment documented in `docs/deployment.md` with: platform choice rationale, configuration steps, environment variables needed
  - Dependencies: Week 10 Tasks 1, 2

- **Task 2: Deploy AI inference service with GPU**
  - Tools: RunPod/Lambda Labs/Fly.io GPU instances, Docker
  - Output Artifact: Deployed AI service URL, deployment configuration
  - Definition of Done: AI inference service running on GPU instance; `GET /health` returns model version and "ready" status; `POST /api/generate` returns SQL within 5 seconds; backend configured to call deployed AI service URL; cost documented ($/hour, estimated monthly); deployment instructions in `docs/deployment.md`
  - Dependencies: Team 3 Week 10 Task 1

- **Task 3: Set up production monitoring with uptime checks**
  - Tools: UptimeRobot (free) or similar, email alerts
  - Output Artifact: Monitoring configuration, `docs/monitoring.md`
  - Definition of Done: Uptime checks configured for: (1) frontend URL (every 5 min), (2) backend `/health` (every 5 min), (3) AI service `/health` (every 5 min); email alerts on downtime; `monitoring.md` documents: services monitored, alert recipients, escalation procedure, SLA targets (99% uptime); first 24 hours of monitoring data shows ≥ 99% uptime
  - Dependencies: Tasks 1, 2

- **Task 4: Run final integration test suite against deployed services**
  - Tools: Pytest, `httpx`, deployed URLs
  - Output Artifact: `backend/tests/integration/test_deployed.py`, `backend/reports/deployment_test_report.md`
  - Definition of Done: Tests run against deployed URLs (configurable via env var); test cases: (1) health checks for all services, (2) upload file → verify schema, (3) NL query → verify SQL and results, (4) error handling (invalid file, bad query); all tests pass; `deployment_test_report.md` documents: test results, latency measurements (higher than local due to network), any issues found and resolved
  - Dependencies: Tasks 1, 2, 3

- **Task 5: Create operational runbook for common issues**
  - Tools: Markdown
  - Output Artifact: `docs/runbook.md`
  - Definition of Done: Runbook covers: (1) service restart procedures (frontend, backend, AI), (2) database corruption recovery (restore from backup), (3) AI service OOM (switch to quantized model or API fallback), (4) high latency troubleshooting (check GPU utilization, connection pool, cache hit rate), (5) deployment rollback steps, (6) log access and analysis, (7) scaling procedures; each section has: symptom, diagnosis steps, resolution steps, prevention; reviewed by backend team
  - Dependencies: All prior backend and deployment work

### Team 3 (AI / Model) – Deliverables

- **Task 1: Upload best model to Hugging Face Hub**
  - Tools: `huggingface-cli`, `transformers`, `safetensors`
  - Output Artifact: Hugging Face model repository `<org>/qwen-nlsql-v4` (or recommended version)
  - Definition of Done: Model (merged or adapter) uploaded to HF Hub; model card includes: description, training data, evaluation results (EX, EM), usage example (Python code), limitations, license; model loadable via `AutoModelForCausalLM.from_pretrained("<org>/qwen-nlsql-v4")`; tested download and inference from clean environment
  - Dependencies: Week 10 Task 1

- **Task 2: Create final evaluation Jupyter notebook for presentation**
  - Tools: Jupyter, `pandas`, `matplotlib`, `seaborn`, `plotly`
  - Output Artifact: `ai/notebooks/final_evaluation.ipynb`
  - Definition of Done: Notebook contains presentation-quality visualizations: (1) accuracy progression chart (baseline → v1 → v2 → v3 → v4), (2) Spider vs. BIRD performance comparison, (3) robustness improvement chart, (4) hallucination rate reduction chart, (5) latency distribution histograms, (6) confidence calibration plot, (7) 5 impressive before/after examples, (8) cost comparison table; all plots have titles, labels, legends; notebook exports cleanly to PDF; all cells execute without errors
  - Dependencies: All prior evaluation results

- **Task 3: Prepare presentation slides content for AI/Model section**
  - Tools: Markdown, exported charts from Jupyter/W&B
  - Output Artifact: `docs/presentation/ai_section.md` with slide-by-slide content
  - Definition of Done: Content for 8-10 slides: (1) Problem: NL-to-SQL challenge, (2) Model choice rationale, (3) Fine-tuning approach (QLoRA diagram), (4) Training data composition, (5) Results: accuracy metrics, (6) Robustness and hallucination testing, (7) Inference optimization, (8) Demo queries, (9) Limitations and future work, (10) Aunalytics relevance; each slide has: title, 3-5 bullet points, visualization reference; presenter notes for each slide
  - Dependencies: All prior AI work

- **Task 4: Run final stress test on deployed inference service**
  - Tools: `locust`, Python, deployed AI service URL
  - Output Artifact: `ai/tests/load/results/production_load_report.md`
  - Definition of Done: Load test against deployed service (not local); test configs: 1, 5, 10 concurrent users × 5 minutes each; `production_load_report.md` documents: RPS achieved, latency percentiles, error rate, cost incurred during test; comparison to local benchmarks (Week 8); recommendation for maximum safe concurrent users; test results shared with Team 2 for runbook
  - Dependencies: Team 2 Week 11 Task 2

- **Task 5: Knowledge transfer documentation for AI components**
  - Tools: Markdown
  - Output Artifact: `docs/ai_knowledge_transfer.md`
  - Definition of Done: Document covers: (1) how to retrain the model (step-by-step with SLURM commands), (2) how to update training data (add new examples), (3) how to run evaluations (scripts and expected outputs), (4) how to switch model versions in inference server, (5) how to debug common inference issues (OOM, slow generation, wrong SQL patterns), (6) W&B project navigation guide, (7) key design decisions and rationale; document ≥ 1500 words; reviewed by both AI team members
  - Dependencies: All prior AI work

---

## Week 12: May 17 – May 23

### Team 1 (Frontend) – Deliverables

- **Task 1: Final bug bash and regression testing**
  - Tools: Cypress, Jest, manual testing checklist
  - Output Artifact: `frontend/reports/bug_bash_results.md`, updated `frontend/cypress/e2e/regression.cy.ts`
  - Definition of Done: 2-hour dedicated bug bash session; all discovered bugs logged in `bug_bash_results.md` with: description, reproduction steps, severity (P0-P3), fix status; P0 and P1 bugs fixed same day; regression test suite updated with tests for each fixed bug; all tests pass; `bug_bash_results.md` committed with final status
  - Dependencies: All prior work

- **Task 2: Performance budget enforcement in CI**
  - Tools: Lighthouse CI, `bundlesize`, GitHub Actions
  - Output Artifact: Updated `.github/workflows/frontend-ci.yml` with performance gates
  - Definition of Done: CI enforces: (1) JS bundle < 200KB gzipped (via `bundlesize`), (2) Lighthouse Performance ≥ 85, (3) Lighthouse Accessibility ≥ 95; PR blocked if any gate fails; current metrics all passing; `bundlesize` config in `package.json`; performance budget documented in `frontend/PERFORMANCE_BUDGET.md`
  - Dependencies: Week 9 Task 5, Week 6 Task 4

- **Task 3: Create shareable demo link with pre-loaded data**
  - Tools: Vercel, Next.js, URL query parameters
  - Output Artifact: Shareable URL with format `https://app.vercel.app/?demo=chinook&query=Show+all+albums`
  - Definition of Done: URL parameters: `demo` (pre-loads database), `query` (pre-fills query input), `autorun` (auto-executes query on load); 5 shareable links created for presentation; links work without prior setup; landing page detects `demo` param → loads pre-bundled database → shows results; links documented in `README.md`
  - Dependencies: Week 9 Task 2, Week 11 Task 3

- **Task 4: Generate final project documentation bundle**
  - Tools: Markdown, PDF export
  - Output Artifact: `docs/final_bundle/` containing: `README.md`, `architecture.md`, `api_documentation.md`, `user_guide.md`, `technical_report.md`, all exported as PDF
  - Definition of Done: All documentation compiled into `final_bundle/`; PDFs generated via markdown-to-PDF tool; table of contents with page numbers; consistent formatting across all documents; total documentation ≥ 5000 words across all files; no broken internal links; bundle reviewed by project lead
  - Dependencies: All prior documentation

- **Task 5: Presentation rehearsal and demo environment validation**
  - Tools: Manual testing, deployed services
  - Output Artifact: `docs/presentation/rehearsal_notes.md`
  - Definition of Done: Full presentation dry-run completed (< 20 minutes); all demo scenarios execute successfully on deployed services; backup screenshots captured for offline fallback; `rehearsal_notes.md` documents: timing per section, technical issues encountered, mitigation steps; internet-independent fallback plan verified (local Docker stack works)
  - Dependencies: All prior work across all teams

### Team 2 (Backend + Database) – Deliverables

- **Task 1: Final security scan and dependency audit**
  - Tools: `safety` (Python dependency scanner), `pip-audit`, `bandit` (static analysis)
  - Output Artifact: `backend/reports/security_scan.md`
  - Definition of Done: `pip-audit` shows zero known vulnerabilities (or documented exceptions with mitigations); `bandit -r backend/` shows zero high-severity findings; `security_scan.md` documents: tools run, findings, fixes applied, accepted risks with justification; all dependencies pinned to exact versions in `requirements.txt`; scan added to CI pipeline
  - Dependencies: All prior backend work

- **Task 2: Final load test on deployed production stack**
  - Tools: `locust`, deployed service URLs
  - Output Artifact: `backend/tests/load/results/production_load_report.md`
  - Definition of Done: Load test against deployed stack (frontend → backend → AI); test configs: 10 concurrent users × 10 minutes; measures: end-to-end latency (NL query → results displayed), RPS, error rate; `production_load_report.md` documents: results, comparison to local benchmarks, bottleneck analysis, capacity recommendations; target: ≥ 5 RPS with p95 < 8 seconds end-to-end
  - Dependencies: Week 11 Tasks 1, 2

- **Task 3: Verify all deployment rollback procedures**
  - Tools: Render/Railway CLI, Docker, Git
  - Output Artifact: `docs/rollback_verification.md`
  - Definition of Done: Rollback tested: (1) deploy broken code → verify detection via health check, (2) rollback to previous version → verify service restored, (3) time measured: detection (< 5 min via uptime monitor) + rollback (< 5 min manual); `rollback_verification.md` documents: steps taken, timing, issues encountered; rollback procedure verified for both backend and AI services
  - Dependencies: Week 11 Tasks 1, 2, 5

- **Task 4: Generate API changelog and version documentation**
  - Tools: Markdown, Git log
  - Output Artifact: `docs/api_changelog.md`
  - Definition of Done: Changelog lists all API endpoints with: (1) when introduced (week), (2) breaking changes (if any), (3) current request/response schemas, (4) deprecations; format follows Keep a Changelog standard; covers all endpoints from v1; reviewed for accuracy against OpenAPI spec
  - Dependencies: Week 8 Task 5

- **Task 5: Final backend test coverage report and gap analysis**
  - Tools: Pytest, `pytest-cov`, `coverage`
  - Output Artifact: `backend/reports/coverage_report.md`, `backend/htmlcov/index.html`
  - Definition of Done: `pytest --cov=backend --cov-report=html backend/tests/` generates report; target: ≥ 80% line coverage for `services/`, `routers/`; `coverage_report.md` lists: per-module coverage, uncovered critical paths, overall statistics; any module below 60% has documented remediation plan; coverage report added to CI; HTML report committed for review
  - Dependencies: All prior backend tests

### Team 3 (AI / Model) – Deliverables

- **Task 1: Final model accuracy verification on deployed service**
  - Tools: Python, `httpx`, deployed AI service URL, Spider dev set
  - Output Artifact: `ai/eval/results/deployed_verification.json`
  - Definition of Done: Run 100 Spider dev queries against deployed inference service; compare results to local evaluation: EX difference ≤ 1% (quantization/deployment should not degrade accuracy); any discrepancies documented with root cause; `deployed_verification.json` contains per-query results; verification script committed as `ai/scripts/verify_deployed.py`
  - Dependencies: Week 11 Task 1; Team 2 Week 11 Task 2

- **Task 2: Create interactive demo notebook for presentation**
  - Tools: Jupyter, `ipywidgets`, `requests`
  - Output Artifact: `ai/notebooks/interactive_demo.ipynb`
  - Definition of Done: Notebook has interactive widgets: (1) text input for NL query, (2) dropdown for database selection, (3) "Generate SQL" button, (4) output cells for: generated SQL, results table, confidence score, latency; calls deployed inference API; 5 pre-loaded example queries with expected outputs; works as backup demo if web UI fails; all cells execute without errors
  - Dependencies: Week 11 Task 1; Team 2 Week 11 Task 2

- **Task 3: Prepare AI team presentation with live demo**
  - Tools: Jupyter, deployed services, presentation software
  - Output Artifact: `docs/presentation/ai_demo_script.md`
  - Definition of Done: Demo script includes: (1) show baseline query failure (before fine-tuning), (2) show same query succeeding with v4, (3) demonstrate robustness (same question phrased 3 ways → same SQL), (4) show hallucination detection (query about nonexistent table → graceful error), (5) show confidence scores; timing: 5 minutes; backup: pre-recorded GIF for each step; dry-run completed
  - Dependencies: All prior AI work

- **Task 4: Archive all W&B experiments and export key metrics**
  - Tools: `wandb` API, Python, `json`
  - Output Artifact: `ai/wandb_export/` containing: `all_runs.json`, `key_metrics.csv`, `best_model_config.json`
  - Definition of Done: `all_runs.json` contains metadata for all W&B runs (run ID, config, final metrics); `key_metrics.csv` has one row per model version with columns: version, dataset, EX, EM, robustness, hallucination_rate, p95_latency; `best_model_config.json` contains full training config of recommended model; export script committed as `ai/scripts/export_wandb.py`; data verified against W&B dashboard
  - Dependencies: All prior W&B experiments

- **Task 5: Final AI system documentation and limitations**
  - Tools: Markdown
  - Output Artifact: `docs/ai_system_documentation.md`
  - Definition of Done: Document covers: (1) system architecture (prompt builder → inference → post-processor → validator), (2) model card (training data, biases, limitations), (3) known failure modes with examples (complex subqueries, ambiguous aggregations, cross-database queries), (4) performance envelope (what query complexity is supported), (5) cost per query at each deployment option, (6) future improvements roadmap (RAG, multi-turn, larger models), (7) ethical considerations (SQL injection risk, data privacy); ≥ 2000 words; peer-reviewed
  - Dependencies: All prior AI work
