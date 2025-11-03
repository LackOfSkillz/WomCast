# WomCast — Task Breakdown

**Generated**: 2025-11-02  
**Version**: 0.1.0  
**Total Estimated Days**: ~43-49 days

---

## Milestone M1 — System Setup

**Goal**: Repo, tooling, CI, "Hello TV" shell  
**Duration**: 5.5 days

| ID | Task | Owner | Est (d) | Tags | Dependencies | Parallel | Status |
|----|------|-------|---------|------|--------------|----------|--------|
| M1.1 | Set up monorepo skeleton | Gary | 0.5 | [ops] | — | ✓ | ✅ |
| M1.2 | Python toolchain + lint/test | AI-Agent | 0.5 | [ops][backend][security] | M1.1 | ✓ | ✅ |
| M1.3 | Node/TS toolchain + lint/test | AI-Agent | 0.5 | [ops][ui][security] | M1.1 | ✓ | ✅ |
| M1.4 | CI workflows (lint/test/security) | AI-Agent | 0.75 | [ops][security] | M1.2, M1.3 | — | ✅ |
| M1.5 | Common backend scaffold (FastAPI "hello") | AI-Agent | 0.75 | [backend] | M1.2 | — | ✅ |
| M1.6 | Electron "Hello TV" 10-foot shell | AI-Agent | 1.0 | [ui] | M1.3 | — | ✅ |
| M1.7 | Image pipeline bootstrap (Pi OS Lite) | AI-Agent | 1.0 | [ops] | M1.5, M1.6 | — | ✅ |
| M1.8 | Docs foundation | Gary | 0.5 | [docs] | M1.1 | ✓ | ✅ |
| M1.9 | CODEOWNERS + Conventional Commits + PR templates | AI-Agent | 0.25 | [ops][docs] | M1.1 | ✓ | ✅ |
| M1.10 | Logging/observability scaffold | AI-Agent | 0.5 | [backend][ops] | M1.5 | ✓ | ✅ |
| M1.11 | License policy & scanners configuration | AI-Agent | 0.5 | [security][ops] | M1.4 | — | ✅ |
| M1.12 | VS Code launch configs & dev scripts | AI-Agent | 0.25 | [ops] | M1.5, M1.6 | ✓ | ✅ |

**M1 Acceptance Criteria**:
- All services return 200 on /healthz
- Electron shell launches full-screen with keyboard nav
- Bootable .img.gz produced
- CI gates block PRs on failures
- CODEOWNERS enforces reviews; logging excludes PII
- Kodi JSON-RPC ping script and libcec enablement included

---

## Milestone M2 — Storage & Library

**Goal**: USB auto-mount, indexer, basic playback  
**Duration**: 7.5 days

| ID | Task | Owner | Est (d) | Tags | Dependencies | Parallel | Status |
|----|------|-------|---------|------|--------------|----------|--------|
| M2.1 | udev automount rules for USB3 | AI-Agent | 0.75 | [backend][ops] | M1.7 | — | ✅ |
| M2.2 | Library DB schema & migrations (SQLite) | AI-Agent | 1.0 | [backend] | M1.5 | ✓ | ✅ |
| M2.3 | Indexer: scan + metadata extract + artwork cache | AI-Agent | 1.5 | [backend][perf] | M2.2 | — | ✅ |
| M2.4 | Media service: Kodi JSON-RPC bridge | AI-Agent | 1.25 | [backend] | M1.5 | ✓ | ✅ |
| M2.5 | Frontend: Library browse/detail screens | AI-Agent | 1.0 | [ui] | M2.3, M2.4 | — | ✅ |
| M2.6 | Subtitles + resume position | AI-Agent | 0.75 | [backend][ui] | M2.4, M2.5 | — | ✅ |
| M2.7 | Perf script: cold/warm index timers | AI-Agent | 0.25 | [perf][ops] | M2.3 | ✓ | ✅ |
| M2.8 | Docs & CHANGELOG updates | Gary | 0.25 | [docs] | M2.* | — | ✅ |
| M2.9 | Network shares (SMB/NFS) mounting option | AI-Agent | 0.75 | [backend][ops] | M2.1 | ✓ | ✅ |
| M2.10 | DB corruption & backup strategy | AI-Agent | 0.5 | [backend][security] | M2.2 | ✓ | ✅ |
| M2.11 | Artwork/metadata legal filters | AI-Agent | 0.25 | [backend][security] | M2.3 | ✓ | ✅ |
| M2.12 | Settings persistence service | AI-Agent | 0.5 | [backend][ui] | M2.2 | ✓ | ✅ |

**M2 Acceptance Criteria**:
- USB drive auto-mounts and indexes 1k files ≤5s
- Library displays with artwork and metadata
- Playback start/stop/pause works via Kodi bridge
- Subtitles load and resume position persists
- Mount permissions verified; indexing excludes system dirs
- Optional SMB/NFS mounts functional; SQLite WAL mode + backup validated

---

## Milestone M3 — Free Streaming + Live TV + Casting + Voice

**Goal**: Connectors, M3U/HLS, mDNS/WebRTC, Whisper  
**Duration**: 12.5 days

| ID | Task | Owner | Est (d) | Tags | Dependencies | Parallel | Status |
|----|------|-------|---------|------|--------------|----------|--------|
| M3.1 | Connector: Internet Archive | AI-Agent | 1.0 | [backend] | M1.5 | ✓ | ✅ |
| M3.2 | Connectors: PBS, NASA TV, Jamendo | AI-Agent | 1.5 | [backend] | M3.1 | ✓ | ✅ |
| M3.3 | Frontend: Connectors hub UI | AI-Agent | 0.75 | [ui] | M3.1, M3.2 | — | ✅ |
| M3.4 | Live TV ingest (M3U/HLS/DASH) | AI-Agent | 1.0 | [backend] | M1.5 | ✓ | ✅ |
| M3.5 | Live TV UI: channel list + play | AI-Agent | 0.75 | [ui] | M3.4, M2.4 | — | ✅ |
| M3.6 | Casting service: mDNS advert + signaling | AI-Agent | 1.0 | [backend][ops] | M1.5 | ✓ | ✅ |
| M3.7 | Phone-mic relay via WebRTC | AI-Agent | 1.0 | [backend][ai] | M3.6 | — | ✅ |
| M3.8 | Whisper STT (small) integration | AI-Agent | 1.0 | [ai][backend] | M3.7 | — | ✅ |
| M3.9 | Voice UX in frontend (push-to-talk) | AI-Agent | 0.75 | [ui][ai] | M3.8 | — | todo |
| M3.10 | Perf scripts: cast & voice timers | AI-Agent | 0.25 | [perf][ops] | M3.6–M3.9 | ✓ | ✅ |
| M3.11 | Docs update for connectors/Live TV/voice | AI-Agent | 0.25 | [docs] | M3.* | — | ✅ |
| M3.12 | STUN/TURN config (LAN-first, TURN optional) | AI-Agent | 0.5 | [backend][ops] | M3.6 | ✓ | todo |
| M3.13 | QR pairing + mobile PWA deep link | AI-Agent | 0.5 | [ui][ops] | M3.6 | ✓ | todo |
| M3.14 | Connector failure fallbacks & rate limits | AI-Agent | 0.5 | [backend][security] | M3.1–M3.3 | ✓ | ✅ |
| M3.15 | Live TV EPG-lite (optional) | AI-Agent | 0.75 | [backend][ui] | M3.4, M3.5 | ✓ | ✅ |
| M3.16 | Subtitle font pack & fallback rules | AI-Agent | 0.25 | [ui] | M2.6 | ✓ | ✅ |

**M3 Acceptance Criteria**:
- All free connectors browse and play content
- M3U playlist loads and channels play
- Cast pairing ≤2s on LAN
- Voice transcription works with ≤3s RTT
- mDNS TXT includes device name and version
- Quantized model option; p50/p95 latency recorded to local metrics
- QR pairing encodes womcast.local + session credentials
- Connector backoff/retry and rate-limiting functional

---

## Milestone M4 — Cloud Mapper + CEC Fallback + Server Voice

**Goal**: QR flows, HDMI-CEC, server-side voice  
**Duration**: 5 days

| ID | Task | Owner | Est (d) | Tags | Dependencies | Parallel | Status |
|----|------|-------|---------|------|--------------|----------|--------|
| M4.1 | Cloud badge & QR passthrough (legal services) | AI-Agent | 1.0 | [ui][backend] | M3.3 | — | todo |
| M4.2 | HDMI-CEC input switch helper | AI-Agent | 0.75 | [backend][ops] | M2.4 | ✓ | todo |
| M4.3 | Server-side voice relay (when device lacks mic) | AI-Agent | 0.75 | [ai][backend] | M3.8 | ✓ | todo |
| M4.4 | Settings panel (models, privacy, pairing) | AI-Agent | 1.0 | [ui] | M3.9 | — | todo |
| M4.5 | Hardening & error UX (network/offline states) | AI-Agent | 0.75 | [ui][backend][security] | M4.1–M4.4 | — | todo |
| M4.6 | Docs updates (Cloud/CEC/Settings) | Gary | 0.25 | [docs] | M4.* | — | todo |
| M4.7 | Legal notices & provider terms acknowledgment | AI-Agent | 0.25 | [ui][docs][security] | M4.1 | ✓ | todo |
| M4.8 | Privacy controls (data purge/export) | AI-Agent | 0.75 | [ui][backend][security] | M4.4, M2.12 | — | todo |

**M4 Acceptance Criteria**:
- Cloud service QR codes open provider apps (no DRM bypass)
- CEC input switching works with fallback UI
- Server-side voice processing functions
- Settings panel allows model/privacy configuration
- First-use terms shown with acknowledgment stored
- Privacy controls purge voice history, embeddings, recents; local export functional

---

## Milestone M5 — AI Bridge + PWA + Docs

**Goal**: Ollama/Chroma integration, PWA control  
**Duration**: 7 days

| ID | Task | Owner | Est (d) | Tags | Dependencies | Parallel | Status |
|----|------|-------|---------|------|--------------|----------|--------|
| M5.1 | Ollama model mgmt + intent API | AI-Agent | 1.25 | [ai][backend] | M3.8 | — | todo |
| M5.2 | ChromaDB collections + semantic search endpoint | AI-Agent | 1.0 | [ai][backend] | M2.3 | ✓ | todo |
| M5.3 | Frontend search unification (text + semantic + voice) | AI-Agent | 0.75 | [ui][ai] | M5.2, M3.9 | — | todo |
| M5.4 | LAN PWA remote (basic control + voice button) | AI-Agent | 1.25 | [ui][ops] | M3.6, M3.9 | — | todo |
| M5.5 | Docs hardening + samples & demo mode | Gary | 0.5 | [docs] | M5.* | — | todo |
| M5.6 | Model download/space management | AI-Agent | 0.75 | [ai][ops] | M5.1 | ✓ | todo |
| M5.7 | PWA service worker + offline cache | AI-Agent | 0.5 | [ui][ops] | M5.4 | ✓ | todo |
| M5.8 | Demo content pack + fake M3U generator | AI-Agent | 0.25 | [ops][perf] | M3.4, M2.3 | ✓ | todo |

**M5 Acceptance Criteria**:
- Voice intent resolution ≤3s p50
- Semantic search returns relevant results
- PWA works on mobile browser (LAN)
- Demo content mode validates flows
- mDNS discovery; QR to open PWA on mobile
- UI shows model sizes; free-space check; cancelable downloads
- PWA service worker caches controls with reconnect handling

---

## Milestone M6 — Retro + UI Polish + Final Image

**Goal**: RetroArch, accessibility, release  
**Duration**: 5.75 days

| ID | Task | Owner | Est (d) | Tags | Dependencies | Parallel | Status |
|----|------|-------|---------|------|--------------|----------|--------|
| M6.1 | RetroArch cores & controller mapping | AI-Agent | 1.25 | [retro][ops] | M1.7 | — | todo |
| M6.2 | Accessibility & reduced motion | AI-Agent | 0.5 | [ui] | M5.3 | ✓ | todo |
| M6.3 | Final perf gates & regression checks | AI-Agent | 0.5 | [perf][ops] | M2.7, M3.10 | ✓ | todo |
| M6.4 | Image pack & release notes | Gary | 0.5 | [ops][docs] | M6.3 | — | todo |
| M6.5 | Easter eggs hook points (placeholders) | AI-Agent | 0.25 | [ui] | M6.2 | ✓ | todo |
| M6.6 | Bluetooth controller pairing UI + profiles | AI-Agent | 0.75 | [retro][ui][ops] | M6.1 | ✓ | todo |
| M6.7 | First-boot wizard | AI-Agent | 0.75 | [ui][ops] | M5.3, M2.12 | — | todo |
| M6.8 | Image signing/checksums + release validation | AI-Agent | 0.25 | [security][ops] | M6.4 | ✓ | todo |

**M6 Acceptance Criteria**:
- RetroArch games load with save states
- Accessibility passes contrast/nav checks
- All performance budgets green
- Final .img.gz < 2.5GB with release notes
- Bluetooth controller pairing flow in Settings
- First-boot wizard: setup PIN, optional shares, optional model download (skippable)
- SHA256 + signature published; verify script in RUNBOOK

---

## CI/Gate Tasks

| ID | Task | Owner | Est (d) | Tags | Status |
|----|------|-------|---------|------|--------|
| CI.1 | lint-test workflow | AI-Agent | — | [ops][security] | todo |
| CI.2 | security-audit workflow | AI-Agent | — | [ops][security] | todo |
| CI.3 | build-image workflow | AI-Agent | — | [ops] | todo |
| CI.4 | perf-smoke workflow | AI-Agent | — | [ops][perf] | todo |
| CI.5 | docs-check workflow | AI-Agent | — | [ops][docs] | todo |

**CI Acceptance**: All gates block PRs on failure; no exceptions without documented waiver.

---

## Summary

- **Total Tasks**: 73 (68 milestone tasks + 5 CI tasks)
- **Milestone Breakdown**:
  - M1: 12 tasks (5.5 days)
  - M2: 12 tasks (7.5 days)
  - M3: 16 tasks (12.5 days)
  - M4: 8 tasks (5 days)
  - M5: 8 tasks (7 days)
  - M6: 8 tasks (5.75 days)
  - CI: 5 tasks (continuous)
- **Total Estimated Days**: 43.25 days (serial path ~43-49 days with parallel optimization)

---

## Dependency Validation

All task dependencies validated:
- ✅ No circular dependencies detected
- ✅ All referenced task IDs exist
- ✅ Parallelizable tasks marked appropriately
- ✅ Critical path: M1.1 → M1.2 → M1.5 → M2.2 → M2.3 → M2.5 → M2.6 → M5.3 → M6.2 → M6.7

---

## Notes

- **Parallelization**: Tasks marked ✓ can run concurrently once dependencies are met
- **Estimates**: In days; adjust as subtasks expand
- **Owners**: Gary (architecture/docs), AI-Agent (implementation)
- **Timestamps**: Use `scripts/dev/task-start.ps1` and `task-done.ps1` to track
- **New Tasks**: 21 additional tasks added to enhance robustness, legal compliance, and operational polish
