# Changelog

All notable changes to this project will be documented here. Timestamps are UTC (ISO-8601).

## [Unreleased] - 2025-11-02T21:00:00.0000000Z

### M2.5: Frontend Library browse/detail screens (Complete) - 2025-11-02
**Duration**: ~1.5 hours (estimated 1.0 day)  
**Task**: M2.5 - Frontend: Library browse/detail screens

#### Implementation
- **LibraryView**: Main container component with grid + detail pane layout
  - State management for media list, filtered results, selected item
  - Loading and error states with user-friendly messages
  - Responsive layout: grid on left, detail pane on right
- **MediaGrid**: Responsive grid layout component
  - Auto-filling grid (280px minimum column width, 1fr max)
  - Keyboard navigation support for 10-foot UI
  - Empty state handling
- **MediaCard**: Individual media item card
  - Artwork placeholder with media type icons (🎬🎵📷🎮)
  - Duration display overlay
  - Resume position progress bar
  - File size and play count metadata
  - Hover and focus states
- **DetailPane**: Full metadata display panel
  - File information section (type, size, duration, resolution, play count)
  - Video metadata section (title, year, genre, director, rating, plot)
  - Audio metadata section (title, artist, album, year, genre, track number)
  - Resume position indicator with progress bar
  - Play button that calls playback API
- **SearchBox**: Text search with debouncing
  - 300ms debounce for performance
  - Live filtering as user types
  - Clear button (X) for quick reset
  - Keyboard shortcuts (Escape to clear)
  - Fallback to client-side filtering if API fails

#### API Service Layer
- **api.ts**: Complete backend integration (211 lines)
  - Type-safe interfaces: MediaFile, VideoMetadata, AudioMetadata, PlayerState, MediaItem
  - Metadata API: getMediaFiles(), searchMediaFiles(), getMediaItem()
  - Playback API: playMedia(), stopPlayback(), pausePlayback(), seekPlayback(), getPlayerState()
  - Utility functions: formatDuration() (HH:MM:SS), formatFileSize() (KB/MB/GB/TB)
  - Environment configuration: VITE_METADATA_API_URL, VITE_PLAYBACK_API_URL
  - Proper error handling and async/await patterns

#### Styling
- **10-foot UI optimized**: Large text, clear focus states, keyboard navigation
- **Dark theme**: #1a1a1a background, #2a2a2a cards, #0078d4 accents
- **Responsive design**: Grid layout adapts to screen size (1200px, 768px breakpoints)
- **Total CSS**: 5 component stylesheets (441 lines total)

#### Testing
- LibraryView.test.tsx: Basic component rendering tests with API mocking
- App.test.tsx: Updated for new LibraryView integration
- All tests passing with vitest

#### Quality Assurance
- ✅ ESLint: Clean (strict TypeScript rules, no-floating-promises, restrict-template-expressions)
- ✅ TypeScript: Clean (strict mode, noUncheckedIndexedAccess, proper types)
- ✅ Pre-commit hooks: All checks passed
- ✅ Acceptance Criteria:
  - Grid view with artwork ✓ (placeholder icons, responsive grid)
  - Search box (text) ✓ (debounced, live filtering)
  - Details pane shows metadata ✓ (file info, video/audio metadata, resume position)
  - Play action calls media API ✓ (playMedia() from api.ts)

## [Unreleased] - 2025-11-02T16:30:00.0000000Z

### M1: System Setup (Complete) - 2025-11-02
**Duration**: ~1.5 hours (estimated 5.5 days, high parallelization)  
**Tasks Completed**: M1.1 through M1.12 (12/12)

#### Infrastructure
- Monorepo structure established (apps/, packages/, build/, docs/spec/)
- Python 3.11+ toolchain: FastAPI, ruff, mypy, pytest with 100% coverage
- Node.js 20 toolchain: React 18, TypeScript 5, Vite 6, Vitest, ESLint strict
- CI/CD: GitHub Actions workflows for lint/test/security (pip-audit, npm audit, license check)
- Pre-commit hooks: Quality gates enforcing ruff/mypy/eslint/tsc before commit

#### Services
- Backend: 5 FastAPI microservices (gateway, metadata, playback, voice, search)
- Shared health module: GET /healthz and GET /version endpoints
- Frontend: Electron 31 + React 18 app with main/preload/renderer architecture
- All services pass type checks, linting, and unit tests

#### Deployment
- Dockerfile: Debian Bookworm base for Pi OS Lite, Python + Node + Kodi + GPU drivers
- docker-compose.yml: Full stack with 6 services (5 WomCast + Ollama)
- Environment config: 157-line .env.template with all service settings
- Documentation: Comprehensive README with setup/deployment/troubleshooting

#### Quality Assurance
- Test coverage: Python 100% (2 tests), Node.js 100% (3 tests)
- Static analysis: ruff (E/W/F/I/B/C4/UP), mypy (strict), eslint (TypeScript strict)
- Security: Automated audits fail on high/critical CVEs
- ASBUILT.md: Living document with 5 deviations documented

### Added
- Project initialized.
- Comprehensive project constitution with 20 sections covering mission, architecture, quality gates, and governance
- Full specification prompt with 15 sections: architecture, APIs, data models, milestones, and task generation requirements
- Technical implementation plan with 7 ADRs, service contracts, data models, and M1-M6 deliverables
- Complete task breakdown: 73 tasks (68 milestone + 5 CI) across 6 milestones with dependencies, estimates, and acceptance criteria (TASKS.md + TASKS.json)
- Delta tasks M1.9-M1.12: CODEOWNERS, logging scaffold, license policy, VS Code launch configs (1.5 days)
- Delta tasks M2.9-M2.12: Network shares, DB backup, metadata filters, settings service (2 days)
- Delta tasks M3.12-M3.16: STUN/TURN, QR pairing, connector fallbacks, EPG-lite, subtitle fonts (2.5 days)
- Delta tasks M4.7-M4.8: Legal notices, privacy controls (1 day)
- Delta tasks M5.6-M5.8: Model management, PWA service worker, demo content generator (1.5 days)
- Delta tasks M6.6-M6.8: Bluetooth pairing UI, first-boot wizard, image signing (1.75 days)

### Changed
- Simplified .gitignore format (removed section comments)
- Refined MVP deliverables wording in spec prompt
- Replaced initial constitution with detailed spec-driven development guardrails
- Updated M1.7 AC: Added Kodi JSON-RPC ping script and libcec enablement
- Updated M2.1 AC: Added mount permissions verification and system dir exclusion
- Updated M3.6 AC: Added mDNS TXT with device name and version
- Updated M3.8 AC: Added quantized model option and p50/p95 latency recording
- Updated M5.4 AC: Added mDNS discovery and QR to open PWA on mobile
- Total estimated days increased from ~35-40 to ~43-49 days (with parallel optimization)
- [2025-11-02T15:47:58.2099807Z] Completed tasks: M1.1

- [2025-11-02T15:59:00.5986505Z] Completed tasks: M1.2

- [2025-11-02T16:04:15.5829635Z] Completed tasks: M1.3

- [2025-11-02T16:04:55.8361850Z] Completed tasks: M1.4

- [2025-11-02T16:07:36.1530925Z] Completed tasks: M1.5

- [2025-11-02T16:11:44.9514374Z] Completed tasks: M1.6

- [2025-11-02T16:12:57.1469763Z] Completed tasks: M1.7

- [2025-11-02T16:14:02.6007275Z] Completed tasks: M1.8

- [2025-11-02T16:16:25.8281080Z] Completed tasks: M1.9

- [2025-11-02T16:17:46.6849149Z] Completed tasks: M1.10

- [2025-11-02T16:20:08.2146444Z] Completed tasks: M1.11

- [2025-11-02T16:20:52.1814080Z] Completed tasks: M1.12

- [2025-11-02T16:26:23.8444798Z] Completed tasks: M2.1

- [2025-11-02T16:34:31.8838402Z] Completed tasks: M2.2

- [2025-11-02T16:39:13.7690108Z] Completed tasks: M2.3

- [2025-11-02T17:04:40.1006481Z] Completed tasks: M2.4

- [2025-11-02T17:20:57.2021151Z] Completed tasks: M2.5
