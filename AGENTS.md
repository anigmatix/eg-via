# AGENTS.md — EG-VIA (Evidence-Grounded Variant Interpretation Assistant)

> This file defines how AI coding agents (Codex) should work in this repo.  
> Follow these rules before making any changes.

## 0) Mission
Build EG-VIA: a safety-oriented, evidence-grounded system that produces **citation-bound** variant interpretation drafts for oncology SNVs/indels, with **uncertainty** and **abstention**.

This is an *assistive evidence synthesis tool*, not a clinical decision engine.

---

## 1) Non-Negotiables (Safety + Correctness)
1. **No treatment recommendations** (no drug, dosing, regimen, NCCN-like guidance).
2. **No diagnosis claims** and no patient-specific decisioning.
3. **No citation → no claim**: every extracted claim must map to a real citation present in the evidence table.
4. **Uncertainty is required**: outputs must include limitations and uncertainty language.
5. **Abstain when weak/conflicting**: if evidence is insufficient or contradictions are high, return an abstention response and explain what’s missing.
6. Never fabricate citations, PMIDs, URLs, or quotes.

If any of these constraints are violated, the change is invalid.

**MVP clarification:** We enforce **claim-level citation binding** (every claim has a citation).  
Sentence-level citation coverage is a later hardening step and/or evaluation metric.

---

## 2) Development Workflow (How Agents Operate)

### 2.1 Branch / Worktree Strategy
- Each agent must work on **one vertical slice** in isolation:
  - `agent/backend-retrieval-*`
  - `agent/backend-orchestrator-*`
  - `agent/frontend-ui-*`
  - `agent/eval-*`
  - `agent/deployment-*`
- Keep PRs small and focused. Avoid refactors unless necessary for the task.

### 2.2 Definition of Done (DoD) for any agent task
A task is done only when:
- Code compiles/runs locally
- Tests pass
- Lint/type checks pass (if configured)
- README/inline docs updated if behavior changed
- Safety constraints (Section 1) preserved
- No secrets added to repo

### 2.3 Communication Protocol
When proposing changes, the agent must provide:
- Summary of what changed
- Why this design
- How to run/test
- Known limitations / TODOs
- Any risks or follow-ups

---

## 3) Repo Structure (Expected)
eg-via/  
frontend/  # Next.js + Tailwind UI  
backend/   # FastAPI service + orchestration  
eval/      # datasets + eval runner scripts  
infra/     # docker-compose, CI, deployment config  
AGENTS.md  
README.md  

Agents must not move folders without explicit instruction.

---

## 4) Tech Stack and Standards

### 4.1 Backend
- Python 3.11+
- FastAPI
- Pydantic v2 for schemas
- HTTP clients: `httpx`
- Logging: structured logs (JSON preferred)
- Unit tests: `pytest`

Backend must implement an orchestrated pipeline:
- `Retrieval` → `Claim Extraction` → `Evidence Grading` → `Synthesis` → `Verification` → `Response`
- Deterministic gating: thresholds for abstention/conflict (policy-owned, not LLM-owned)

### 4.2 Frontend
- Next.js (App Router preferred)
- TypeScript
- Tailwind
- Minimal dependencies
- UI must present:
  - Draft interpretation
  - Evidence table
  - Confidence + abstention
  - Trace panel

### 4.3 Formatting / Style
- Python: Ruff (and Black if configured)
- TS: ESLint + Prettier (if configured)
- Prefer clarity over cleverness.

---

## 5) Core Data Contracts (Do NOT break)

### 5.1 Variant Request (API v1, MVP)
Canonical request schema used by backend route `POST /v1/interpret`:

- `gene: string`
- `hgvs: string`
- `variant_type: "SNV" | "indel"`
- `disease_context: string`
- `assay_context: "tumor-only" | "tumor-normal" | "panel" | "WES"`
- `user_question?: string`

If a change requires schema changes, update:
- backend schemas
- frontend types
- eval harness
- and document in README

### 5.2 Citation Object (Evidence metadata)
- `citation_id: string` (e.g., "C1", "P3")
- `source: "ClinVar" | "PubMed"`
- `title?: string`
- `year?: number`
- `url?: string`
- `raw_id?: string` (e.g., PMID or ClinVar variation ID)
- `metadata?: object` (source-specific)

### 5.3 Claim Object (critical)
All claims must be schema-valid and citation-bound:

- `claim_id: string`
- `text: string`
- `citation_id: string` (must exist in evidence table)
- `supports_or_contradicts: "support" | "contradict" | "neutral"`
- `evidence_strength: "Strong" | "Moderate" | "Weak"`
- `year?: number`

### 5.4 Evidence Table Entry (MVP)
Each evidence table entry pairs a citation with a single extracted claim:

- `citation: Citation`
- `claim: Claim`

### 5.5 Output (API v1, MVP)
Canonical response schema from `POST /v1/interpret`:

- `request_id: string`
- `draft: { summary, what_is_known, conflicting_evidence, limitations, uncertainty, disclaimer }`
- `evidence_table: EvidenceTableEntry[]`
- `confidence_panel: { confidence: number (0–1), reasons: string[], abstain: bool, abstain_reasons: string[] }`
- `trace: { request_id, retrieval_queries, source_count, claim_count, conflict_count, verification_checks, verification_failures, timings_ms }`

---

## 6) Orchestration Rules
- Retrieval must run before extraction.
- Extraction must yield valid Claim JSON objects (schema validated).
- Synthesis can ONLY use the structured claim objects (no free-form external facts).
- Verifier must run after synthesis.
- Verifier may:
  - edit the draft to remove unsupported content
  - downgrade confidence
  - trigger abstention
- Any “treatment-like” content must be removed/blocked.

---

## 7) Evidence & Citation Rules
- Every claim must map to a `citation_id` that exists in `evidence_table`.
- Prefer paraphrases; avoid long direct quotes.
- Never invent PMIDs/accessions.
- If sources disagree, explicitly describe conflict and reduce confidence.

---

## 8) Testing Requirements

### 8.1 Backend tests (minimum)
- API contract tests for `/healthz` and `/v1/interpret`
- Schema validation tests for Claim, Citation, EvidenceTableEntry, Output
- Abstention triggers under low/empty evidence
- Treatment-language blocking test(s)
- Retrieval unit tests must use recorded fixtures (no flaky network tests)

### 8.2 Frontend tests (optional MVP)
- Type checks
- Minimal component tests if time allows

### 8.3 Eval harness
- Target: 30 curated variants (post-MVP can start smaller)
- Automated checks:
  - claim citation binding
  - abstain vs ok expectations for selected cases
  - structural validation of outputs

---

## 9) Local Development Commands (keep updated)
> If these commands change, update this section.

### Backend (uv-based, recommended)
From repo root:
- Create venv:
  - `uv venv && source .venv/bin/activate`
- Install backend editable:
  - `uv pip install -e backend`
- Run:
  - `uvicorn backend.app.main:app --reload --port 8000`
- Tests:
  - `pytest -q backend/tests`

### Frontend
- Install:
  - `cd frontend && npm install`
- Run:
  - `cd frontend && npm run dev`
- Typecheck/lint (if configured):
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run lint`

### Full stack (optional)
- `docker compose up --build`

---

## 10) Security & Secrets
- Never commit API keys or secrets.
- Use `.env.local` for frontend and `.env` for backend (gitignored).
- Use mock keys in examples.

---

## 11) When in Doubt (Agent Behavior)
- Prefer smaller, testable changes.
- Ask for clarification only if blocking; otherwise make the best safe assumption.
- If a task is ambiguous, implement the smallest safe increment and document limitations.

---

## 12) Quality Bar (What “Good” Looks Like)
This is not a toy demo. Changes should reflect:
- clear separation of concerns
- deterministic safety gates around LLM outputs
- reliable schemas + validation
- strong developer experience (run/test easy)
- traceability and transparency

End goal: a repo that would impress an Anthropic/Google Health interviewer.
