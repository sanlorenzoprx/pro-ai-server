# Phone-Hosted Knowledge

DroidShield keeps the second-brain layer on the Android phone.

The Windows desktop app is only the control surface. It forwards port `8766`, checks the phone service, and shows the vault state. The source of truth lives in Termux:

```text
~/pro-ai-knowledge/
  raw/
  wiki/
    sources/
    entities/
    concepts/
    questions/
    index.md
    maintenance-log.md
  knowledge.sqlite3
```

## Startup

`droidshield generate-scripts` writes `pro-ai-knowledge-server.py` into the Termux bundle. `~/start-droidshield.sh` starts that phone-side server before launching Ollama.

For USB mode, the phone binds the knowledge API to `127.0.0.1:8766` and the host runs:

```powershell
adb forward tcp:8766 tcp:8766
```

`droidshield tunnel` now forwards both:

```powershell
adb forward tcp:11434 tcp:11434
adb forward tcp:8766 tcp:8766
```

## First Version Behavior

Use the desktop Knowledge tab to choose a `.md` file from Windows. The app sends it through the forwarded phone API, stores it under `~/pro-ai-knowledge/raw`, and ingests it immediately.

PowerShell can do the same thing:

```powershell
droidshield knowledge-add .\notes\my-source.md
```

The manual fallback is to drop markdown files into `~/pro-ai-knowledge/raw` on the phone, then use the desktop Knowledge tab's re-ingest action.

The phone server creates:

- source summary pages in `wiki/sources`
- an Obsidian-friendly `wiki/index.md`
- a `wiki/maintenance-log.md`
- SQLite tables for sources, chunks, wiki pages, and full-text search
- quick captures in `inbox/`
- daily briefs in `wiki/daily/`
- weekly syntheses in `wiki/weekly/`

## Feedback Loop

The 2nd Brain tab is built around output, not just storage:

- `Quick capture` saves an idea directly to the phone inbox.
- `Daily brief` creates a markdown brief with recent sources, quick captures, connections, a pattern, and a question.
- `Weekly synthesis` creates a markdown synthesis with thesis, evidence, contradictions, gaps, and one action.

The first implementation is deterministic and citation-oriented. It uses the local SQLite/FTS index and generated wiki pages. The next upgrade can route the same inputs through phone-hosted Ollama for richer synthesis.

This is the foundation for the COG-style maintained markdown wiki plus a Henry-style lightweight index. LLM expansion, richer entity/concept updates, and hybrid vector search can build on this phone-hosted base.
