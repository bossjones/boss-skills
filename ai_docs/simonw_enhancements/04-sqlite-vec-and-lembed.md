# sqlite-vec, sqlite-lembed and semantic search

**Verdict:** Ship a stdlib FTS5 sidecar index in the core now. Offer sqlite-vec + sqlite-lembed only as an opt-in `[semantic]` extra, because the default `python3` on this machine can't load extensions at all.

Legend: **[V]** means I verified it locally on 2026-10-16. **[D]** means it is stated in the docs or the repo. **[I]** is my inference.

## What it is

- **sqlite-vec** is a C SQLite extension that adds a `vec0` virtual table and `vec_distance_cosine()`. A KNN query looks like `WHERE embedding MATCH ? AND k = 5 ORDER BY distance`. The README says it is "pre-v1, so expect breaking changes" [D]. The latest stable release is **v0.1.9 (2026-03-31)**, and **v0.1.10-alpha.4** shipped on 2026-05-18, which is also the last commit [V, `gh api`]. The repo has 216 open issues and PRs, so it is active but busy.
- **sqlite-lembed** is a `llama.cpp`-backed extension that adds `lembed(model, text)`. Models are GGUF files that you register with `INSERT INTO temp.lembed_models ... lembed_model_from_file()` [D]. The latest release is **v0.0.1-alpha.8 (2024-08-24)** and the last commit was 2024-11-22, with nothing since [V]. In practice it is unmaintained alpha software, and its README still says "work-in-progress", with no batching and no GPU in prebuilt builds [D].
- Simon's TIL (2024-08-11) uses sqlite-vec **v0.1.1** through `datasette-sqlite-vec` / `sqlite-utils-sqlite-vec`. It builds `vec0` with `float[1536]` from an `llm`-produced `embeddings` table using OpenAI vectors, so it needs network access and an API key [D].
- `llm embed-multi --sql ... --store` can feed vectors from SQLite, and `llm similar` is brute-force cosine [D]. Local models come from the `llm-sentence-transformers` plugin, which brings a heavy torch dependency [D/I].
- The requested Datasette search page didn't mention semantic or vector search at all. It only covers FTS [D].

## Fit for the multi-agent plugin

| Idea | Plugin component | Verdict | Why |
|---|---|---|---|
| Keyword search over board history ("has anyone hit this CI error?") | `board.py search`, sidecar `board.fts.sqlite` | **Adopt now** | FTS5 is compiled into every interpreter I tested [V]. BM25 plus the porter stemmer matched "failed" for the query "fail" [V]. Error strings such as `SIGSEGV`, test names and PR numbers are exact tokens, which is where lexical search beats embeddings [I]. |
| Duplicate-question check before `post --kind question` | `board.py post --check-dupes` (advisory, prints top 3) | **Adopt now (FTS)** / Optional extra (vec) | A BM25 top-3 on the draft body costs about 1 ms on 11k rows [V]. Paraphrases such as "segfault" vs "SIGSEGV" are missed by FTS, which returned 0 hits [V], and caught by vectors, where the nearest neighbour scored distance 0.46 [V]. |
| Route a question to whoever last discussed the topic | `board.py who-knows "<text>"` | **Adopt now (FTS)** | Group the FTS hits by `sender` and weight by recency. No vectors are needed. |
| Recovery aid (PRIME-1 / REDIRECT-1) | `ma-recovery` skill: `board.py search --for <agent> --since <ts> "<task terms>"` | **Adopt now (FTS)** | After a restart the agent knows its task and branch names. Those are lexical [I]. |
| Topic clustering for the hourly digest | `digest` | **Later** | The digest already groups by `topic`. Clustering 400 posts per hour is a k-means job over vectors that sqlite-vec doesn't provide. The value is unproven [I]. |
| Semantic (paraphrase) search | `[semantic]` extra: `board.vec.sqlite` | **Optional extra** | It works and is cheap on the machines that can load extensions [V], but it is blocked on the default interpreter and lembed is abandoned (see Risks). |
| Vectors or FTS tables inside `board.sqlite` | board core | **No fit** | That would be an implicit schema change to the live DB, which the spec forbids. |

## Proposed spec changes

1. **Phase 2 → Design rules → Board: add a sidecar rule.** "Derived indexes live in `$MA_HOME/board.fts.sqlite` (core) and `$MA_HOME/board.vec.sqlite` (extra). They are built by an indexer that ATTACHes the board read-only. They are disposable: delete them and rebuild." I tested this ATTACH pattern [V]. Writes through `board.*` fail with "attempt to write a readonly database", and the board's `schema_version` and mtime stayed the same.
2. **Phase 2 layout: add `lib/multi_agent/search.py`** (stdlib only):

   ```sql
   -- board.fts.sqlite
   CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(
     body, topic, kind UNINDEXED, sender UNINDEXED, ts UNINDEXED,
     tokenize='porter unicode61');          -- rowid = messages.id
   CREATE TABLE IF NOT EXISTS meta(k PRIMARY KEY, v);  -- board_path, last_id, built_at
   ```

   ```python
   def index(board, side):                     # idempotent, incremental
       s = sqlite3.connect(side, timeout=5)
       s.execute("ATTACH ? AS board", (f"file:{board}?mode=ro",))  # requires uri=True on connect
       s.execute("PRAGMA board.query_only=1")
       last = s.execute("SELECT coalesce(max(rowid),0) FROM fts").fetchone()[0]
       s.execute("""INSERT INTO fts(rowid,body,topic,kind,sender,ts)
                    SELECT id,body,topic,kind,sender,ts FROM board.messages
                    WHERE id > ? ORDER BY id""", (last,))
       s.commit()
   ```

   Messages are append-only, so `id > last` is enough. If `max(id)` in the board is lower than `last`, the board was reset: drop the index and rebuild. Run the indexer lazily inside `search` and as a `--once` step of the `status` monitor. Never run it from hooks.

3. **Phase 2 subcommands: add `search "<q>" [--for A] [--topic T] [--since TS] [--limit 10] [--json]`**, `who-knows "<q>"`, and an advisory `post --check-dupes` that prints `DUPE? #id sender snippet` lines and still posts. Escape user text into an FTS5 phrase or token list so that `-` and `:` in CI errors don't raise `fts5: syntax error` [I]. Exit code 1 means no hits, which matches the existing exit-code table.
4. **Phase 1 R4 / Phase 3 tests:** the FTS5 availability check is `CREATE VIRTUAL TABLE temp.x USING fts5(a)` in a try block. If it fails, `search` falls back to `LIKE` over the board opened `mode=ro`. The tests are: "index leaves board schema_version and mtime unchanged", "incremental index after new posts", and "search runs under `python3 -I`".
5. **New optional extra `profiles/semantic/` (or `lib/multi_agent/semantic.py`)**, PEP 723 with `dependencies = ["sqlite-vec==0.1.9", "sqlite-lembed==0.0.1a8"]`:

   ```sql
   CREATE VIRTUAL TABLE vec USING vec0(embedding float[384] distance_metric=cosine);
   INSERT INTO vec(rowid, embedding) VALUES (:id, lembed('mini', :body));
   SELECT rowid, distance FROM vec
    WHERE embedding MATCH lembed('mini', :q) AND k = 10 ORDER BY distance;
   ```

   Its first step probes `hasattr(conn, "enable_load_extension")` and prints `SEMANTIC-UNAVAILABLE: interpreter lacks extension loading (use uv run)` before exiting 2. Model path: `$MA_HOME/models/all-MiniLM-L6-v2.q8_0.gguf`, fetched by an explicit `ma install --semantic` step, never on demand. Use hybrid ranking with reciprocal-rank fusion of the FTS and vec top-20 [I].

6. **Codex parity section:** the FTS core needs nothing beyond `--add-dir $MA_HOME`. The semantic extra must have its wheels in the uv cache and the model on disk before a sandboxed worker runs it. I confirmed that `uv run --offline` works once cached [V].

## Risks and costs

**Extension loading** [V]. I ran `hasattr(conn, "enable_load_extension")` and an FTS5 table create under each interpreter with `-I`, and checked `PRAGMA compile_options`.

| Interpreter | SQLite | `enable_load_extension` | FTS5 | sqlite-vec loads |
|---|---|---|---|---|
| Apple CLT `/usr/bin/python3` 3.9.6 | 3.51.0 | **No** (`OMIT_LOAD_EXTENSION`) | Yes | No |
| **pyenv 3.12.8, the default `python3` here** | 3.51.0 | **No** (linked to system SQLite) | Yes | No (AttributeError) |
| Homebrew 3.10–3.14 | 3.53.4 | Yes | Yes | Yes (3.13 tested) |
| uv python-build-standalone 3.13.15 | 3.53.1 | Yes | Yes | Yes |

The `python3 -I` that agents actually invoke can't load extensions. Any vector feature therefore has to run through `uv run --python 3.13` or Homebrew, never the core CLI path.

**Cost** [V, synthetic data]. I used a 24.1 MB MiniLM q8_0 GGUF (25,279,104 bytes) on Apple Silicon CPU with 11,000 synthetic messages of about 60 characters each.

| Operation | Result |
|---|---|
| Embedding | 12.5 s total (1.1 ms per message) |
| KNN query, including embedding the query | 1.6–5.4 ms |
| Sidecar size | 19 MB |
| FTS5 index build over the same 11,000 messages | 0.02 s |
| FTS5 query | about 1 ms |

The live bodies are longer, so expect roughly 5–20x the embedding time, still under a few minutes, and incremental after the first run [I]. MiniLM truncates long input at its token limit, so long posts are embedded only from their first part [I].

**Other risks**

- sqlite-lembed has had no release since 2024-08 and depends on a pinned `llama.cpp` [V/D]. If it breaks, the swap-ins are `llm embed-multi` with `llm-sentence-transformers` (heavy) or a remote API (needs network, which conflicts with sandboxes).
- sqlite-vec is pre-v1, with breaking changes possible [D]. Pin `==0.1.9`, since the sidecar is rebuildable.
- Privacy: an indexer that uses a remote embedding API would ship every agent message off-box. The extra must be local-only [I].
- Synthetic-data caveat: in my corpus five identical template posts tied at the top. On the real board, duplicate-detection precision is untested.

## Appendix: references

- <https://til.simonwillison.net/sqlite/sqlite-vec>: The TIL is dated 2024-08-11 and uses sqlite-vec v0.1.1. It covers `vec0 float[1536]`, the KNN `MATCH ... k`, `vec_distance_cosine`, the sqlite-utils and Datasette plugins, and OpenAI embeddings via `llm`.
- <https://alexgarcia.xyz/blog/2024/sqlite-lembed-init/index.html>: This post is dated 2024-07-24 and uses v0.0.1-alpha.4. It covers `temp.lembed_models`, `lembed()`, the MiniLM q8_0 example at 384 dimensions, and beta status with no Windows support.
- <https://github.com/asg017/sqlite-vec>: The README carries the pre-v1 warning, `pip install sqlite-vec`, and pure C with no dependencies. Releases and dates come from `gh api repos/asg017/sqlite-vec/releases`: v0.1.9 on 2026-03-31 and v0.1.10-alpha.4 on 2026-05-18.
- <https://github.com/asg017/sqlite-lembed>: The README says "work-in-progress", with no batching and no prebuilt GPU support. `gh api` shows v0.0.1-alpha.8 on 2024-08-24 and the last commit on 2024-11-22.
- <https://pypi.org/pypi/sqlite-vec/json> and <https://pypi.org/pypi/sqlite-lembed/json>: Both have macOS arm64 and x86_64 wheels, at versions 0.1.9 and 0.0.1a8.
- <https://huggingface.co/asg017/sqlite-lembed-model-examples/resolve/main/all-MiniLM-L6-v2/all-MiniLM-L6-v2.e4ce9877.q8_0.gguf>: This model is 25,279,104 bytes. I downloaded it and used it for the benchmark.
- <https://llm.datasette.io/en/stable/embeddings/cli.html>: Covers `embed-multi --sql/--attach/--store`, collections tied to one model, brute-force `llm similar`, and `llm-sentence-transformers` for local models.
- <https://docs.datasette.io/en/stable/search.html?q=semantic&check_keywords=yes&area=default>: The page loaded, but its content had no mentions of semantic, embedding or vector search.
- Local scratch scripts are in `/private/tmp/claude-501/simonw-research/vec/`: `probe.py`, `bench.py` and `models/`.
