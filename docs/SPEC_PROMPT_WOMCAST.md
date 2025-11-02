# WomCast — Full Specification Prompt (Generate Plan & Tasks from this)

## 0) Project Snapshot

**Name**: WomCast (Wombacker Cast)  
**Tagline**: A local-first, AI-assisted entertainment OS for Raspberry Pi 5 with a polished 10-foot UI.  
**Primary Device**: Raspberry Pi 5 (8GB), HDMI 2.0  
**Base OS**: LibreELEC or Raspberry Pi OS Lite  
**Goal**: Deliver a private, fast, legal alternative to Roku/Fire TV/Apple TV—focused on local media, free/public-domain streaming, legal cloud passthrough, retro gaming, live TV, casting, and on-device voice/AI search.  
**Operating Mode**: LAN-only by default, no telemetry, PIN pairing, optional TLS.

## 1) Objectives & Non-Goals

### Objectives
- Bootable Pi image that launches a clean, modern 10-foot UI
- Auto-mount USB and index ≤5s for ~1,000 items
- Smooth playback for major media formats; simple, resilient Live TV via user M3U/HLS/DASH
- Free/public-domain content connectors: Internet Archive, PBS, NASA TV, Jamendo
- Legal cloud service passthrough (Prime/Netflix/Hulu/Disney+/YouTube) via QR sign-in and/or HDMI-CEC input switching—not DRM bypass
- Local AI: Whisper STT + Ollama LLM + ChromaDB search with ≤3s voice round-trip
- Casting + optional phone-mic input; Retro gaming (NES→PS1) via RetroArch; BT controllers
- CI gates for quality, security, performance, and docs

### Non-Goals
- No DRM cracking, piracy, or gray-area "scrapers"
- No default telemetry; no cloud lock-in
- Phase 2 "WomCast Link" (remote access) is out of MVP

## 2) Users, UX & Accessibility

### Users
- Household viewers using remote/keyboard/CEC
- Tinkerers deploying Pi images

### 10-Foot UX
- React/Electron or Kodi Skin (choose one per build flavor)
- Big targets, high contrast, minimal typing, keyboard/CEC navigation
- Key screens: Home, Library, Search (voice + text), Connectors, Live TV, Retro, Settings
- Accessibility: reduced motion toggle, strong focus rings, screen-reader hints where feasible

## 3) Scope (MVP Features)

- Local playback: .mkv, .mp4, .avi, .flv, .swf, .mp3, .m4a, .flac
- Auto-mount + index USB (≤5s/1k items), artwork/metadata fetch (legal sources)
- Free/public-domain connectors: Internet Archive, PBS, NASA TV, Jamendo
- Cloud passthrough: badges, QR sign-in redirects, HDMI-CEC input switch helper
- Live TV: user M3U/HLS/DASH playlists
- Voice & AI: Whisper STT (on-device), Ollama LLM, ChromaDB semantic search
- Casting: mDNS discovery + WebRTC pairing; optional phone-mic voice input
- Retro: RetroArch cores (NES→PS1), save states, BT controllers
- Security defaults: LAN-only, PIN pairing, optional TLS
- Performance budgets: Boot ≤15s; Index ≤5s/1k; AI RTT ≤3s; Cast setup ≤2s
- Docs: ASBUILT delta, RUNBOOK, CHANGELOG; task timestamping

### Out of MVP (Phase 2)
- WomCast Link (remote access via WireGuard + WebRTC/STUN/TURN)
- App Store/Marketplace
- Non-Pi desktop builds as official targets (dev/testing only for MVP)

## 4) Architecture & Components

### Frontend
- **Option A**: React + Electron (TypeScript), 10-foot UI components, CEC/keyboard navigation
- **Option B**: Kodi Skin UI with JSON-RPC integration
- PWA shell for local control on LAN (Phase M5)

### Backend (FastAPI, Python 3.11)
- **USB Indexer Service**: auto-mount detect, scan media, extract metadata, hash & cache, artwork; exposes /media/* APIs
- **Media Playback Bridge**: orchestrates ffmpeg/mpv/kodi JSON-RPC; handles playlists, resume, subtitles
- **AI Bridge**: Whisper (STT), Ollama (LLM), ChromaDB (embeddings/search); voice intent → action routing
- **Live TV Service**: ingest M3U/HLS/DASH, validate/clean, program guide basics
- **Casting/Pairing Service**: mDNS advert, WebRTC signaling, PIN pairing, phone-mic capture relay
- **Connector Modules**: Internet Archive, PBS, NASA, Jamendo (HTTP+legal APIs)

### Media/Playback
- ffmpeg/libav; mpv or Kodi player integration
- Subtitle support (srt/vtt/ass); audio tracks; resume position

### Retro
- RetroArch cores and per-core configs; controller mapping; save states

### Storage
- **Library DB**: SQLite (media index, artwork cache, playstate)
- **Vector DB**: ChromaDB (local embeddings for semantic search)
- **Config & Secrets**: local .env (dev only), production via env vars; never commit secrets

### Security
- LAN-only by default (bind to RFC1918)
- Optional TLS with local certs
- PIN pairing; short-lived tokens for casting/QR flows
- Input validation on playlists/URLs

## 5) APIs (Illustrative)

- `GET /healthz` → status
- `POST /v1/index/scan` → trigger/refresh scan
- `GET /v1/media/search?q=...` → results (text + semantic)
- `GET /v1/media/{id}` → metadata
- `POST /v1/play/{id}` → begin playback
- `POST /v1/voice/stt` (binary audio) → transcript
- `POST /v1/voice/intent` (text) → {action, args}
- `POST /v1/cast/session` → {session_id, pin}
- `POST /v1/connector/{source}/browse` → listings
- `POST /v1/livetv/load_m3u` (file/url) → channels
- `GET /v1/settings` / `PUT /v1/settings` → config (PII-free)

### Events/WebSocket
- `/ws` for player state, indexing progress, cast pairing, AI intent status

## 6) Data Model (high level)

- **MediaItem** {id, path, type, title, album, artist, year, duration, codecs, artwork_ref, hash, added_at, last_played, play_progress}
- **Channel** {id, name, logo, stream_url, group, epg_ref}
- **ConnectorItem** {id, source, title, description, url, media_type, thumb}
- **VoiceQuery** {id, ts, transcript, intent, latency_ms}
- **CastSession** {id, pin, created_at, expires_at, paired_device}
- **Settings** {ui_theme, network, security, llm_model, stt_model, retro_profiles, cec_enabled, ...}

## 7) Performance & Reliability

- Boot to UI ≤15s (Pi 5, clean image)
- Index ≤5s for 1k items on USB3 SSD
- AI voice intent ≤3s (audio→intent)
- Cast setup ≤2s on same LAN
- Graceful degradation: if AI offline, fallback to text search; if connectors fail, keep local library

## 8) Quality, Security, Licensing

### Quality Gates (CI & local)
- **Build/Lint**: ruff + mypy (no new Any), eslint + TS typecheck, unit tests
- **Security**: pip-audit + npm audit (no high/critical); dependency license scan
- **Pack/Boot Smoke**: image build + Kodi JSON-RPC ping
- **Perf scripts**: index/AI/cast timers; thresholds enforced
- **UX checks**: keyboard/CEC nav; sample media tests

### Licenses
- Prefer Apache-2/MIT/BSD/MPL. Avoid unknown/incompatible. No DRM circumvention.

## 9) Deliverables & Documentation

- **Image**: .img.gz for Pi 5
- **Repos**: FastAPI backend, Frontend app, build scripts
- **Docs**: docs/ASBUILT.md (delta log), docs/RUNBOOK.md (ops/troubleshooting/rollback), CHANGELOG.md (UTC, Keep-a-Changelog)
- **Spec Artifacts**: docs/spec/SPECIFICATIONS.md, TASKS.md, TASKS.json
- **Helper Scripts**: scripts/dev/task-start.*, scripts/dev/task-done.*
- **Timestamps in tasks**: start_at_utc, end_at_utc, duration_h, status

## 10) Milestones (M1 → M6)

- **M1 System Setup**: repo, tooling, CI, base image scaffold
- **M2 Storage & Library**: auto-mount/index, artwork cache, DB, basic playback
- **M3 Free Streaming + Live TV + Casting + Voice**: connectors, M3U/HLS, mDNS/WebRTC, Whisper
- **M4 Cloud Mapper + CEC Fallback + Server Voice**: QR flows, HDMI-CEC helper, server-side voice bridge
- **M5 AI Bridge + PWA + Docs**: Ollama/Chroma integration, PWA control, docs solidified
- **M6 Retro + UI Polish + Final Image**: RetroArch, BT controllers, accessibility, final perf gates

## 11) Repo Layout (proposed)

```
C:\Dev\WomCast
  /apps
    /frontend      # React/Electron (or Kodi skin assets if chosen)
    /backend       # FastAPI services (indexer, media, AI, casting, liveTV)
  /packages
    /ui-kit        # shared 10-foot components (if React flavor)
    /proto         # openapi schemas, ws event types
  /build
    /image         # Pi image build scripts (LibreELEC or Pi OS Lite base)
  /docs
    /spec          # SPECIFICATIONS.md, TASKS.md, TASKS.json (autogenerated by Spec Kit)
    ASBUILT.md
    RUNBOOK.md
    CHANGELOG.md
  /scripts
    /dev           # task-start.*, task-done.*, perf-checks, lint-all
  .github/workflows
```

## 12) Risks & Mitigations

- **Performance misses on Pi 5**: use async IO, avoid heavy Node processes at boot; cache artwork; defer non-critical tasks
- **Audio/codec drift**: rely on ffmpeg/mpv/Kodi; provide codec error UX
- **Connector API changes**: adapter pattern; feature flags; graceful fallback to local
- **Licensing pitfalls**: automated scans; restricted deps list
- **Voice latency spikes**: keep models local; quantized Whisper; prompt/LLM tuning; pre-warm

## 13) Acceptance Criteria (MVP)

- Boots to UI ≤15s; library index ≤5s/1k; AI RTT ≤3s; cast ≤2s
- Plays listed formats; Live TV from valid M3U/HLS; free connectors browse & play
- Voice search finds items; intents navigate/play or open connectors
- Retro games load; controllers map; save states work
- All CI gates green; docs updated; changelog entries exist

## 14) Ask to Planner/Tasks Generator

- Produce a dependency-ordered task breakdown across M1–M6, grouping backend/frontend/build/docs
- Include parallelizable tasks, estimates, owner placeholders, and tags ([backend] [ui] [ai] [retro] [ops] [security] [perf] [docs])
- Emit both human-readable TASKS.md and machine-readable TASKS.json with timestamps fields ready
- Generate CI workflows (lint/test/security/perf smoke) and perf scripts stubs
- Propose a minimal "Hello TV" React/Electron (or Kodi skin) shell with keyboard/CEC nav to validate 10-foot patterns early (M1 exit)

## 15) Extras to Seed the Plan

- Prefer React/Electron flavor for MVP (we can keep a Kodi skin path as alt build later)
- Ollama default model: small, fast local model for intents; allow swapping via Settings
- Whisper small/medium selectable; default to small for latency
- Chroma collections: media_index, voice_queries
- Include a Demo Content Mode (sample media + sample M3U) to validate flows in CI smoke
