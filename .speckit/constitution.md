# WomCast — Project Constitution (Spec-Driven Development Guardrails)

## 1) Mission & Non-Goals

**Mission**: Build a local-first, privacy-respecting entertainment OS for Raspberry Pi 5 with a polished 10-foot UI, free-content connectors, legal cloud passthrough, live TV, retro gaming, casting, and on-device AI voice/search.

**Non-Goals**:
- No DRM bypass or gray-area content
- No phone-home telemetry by default
- No feature creep beyond MVP scope (Phase 2 "WomCast Link" excluded from MVP)

## 2) Product Pillars

- **Local-first & private** (LAN by default, optional TLS, PIN pairing)
- **Performance** (boot ≤15s; index ≤5s/1k; AI RTT ≤3s; cast setup ≤2s)
- **Reliability** (offline-friendly; graceful degradation)
- **Legality & Ethics** (licensed or public-domain only; passthrough for paid services)
- **Delightful 10-foot UX** (remote/keyboard/CEC friendly; big targets; clear typography)

## 3) Target Platforms & Support Matrix (MVP)

- **Primary**: Raspberry Pi 5 (8 GB), HDMI 2.0
- **OS Base**: LibreELEC or Raspberry Pi OS Lite
- **Extended** (best effort): Desktop builds (Windows/macOS/Linux) for dev/testing only

## 4) Architecture Guardrails

- **Frontend**: React + Electron or Kodi Skin UI (choose one per build flavor; avoid split-brain UX)
- **Backend Services**: FastAPI (Python 3.11) micro-services (USB indexer, media API, AI bridge)
- **AI**: Ollama (local LLM), Whisper STT, ChromaDB for semantic search
- **Media/Live TV**: FFmpeg, HLS/DASH parser; user-supplied M3U playlists only
- **Retro**: RetroArch cores (NES→PS1) with save states, BT controllers
- **Casting**: mDNS + WebRTC + local pairing; optional phone mic input
- **Storage**: USB SSD/HDD; optional SMB/NFS network shares
- **Security**: LAN-only by default; no telemetry; PIN pairing; optional TLS; minimal privileges

## 5) Quality Gates (All Milestones M1–M6)

1. **Build/Lint**: ruff + mypy (no new Any), eslint + TS typecheck, unit tests ≥70% line coverage on changed code
2. **Security**: pip-audit + npm audit (no high/critical); license scan (no forbidden licenses)
3. **Pack/Boot Smoke**: Image builds; Kodi JSON-RPC ping OK; services start without errors
4. **Performance**: Index ≤5s/1k items; AI RTT ≤3s; cast setup ≤2s (measured via scripts)
5. **UX/Behavior**: Keyboard & CEC navigation; sample playback tests pass; accessibility checks (contrast, focus order)
6. **Docs**: docs/ASBUILT.md updated (delta log), docs/RUNBOOK.md (ops + troubleshooting), CHANGELOG.md (UTC, Keep-a-Changelog)

## 6) Definition of Done (DoD)

A story/PR is done when:
- Acceptance Criteria met; code + tests + docs included
- All Quality Gates pass locally and in CI
- Backward compatibility honored (unless major bump with migration notes)
- CHANGELOG.md entry present; ASBUILT delta appended (what changed, why)
- Feature flags or config defaults maintain safe behavior (LAN-only; no telemetry)

## 7) Branching, Reviews, and CI/CD

- **Branching**: main is stable; feature branches use conventional prefixes (feat/, fix/, chore/, docs/, perf/, refactor/)
- **Commits**: Conventional Commits. PRs squash-merge with meaningful titles
- **Reviews**: At least 1 human review for non-trivial changes. Security-sensitive changes require 2 approvals
- **CI**: GitHub Actions gates for build/lint/test/security/license; artifacts: image, deb/zip, SBOM (if available)

## 8) Coding Standards

- **Python**: PEP8 via ruff; type hints enforced by mypy (no new Any); pytest for tests
- **Node/TS/React**: eslint + tsc --noEmit; vitest or jest for tests; Storybook for UI where helpful
- **Config**: .env for local only; secrets via OS keyring or GitHub Actions secrets (never commit secrets)
- **Logging**: Structured logs; no PII; configurable verbosity

## 9) Security & Privacy

- **Principles**: Least privilege; defense in depth; no default remote reachability
- **Data**: No collection of viewing habits, IDs, or analytics by default. Local preferences stored on device; optional export/import
- **Network**: TLS optional; verify certificates if enabled; QR pairing uses short-lived tokens
- **Threats**: MITM on LAN, rogue playlists, malformed media. Validate and sandbox where possible

## 10) Testing Strategy

- **Unit**: ≥70% on changed code; deterministic media/AI stubs
- **Integration**: Playback pipelines, indexer timing, AI round-trip latency
- **E2E (smoke)**: First boot, USB index, play sample files, run voice query, cast handshake
- **Performance**: Automated timers for index/AI/cast; regression thresholds enforced

## 11) Performance Budgets

- **Boot to UI**: ≤15s (Pi 5, clean image, minimal services)
- **Library index**: ≤5s for 1k items (USB 3.0 SSD)
- **AI RTT (voice→intent)**: ≤3s local
- **Cast setup**: ≤2s (same LAN, typical phone)

## 12) Dependencies & Licensing

- **Allow**: MIT/Apache-2/BSD/MPL; GPL okay only when isolated and compatible with distro goals
- **Deny**: Unknown or restricted licenses; code with DRM circumvention
- **Scan**: Automated license check in CI; PR blocked on violations

## 13) Documentation Requirements

- **docs/ASBUILT.md** (system as-built + deltas per PR)
- **docs/RUNBOOK.md** (first boot, operations, troubleshooting, rollback)
- **CHANGELOG.md** (UTC timestamps; Keep-a-Changelog)
- **docs/spec/** → SPECIFICATIONS.md, TASKS.md, TASKS.json
- Each task tracks start_at_utc, end_at_utc, duration_h, status

## 14) Observability & Supportability

- **Metrics**: Minimal local counters (index time, AI RTT, cast time)
- **Health checks**: /healthz endpoints for services; Kodi JSON-RPC ping
- **Crash handling**: Safe restart; user-visible error state; no sensitive logs

## 15) UX Principles (10-Foot)

- Readable at distance (min 18–24px base), strong contrast, large focus states
- Remote/keyboard/CEC first; minimal text entry
- Clear empty states; progress indicators for indexing/casting/AI

## 16) Accessibility

- Keyboard and remote navigability; high-contrast option; screen-reader hints where applicable
- Avoid motion sickness; provide reduced motion toggle

## 17) Internationalization (stretch)

- English default; architecture allows locale packs; date/time and number formatting via i18n lib

## 18) Release & Versioning

- **SemVer**: MAJOR.MINOR.PATCH, images tagged with build metadata + UTC
- **Release notes**: Summaries + upgrade/migration steps
- **Rollback**: Prior image retained; RUNBOOK includes rollback steps

## 19) Risk Register (MVP)

- **Media/licensing**: Strict filters; user-provided playlists only
- **Performance regressions**: CI perf gates; bisect scripts
- **Hardware variance**: Constrain to Pi 5 for MVP; document known issues on other hosts

## 20) Phase Boundaries

- **MVP (M1–M6)**: Everything above except remote access
- **Phase 2**: WomCast Link (WireGuard + WebRTC) for secure remote control/playback
- **Phase 3**: Easter eggs & personalization honoring Mathew Wombacker (fun but safe)

## Enforcement

Any PR that violates this constitution (quality gates, security, licensing, privacy, or scope) must be revised before merge. Exceptions require a clearly documented waiver in the PR, approved by the maintainer.

## Ownership

**Project maintainer**: Gary (WomCast)  
**Reviewer pool**: Contributors designated in CODEOWNERS
