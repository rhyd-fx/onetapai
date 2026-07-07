# OneTap AI — Full Phase-by-Phase Audit

> **Audited:** 2026-07-04 · **Method:** 5 parallel review agents, one per phase, comparing actual code against `plan.md`. Findings cite `file:line` evidence and were verified against the one archived Henrik match.

---

## ✅ Resolution Status (updated 2026-07-05)

The findings below are the **original** audit. The following have since been fixed and verified end-to-end against a live stack (MariaDB + Qdrant v1.15.1 + MinIO + FastAPI):

1. **Secrets & config** — committed Henrik key removed; central `config.py` + `.env` loader; all creds/CORS env-driven.
2. **Vendor swap** — OpenAI/Anthropic → **FastEmbed** (local embeddings) + **OpenRouter** (generation), all env-configurable.
3. **Schema truncation** — `season_id`→VARCHAR(36), `queue_id`→VARCHAR(20) (source fixed to `metadata.queue`); verified no truncation on real ingest.
4. **Coordinate-space contradiction** — new `analysis/spatial/coordinates.py` (robust p1–p99 per-map bounds + `normalize`/`to_percent` + calibration CLI); peek classifier recalibrated to world-unit, map-scaled thresholds; angle-wraparound fixed. Split calibrated from real data.
5. **Real ingestion** — token-bucket rate limiter (replaces concurrency-only "limiter"); snowball `backfill.py`; S3/MinIO archival (`archiver.py`, MinIO in compose).
6. **API wired to DB** — `routes.py` rewritten: `/analyze`, `/acs-trajectory`, `/heatmap`, `/tilt`, `/coach`, `/feedback` all return real computed data with 400/404/501/502/503 handling; `main.py` entrypoint added.
7. **RAG works** — starter knowledge corpus + `ingest_knowledge.py`; **true hybrid** retrieval (dense + BM25 sparse + RRF fusion, off the deprecated `.search()`); grounding guard applied; `/coach` generates grounded, cited answers via OpenRouter.
8. **Tilt calibrated** — non-saturating weighted/significance-gated probability; real `session_date`; honest decline %; wired to DB via `/tilt`; asserting tests.
9. **Feedback loop** — `coaching_feedback` table + `/feedback` endpoint + thumbs UI in `CoachingChat`.
10. **Frontend wired** — Dashboard search → real `/analyze`; heatmap, ACS chart, and coaching chat all consume the live API (Next.js 16); typechecks clean.

**Still open (known follow-ups):** hardware-profile CRUD; remaining aim-deficiency detectors (range/economy splits); `player_sessions` persistence; per-map minimap images + coordinate axis tuning; expanding the knowledge corpus; packaging the backend with `__init__.py` to drop the `sys.path` shims.

---

## Overall verdict

The project is a **well-scaffolded skeleton, not a working system**. Every phase has clean, plausible-looking code that mirrors the plan — but almost none of it is wired together. Three cross-cutting problems dominate everything below:

1. **The API layer is 100% stubbed.** `backend/api/routes.py` — every endpoint (`/analyze`, `/coach`, `/heatmap`, `/acs-trajectory`, `/economy-impact`) returns hardcoded empty JSON or `"This is a stub answer."`. Nothing connects the DB, analysis modules, and RAG layer. This is the single biggest blocker: it's why Phases 1–4 can't actually run end-to-end.
2. **Nothing touches the database after ingestion.** All analysis/tilt/RAG modules are pure functions fed by test-file literals. `grep` for any DB access across `backend/analysis/` returns nothing. They're unit-testable islands, not a pipeline.
3. **A coordinate-space contradiction poisons all spatial work.** The plan's §5.1 explicitly warns coordinates are large signed Unreal units — and the real ingested match confirms it (**x: −3447→8232, y: −9421→800**). Yet the schema comments, Appendix B, the peek-classifier thresholds (`30`/`50`/`90`), and the frontend heatmap all assume a 0–1024 (or %) space. Every spatial feature is calibrated to a coordinate system that doesn't exist in the data.

### 🔴 Urgent, non-phase: a live-format API key is committed
`backend/ingestion/test_henrik.py:16` hardcodes a real Henrik key as a fallback default (`HDEV-0e05...711e`). Rotate it and purge from git history now, before anything else.

---

## Completion by phase

| Phase | Area | Estimate |
|---|---|---|
| **0** | Foundation (ingest/schema/ETL) | **~35%** |
| **1** | Core analysis (spatial/mechanical) | **~35%** |
| **2** | RAG pipeline | **~20–25%** |
| **3** | Tilt detection + API hardening | **~20%** |
| **4** | Frontend | **~30%** |
| **5** | Bot / VOD (in-scope items) | **~25%** |

The earlier Opus 4.6 "~60%" for Phase 0 was generous — on re-audit it's ~35%, because the schema (the one genuinely finished piece) is only one of five deliverables, and "ingest 1,000+ matches," S3 archival, and true rate limiting are all absent or broken.

---

## Phase 0 — Foundation (~35%)

**Solid:** The DDL (`db/init.sql`) is a faithful, complete implementation — all 10 tables, 3 views, generated columns, indexes, FKs, auto-provisioned via `docker-compose`. The ETL's Henrik-JSON decomposition is real and mostly correct against the actual payload (verified: `metadata.matchid`, `all_players`, global `kills[]` grouped by `round`, killer-location lookup, `teams.red/blue.has_won`). All SQL is parameterized — **no injection risk**.

**All 5 prior-review claims CONFIRMED with evidence:** 1 match (not 1,000+), no `__init__.py`, no S3/MinIO, Pydantic models are dead code (`models.py` never imported), no config/`.env` (creds hardcoded).

**New bugs the prior review missed:**
- 🔴 **`season_id` data corruption on every match.** Henrik returns a 36-char UUID; `matches.season_id` is `VARCHAR(10)`. `INSERT IGNORE` silently truncates it to `"4f0864e2-4"` on every row. (`init.sql:34` vs `etl.py:161`)
- 🟠 **`queue_id` truncated + wrong field.** ETL maps `metadata.mode_id` ("competitive", 11 chars) into `VARCHAR(10)` → `"competitiv"`; should be `metadata.queue`.
- 🟠 **The "rate limiter" isn't one.** `asyncio.Semaphore(18)` (`worker.py:20`) caps *concurrency*, not requests/sec; `requests_per_2min` is never used. Pointed at a real 1,000-match backfill on Henrik's 30 req/min tier → immediate sustained 429s.
- 🟠 **`HenrikAPIClient` is itself dead code.** The only working fetch (`test_henrik.py`) reimplements fetching inline and never uses `worker.py`.

Minor/latent: `round_result_code` never populated; `player_locations` stores only the first kill-snapshot per player/round; `players` insert uses `p["puuid"]` without `.get()` (a malformed player rolls back the whole match); `test_ingestion.py` is dead legacy scaffolding.

---

## Phase 1 — Core Analysis (~35%)

**Solid:** `AimProfile` classifier and the `drill_prescriber` (the best module in the repo — genuinely eDPI-aware) are implemented and internally consistent. The ACS-variance SQL view computes coefficient of variation correctly with a divide-by-zero guard. `distance_to_nearest_wall` vector math is correct.

**Missing/broken:**
- ❌ **Map geometry JSON: zero files exist.** Peek classification literally cannot run on real data — `MapGeometry` can only be built from test-file dummy arrays.
- 🔴 **Peek thresholds off by ~2.5 orders of magnitude** (the coordinate-space bug above). 30 units ≈ 0.3% of map width, so `TIGHT_PEEK`/`CROSSFIRE_ENTRY` essentially never fire and nearly everything is misclassified `WIDE_SWING` — output is effectively constant.
- 🟠 **Angle-difference has no wraparound** (`peek_classifier.py:69-76`): +3.0 vs −3.0 rad reads as 6.0 apart instead of ~0.28 → false `OFF_ANGLE`.
- 🟠 **`distance_to_nearest_wall` crashes on empty `wall_segments`** (no guard, unlike the crossfire function).
- 🟡 **ACS-variance view measures the wrong axis:** it groups by `(puuid, agent, match)` → within-match round dispersion, but "feast-or-famine" (and the RAG consumer) means match-to-match. And nothing populates the `acs_cv` the prompt builder reads — it silently defaults to 0 for everyone.
- ❌ Only 3 of 6 aim deficiencies have detection logic; no hardware CRUD (just the table); no zero-damage-death SQL view/flagging pipeline.

---

## Phase 2 — RAG Pipeline (~20–25%)

**Solid:** Qdrant collection schema is correct (3072-dim cosine, matches `text-embedding-3-large`), payload indexes present, provisioned in compose. Multi-query decomposition (`retriever.py:76-136`) is real logic. Prompt composer is well-formed.

**Missing/broken — the value-bearing parts:**
- ❌ **The entire knowledge corpus is absent.** Zero agent playbooks, map docs, or aim methodology files exist. The plan's stated "moat" doesn't exist.
- ❌ **No chunking/embedding/ingestion pipeline.** Nothing reads docs and upserts to Qdrant (`grep upsert` → nothing). So even if built, the collection is empty → `retrieve()` returns `[]`.
- ❌ **No Claude integration.** `grep anthropic/claude` → nothing despite being in requirements. `/coach` returns a hardcoded stub.
- ⚠️ **"Hybrid" retriever is dense-only — the label is false.** `use_hybrid=True` and `rrf_k=60` are read nowhere; there's no sparse vector, no BM25, no RRF. The schema can't even support it (no `sparse_vectors_config`).
- ⚠️ **Grounding guard is inert** — `grounding.py`'s `GROUNDING_SUFFIX` is never imported/applied, so the anti-hallucination constraints from §10.2 never reach the model.
- ❌ No feedback loop (thumbs up/down) anywhere.
- ⚠️ `retriever.py:58` uses the deprecated Qdrant `.search()` API; deps in `requirements.txt` are entirely unpinned.

---

## Phase 3 — Tilt Detection & API Hardening (~20%)

**Solid:** `detect_tilt` is a clean port with defensive `float()`/`isnan` guards; session segmentation by >90-min gaps is correct logic; the `player_sessions` schema is purpose-built for its output.

**Missing/broken:**
- ❌ **The tilt detector is dead code** — never imported, never fed DB data, never persisted. `player_sessions` is never written to by any code.
- ❌ **API layer:** no auth, no rate limiting, no error handling (`HTTPException` imported but never raised; Redis unused). Every endpoint is a stub. No backend service in `docker-compose` and no `main.py` — the app isn't part of the deployable stack.
- 🟠 **`session_date` holds an integer index, not a date** (`tilt_detector.py:107` → `"0"`). Persisting into `session_date DATE NOT NULL` would error / collide on the unique key.
- 🟠 **Probability math saturates instantly:** Factor 1 multiplies normalized slope by `5.0`, so a slope of −0.2 alone maxes the score to 1.0 before the other two factors matter — the three-factor model is theatre. `p_value` is discarded (no significance gating), so normal 3-match variance can trigger a "🛑 stop queueing" false positive.
- 🟡 Docstring advertises CV/R²-based scoring, but neither is actually scored; recommendation text reports a per-match slope % ("~20%") when the real session drop is 46%.

---

## Phase 4 — Frontend (~30%) & Phase 5 — Bot/VOD (~25%)

**Solid:** Genuine Next.js App-Router scaffold; `recharts` present and the ACS chart is a real `LineChart` with a tilt `ReferenceLine`; `DrillCard` is a real prop-driven component. The **Discord bot is the most production-shaped artifact in the repo** — idiomatic `discord.py`, async `httpx` with timeouts and error handling, API shape matches `routes.py`.

**Missing/broken:**
- ❌ **Zero backend integration.** `grep fetch|axios|NEXT_PUBLIC` across `frontend/src` → nothing. Every component renders hardcoded literals (dashboard hardcodes `Friday#PlayZ`). No player search, no Riot ID lookup.
- 🔴 **The flagship map heatmap is faked:** plain `<div>`s at hardcoded CSS `top%/left%` with `{/* Mock Deaths */}` comments — not Canvas/WebGL, and no world-space→screen transform for the Unreal-unit coordinates. Feed real `{x:-4200, y:8150}` and points render off-canvas.
- ❌ Coaching chat is fake (`setTimeout` + canned string, never calls `/coach`); economy stacked-bar chart doesn't exist at all.
- ⚠️ CORS is single-origin (`localhost:3000`) — a deployed frontend would be blocked.
- ❌ **VOD "pipeline" is a placeholder** — 24 lines: a docstring and one dataclass, no executable logic.

---

## What to fix first (recommended order)

1. **Rotate the committed Henrik API key** and add a `.env` + config module (kills the Phase 0/2 hardcoded-creds findings at once).
2. **Fix the schema/data mismatches now**, before ingesting at scale: widen `season_id`/`queue_id`, and **resolve the coordinate-space contradiction** (drop the 0–1024 assumption everywhere; adopt per-map bounds). Cheap now, a painful migration later.
3. **Build the ingestion backfill** (batch loop + pagination + a real token-bucket rate limiter + S3/MinIO) and actually load 1,000+ matches — Phase 0's whole goal is proving the schema at scale, and it hasn't been tested past 1 match.
4. **Wire one vertical slice end-to-end**: `routes.py` → DB query → one analysis module → response → one frontend component. This is the highest-leverage move; it converts the pile of correct-looking islands into a working spine and will expose the real integration bugs.
5. Then iterate on quality: recalibrate peek thresholds against real data, add the RAG knowledge corpus + embedding pipeline, and fix the tilt probability calibration.

Structural notes: add `__init__.py` files (imports currently only work from specific CWDs), and note the Pydantic models are entirely bypassed — the ETL's `dict.get()` approach works but gives none of the "validated data" the plan promised.
