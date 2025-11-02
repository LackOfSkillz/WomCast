# Master Prompt for GitHub Spec Kit
## Project Name
WomCast — Open Entertainment Box

## Objective
Create a local-first entertainment OS for Raspberry Pi 5 (HDMI) that unifies local media, free/public-domain streaming, retro gaming, cloud-service passthrough, AI-powered discovery and voice, phone/tablet casting, and user-added Live TV streams (M3U/HLS/DASH). Deliver a polished, plug-and-play media OS that remains open, secure, and private.

## MVP Deliverables
1. Bootable WomCast Pi5 image (.img.gz)
2. Auto-mount & index USB drives ≤ 5 s
3. Local playback of .mkv .mp4 .avi .flv .swf .mp3 .m4a .flac
4. Free-content connectors (Internet Archive, PBS, NASA, Jamendo)
5. Cloud-service passthrough (badges + QR + CEC)
6. Local AI search & voice (Ollama + Whisper + Chroma)
7. Retro Gaming (NES→PS1 + save states + BT controllers)
8. Live TV (user-added M3U/HLS/DASH)
9. Casting + phone-mic voice input (no DRM detector)
10. Polished 10-foot UI
11. Placeholder Task: Easter Eggs & Personalization — details TBD

## Quality Gates & Definition of Done (REQUIRED)
For each milestone (M1–M6) and tasks:
- Task moves to done only when gates pass in CI; gate results recorded with UTC timestamps + task ID links.

### Global Gate Checklist
1) Build & Lint: ruff, mypy (no new Any), eslint, typecheck, unit tests
2) Security & Compliance: pip-audit/npm audit (no high/critical), license scan, no DRM/extractor modules
3) Pack/Boot Smoke: image builds; Kodi JSON-RPC health OK
4) Performance Budgets: USB index ≤ 5 s (1k items); AI intent RTT ≤ 3 s; Casting setup ≤ 2 s
5) UX/Behavior: nav works; sample files (.mkv/.mp4/.mp3/.flac) + HLS live play
6) Docs & Logs: ASBUILT delta updated; RUNBOOK troubleshooting updated; CHANGELOG "Unreleased" stamped

### Milestone Acceptance (summary)
M1: image boots; Kodi starts; CEC bus detected
M2: USB auto-mount; index 1k ≤ 5 s; covers visible
M3: IA/PBS/NASA/Jamendo playable; M3U/HLS entry; casting; phone-mic intents
M4: Cloud badges; CEC fallback; Whisper server STT ≤ 1.2 s
M5: AI Bridge relevance 3/5; PWA installable; docs updated
M6: Retro cores; PD titles; controller wizard; final .img.gz < 2.5 GB; first-boot wizard OK

### Task Timing Fields (enforced)
Each task/subtask includes: id, title, owner, status, start_at_utc, end_at_utc, duration_h (computed), links, notes. Subtasks include parent_id.

## Documentation & Operational Records (REQUIRED)
Create and maintain:
- docs/ASBUILT.md — "as built" record with Delta Log when design vs implementation diverge.
- docs/RUNBOOK.md — day-2 ops: first boot, common tasks, troubleshooting, backup/restore.
- CHANGELOG.md — Keep a Changelog style, stamped in UTC ISO-8601; initial project stamp at top.

Initial stamps: add UTC project start stamp to CHANGELOG and docs/spec/TASKS.md meta.project_started_at_utc.

Provide scripts:
- scripts/dev/task-start ID — sets start_at_utc if empty.
- scripts/dev/task-done ID — sets end_at_utc, computes duration_h, appends to CHANGELOG under Unreleased/Changed.

## Phase 2 (NOT IN MVP)
WomCast Link — secure remote access via womcast.ai/wamcast.ai using WireGuard or WebRTC (control-only → WG tunnel → WebRTC with STUN/TURN).