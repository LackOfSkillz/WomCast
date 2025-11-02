# WomCast — Technical Implementation Plan (from Spec → Concrete Build Plan)

**Goal**: Turn the WomCast specification into a concrete, versioned build plan with architecture decisions, component boundaries, tooling, image-build steps, CI gates, and milestone-scoped deliverables. Output should drive /speckit.tasks.

## 1) Final Architecture Decisions (ADRs)

### ADRs Summary

**Frontend Flavor (ADR-001)**: MVP uses React + Electron (TypeScript) for a custom 10-foot UI. Rationale: tighter control, cross-platform dev convenience, easy PWA reuse in M5. Keep a Kodi Skin alt-path documented but not built by default.

**Backend Pattern (ADR-002)**: FastAPI (Python 3.11) micro-services in a single repo, split into deployable service folders:
- `indexer` (USB index + metadata/artwork cache)
- `media` (playback orchestrator + player bridge)
- `ai` (Whisper/Ollama/Chroma bridge)
- `livetv` (M3U/HLS/DASH ingest & normalize)
- `cast` (mDNS/WebRTC pairing + phone-mic relay)
- `connectors` (Internet Archive, PBS, NASA TV, Jamendo)

**Playback Engine (ADR-003)**: Prefer mpv with libmpv bindings or Kodi JSON-RPC as a bridge. For MVP, start with Kodi JSON-RPC to leverage proven playback + CEC support; abstract via media service so we can swap to libmpv later.

**Database (ADR-004)**: SQLite for the library (lightweight, Pi-friendly) + ChromaDB for embeddings. Migrations managed via Alembic-style scripts (even for SQLite) for consistency.

**AI Stack (ADR-005)**: Whisper (small) for default STT; Ollama small/fast model for intent; Chroma for semantic search. All local. Settings allow model swap.

**Security Mode (ADR-006)**: LAN-only binds by default, optional TLS, PIN pairing; short-lived tokens for cast/QR. No telemetry. Minimal logs without PII.

**Image Base (ADR-007)**: Raspberry Pi OS Lite base for MVP image (fewer build eccentricities than LibreELEC; easier service management). Keep LibreELEC notes for post-MVP.

## 2) Technology & Versions

- **Node/TS**: Node 20 LTS, TypeScript 5.x, Vite or Electron Forge
- **React**: React 18.x; React Router; headless 10-foot UI components (custom)
- **Electron**: Electron 31+; secure IPC; auto-launch on boot
- **Python**: 3.11.x; FastAPI; Uvicorn; Pydantic v2; httpx; orjson
- **Playback**: Kodi 21 (Omega) JSON-RPC bridge OR mpv/libmpv (second path)
- **Media Tools**: ffmpeg >= 6, yt-dlp (only for free/public domain connectors where compliant)
- **Whisper**: whisper-cpp or openai-whisper; start with small model; quantization where possible
- **Ollama**: latest stable; default model small (e.g., llama3-instruct small variant or similar fast)
- **ChromaDB**: latest 0.5+; persistent local store
- **WebRTC/mDNS**: web-friendly signaling (FastAPI), aiortc for server side if needed; zeroconf for mDNS
- **Retro**: RetroArch stable cores (NES→PS1), retroarch-assets, controller DB
- **Testing**: pytest, coverage, requests; vitest/jest for UI; Playwright for E2E smoke
- **Lint/Sec**: ruff, mypy (no new Any), eslint, pip-audit, npm audit

## 3) Repository Layout

```
C:\Dev\WomCast
  /apps
    /frontend             # React + Electron app (10-foot UI)
      /src
      /public
      electron/
      package.json
    /backend
      /indexer            # FastAPI svc: USB detect + scan + metadata
      /media              # FastAPI svc: playback orchestrator + Kodi/mpv bridge
      /ai                 # FastAPI svc: Whisper, Ollama, Chroma integration
      /livetv             # FastAPI svc: M3U/HLS ingest/EPG-lite
      /cast               # FastAPI svc: mDNS/WebRTC + phone-mic relay
      /connectors         # FastAPI svc: IA/PBS/NASA/Jamendo adapters
      /common             # shared lib: models, config, logging
      pyproject.toml
  /packages
    /ui-kit               # shared 10-foot components (if needed)
    /proto                # OpenAPI schemas, WS event types
  /build
    /image                # Packer/Shell/Ansible scripts for Pi image build
    /scripts              # boot-time services, systemd unit files, kodi jsonrpc checks
  /docs
    /spec                 # SPECIFICATIONS.md, TASKS.md, TASKS.json (Spec Kit outputs)
    ASBUILT.md
    RUNBOOK.md
    CHANGELOG.md
  /scripts
    /dev                  # task-start.*, task-done.*, lint-all.ps1, perf-checks.ps1
  .github/workflows       # CI pipelines
```

## 4) Service Contracts (APIs)

### Common
- `GET /healthz` → {status, version}
- `GET /version` → semver + build metadata

### indexer
- `POST /v1/scan` → trigger scan; options {path?, full?}
- `GET /v1/items?q=&type=&limit=` → search library
- `GET /v1/items/{id}` → metadata
- `GET /v1/art/{id}` → artwork (cached)

### media
- `POST /v1/play/{id}` → {status, session_id}
- `POST /v1/stop` / `POST /v1/pause` / `POST /v1/resume`
- `GET /v1/player/state` → time, status, track
- Bridge: Kodi JSON-RPC wrapper endpoints under `/v1/kodi/*` (kept internal if possible)

### ai
- `POST /v1/voice/stt` (binary audio) → {text, latency_ms}
- `POST /v1/voice/intent` {text} → {action, args, latency_ms}
- `GET /v1/search/semantic?q=` → ranked items

### livetv
- `POST /v1/m3u/load` (file/url) → {channels}
- `GET /v1/channels` → list
- `POST /v1/channels/{id}/play`

### cast
- `POST /v1/session` → {session_id, pin}
- `POST /v1/session/{id}/pair` {pin} → {ok}
- `WS /ws` → pairing events, remote key events, player state mirror

### connectors
- `POST /v1/{source}/browse` → listing results
- `POST /v1/{source}/play` → resolve free/legal streams

### WebSocket topics (all services may publish via gateway)
- `index.progress`, `player.state`, `cast.paired`, `ai.intent`

## 5) Data Model Sketch

### Library (SQLite)
- **media_items**(id PK, path, kind, title, album, artist, season, episode, year, duration, codecs, hash, added_at, last_played, play_progress, artwork_ref)
- **artwork**(id PK, item_id FK, path, etag, w, h)
- **settings**(key PK, value)
- **channels**(id PK, name, logo, url, group_name, sort_order)
- Simple EPG cache table if needed (optional)

### Chroma Collections
- **media_index** (id=media_id, embeddings from title/metadata/filename)
- **voice_queries** (query text, intent classification traces)

## 6) Build & Image Pipeline

### Local Dev
- `make` or PowerShell scripts to run:
  - `scripts/dev/lint-all.ps1`
  - `apps/backend/*/uvicorn --reload`
  - `apps/frontend vite/electron-forge dev`

### Image Build (Pi OS Lite)
1. Pull base Pi OS Lite image
2. Preinstall: Python 3.11, ffmpeg, kodi (or mpv), retroarch, bluetooth stack, Ollama, whisper runtime, chroma deps
3. Create systemd units:
   - `womcast-indexer.service`, `womcast-media.service`, `womcast-ai.service`, `womcast-livetv.service`, `womcast-cast.service`, `womcast-connectors.service`
   - `womcast-ui.service` (Electron autostart in Xorg/Wayland or kiosk mode)
4. Enable CEC (via Kodi or libcec) + udev rules for USB auto-mount
5. Copy app bundles + config into `/opt/womcast`
6. First-boot script to expand FS, create default settings, run quick self-check
7. Pack as `.img.gz`, tag with semver + UTC build

### Artifacts
- Pi image (.img.gz), logs bundle, SBOM (optional), checksums

## 7) CI/CD Workflows (GitHub Actions)

### lint-test.yml
- **Python**: ruff, mypy (--disallow-any-generics for new code), pytest + coverage
- **Node**: eslint, tsc --noEmit, vitest/jest

### security.yml
- `pip-audit --strict` (fail on high/critical)
- `npm audit --audit-level=high` (fail on high/critical)
- license scan (e.g., pip-licenses + license-checker)

### build-image.yml
- Build backend wheels/containers
- Build Electron package
- Assemble Pi image
- Run smoke: boot scripts (sim), Kodi JSON-RPC ping, healthz on all services

### perf-smoke.yml
- Scripted runs: index 1k sample files (≤5s), Whisper+Ollama round-trip (≤3s), cast mock pairing (≤2s)

### docs.yml
- Verify ASBUILT.md delta present on PRs that touch /apps or /build
- Update CHANGELOG.md on release tags

## 8) Testing Strategy

### Unit Tests
- **indexer**: file scanners, metadata parsing, cache logic
- **media**: player command mapper, session state machine
- **ai**: intent classification, STT glue, semantic query rankers
- **livetv**: M3U parser/validator
- **cast**: PIN workflow, ws events

### Integration Tests
- Fake library (1k mixed files), cold index time
- Kodi JSON-RPC or mpv stub to simulate playback
- Chroma embedding and search ranking

### E2E (Playwright)
- Electron app launches, navigates with keyboard
- Plays sample media, pauses/resumes
- Voice button runs STT→intent→action flow
- Cast pairing happy path

### Performance Tests
- Repeatable timers with warm/cold cache
- Budget regressions fail CI

## 9) Security Controls

- Bind to RFC1918 by default; explicit opt-in for remote exposure
- Optional TLS (self-signed flow documented); cert paths in settings
- PIN pairing (short-lived); rotate tokens; rate-limit pairing attempts
- Validate external URLs (M3U/connector results) against allowlist patterns where possible
- Drop privileges for services (non-root), systemd sandboxing flags

## 10) Milestone Deliverables (Build Plan)

### M1 — System Setup
- Repo skeletons, CI lint/test/security wired
- Electron shell "Hello TV" screen; FastAPI hello services
- Image pipeline bootstrap (can pack a bootable but empty shell)
- Docs scaffolding

### M2 — Storage & Library
- USB auto-mount udev rule + indexer service
- SQLite schema + migrations; artwork cache
- Basic playback via Kodi JSON-RPC (or mpv stub)
- Library browse & details screen

### M3 — Free Streaming + Live TV + Casting + Voice
- Connectors (IA/PBS/NASA/Jamendo) with browse → play
- Live TV M3U/HLS ingest; channel list UI; play
- Cast service (mDNS advert, WebRTC signal); PIN pairing; phone-mic capture
- Whisper small + push-to-talk UX; intent→action across library/connectors

### M4 — Cloud Mapper + CEC Fallback + Server Voice
- Cloud badge/QR flows (passthrough); CEC input switch helper
- Optional server-side voice relay mode (if device mic not used)
- Hardening + error UX; log scrubbing; settings panel (LLM/STT selection)

### M5 — AI Bridge + PWA + Docs
- Ollama model mgmt; Chroma collections; semantic search in UI
- LAN PWA remote (basic control + voice button)
- Docs: ASBUILT, RUNBOOK, CHANGELOG matured

### M6 — Retro + UI Polish + Final Image
- RetroArch cores install & controller mapping UI
- Accessibility checks; reduced motion; keyboard/CEC finalize
- Perf gates finalization; release .img.gz + notes

## 11) Estimation Heuristics

- **M1**: 2–3 days
- **M2**: 5–7 days
- **M3**: 7–10 days
- **M4**: 4–6 days
- **M5**: 5–7 days
- **M6**: 5–7 days

(Adjust when /speckit.tasks expands into granular subtasks.)

## 12) Risk Register (Tech)

- **Kodi vs mpv integration complexity** → Insulate via media adapter; start with Kodi JSON-RPC
- **Whisper/Ollama performance on Pi** → use small models, quantized where possible; pre-warm
- **WebRTC NAT quirks** (LAN should be fine) → keep TURN optional; Phase 2 covers remote
- **USB disk variance** → async index + cancellation; UI progress; cache persist

## 13) Developer Experience

- `scripts/dev/lint-all.ps1` → one-shot lint/test
- `scripts/dev/perf-checks.ps1` → runs index/AI/cast timers locally
- VS Code recommended extensions: Python, Ruff, Pylance, ESLint, Prettier
- Launch configs for Electron and each FastAPI service
- Makefile or PS wrappers for common flows

## 14) Outputs Required for /speckit.tasks

Generate a dependency-ordered task graph with:
- Workstreams: [backend] [ui] [ai] [retro] [ops] [security] [perf] [docs]
- Milestone grouping (M1→M6)
- File path hints for each task (touch points)
- Parallelizable tasks flagged
- Estimated durations and owner placeholders
- Scripts and CI workflow stubs to create (names + paths)
- Acceptance criteria per task referencing perf/UX gates

---
**End of plan.**
