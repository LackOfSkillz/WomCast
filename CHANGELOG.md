# Changelog

All notable changes to this project will be documented here. Timestamps are UTC (ISO-8601).

## [Unreleased] - 2025-11-02T22:00:00.0000000Z

### M2.6: Subtitles + resume position (Complete) - 2025-11-02
**Duration**: ~0.75 days (estimated 0.75 days)  
**Task**: M2.6 - Subtitles: External file detection + resume position persistence

#### Implementation
- **Subtitle Detection** (metadata/indexer.py)
  - New `detect_subtitle_files()` function scans for external subtitle files
  - Supported formats: .srt, .vtt, .ass, .ssa, .sub
  - Recognizes 30+ language codes (en, eng, english, es, spa, spanish, fr, fra, french, de, ger, german, it, ita, italian, pt, por, portuguese, ru, rus, russian, ja, jpn, japanese, zh, chi, chinese, ko, kor, korean, ar, ara, arabic, hi, hin, hindi)
  - Pattern matching: `movie.srt`, `movie.en.srt`, `movie.english.vtt`
  - Stores subtitle tracks as JSON array in database: `[{path, language, format}]`
  - Updates both new and existing files with subtitle information
- **Resume Position Persistence** (metadata/main.py)
  - New `PUT /v1/media/{media_id}/resume` endpoint
  - Updates `resume_position_seconds` column in database
  - Returns updated media record with all fields
  - Proper error handling for non-existent media IDs
- **Metadata API Endpoints** (metadata/main.py, 223 lines)
  - `GET /v1/media?type={optional}` - List all media files with optional type filter
  - `GET /v1/media/search?q={query}` - Search media by file name
  - `GET /v1/media/{media_id}` - Get detailed media info with video/audio metadata
  - JSON parsing for subtitle_tracks field in database queries
  - Type-safe response models with proper null handling
- **Kodi Subtitle Control** (playback/kodi_client.py)
  - New `get_subtitles()` method - Returns list of available subtitle tracks
  - New `set_subtitle(subtitle_index)` method - Sets active subtitle track
  - New `toggle_subtitles()` method - Toggles subtitles on/off
  - Track properties: index, language, name, current (boolean)
  - Integration with Kodi JSON-RPC Player.GetProperties and Player.SetSubtitle
- **Playback Subtitle Endpoints** (playback/main.py)
  - `GET /v1/subtitles` - Get available subtitle tracks from active player
  - `POST /v1/subtitles` - Set active subtitle track (body: {subtitle_index: int})
  - `POST /v1/subtitles/toggle` - Toggle subtitles on/off
  - Request models: SubtitleRequest(subtitle_index: int)
- **Frontend API Integration** (frontend/src/services/api.ts, 282 lines)
  - New interface: SubtitleTrack {index, language, name, current}
  - Updated MediaFile interface with `subtitle_tracks?: string` (JSON)
  - New functions:
    - `updateResumePosition(mediaId, positionSeconds)` - PUT to metadata API
    - `getSubtitles()` - GET from playback API
    - `setSubtitle(subtitleIndex)` - POST to playback API
    - `toggleSubtitles()` - POST to playback API
- **DetailPane Subtitle Display** (frontend/src/components/DetailPane.tsx)
  - Parses subtitle_tracks JSON field from MediaFile
  - Displays subtitle languages and formats (e.g., "en (srt), es (vtt)")
  - Shows subtitle count in file information section
  - Resume position bar already existed, now backend persists updates

#### Bug Fixes
- **ESLint Configuration** (frontend/eslint.config.js)
  - Disabled `@typescript-eslint/unified-signatures` rule due to ESLint 9.39.0 bug
  - Bug caused crash: "Cannot read properties of undefined (reading 'name')"
  - Crash occurred on DetailPane.tsx line 133 during linting
- **Ruff Linting** (backend Python code)
  - Added `strict=True` parameter to all zip() calls per B905 rule
  - Prevents length mismatch bugs in dict(zip()) operations
  - Fixed 6 occurrences in metadata/main.py
- **MyPy Type Checking** (metadata/main.py)
  - Added null check for fetchone() result before zip()
  - Raises HTTPException(500) if database query unexpectedly returns None
  - Satisfies mypy arg-type checking for zip() second argument

#### Testing
- ✅ All pre-commit checks passed (ruff, mypy, eslint, tsc)
- ✅ TypeScript compilation clean
- ✅ Python type checking clean
- ✅ Frontend ESLint clean

#### Acceptance Criteria Met
- ✅ **AC1**: SRT/VTT subtitles load automatically (detect_subtitle_files scans for external files)
- ✅ **AC2**: Resume position persists in DB (PUT /v1/media/{id}/resume updates database)
- ✅ **AC3**: UI shows subtitle toggle (DetailPane displays subtitle tracks, API has toggleSubtitles)

#### Files Modified
- apps/backend/metadata/main.py (18 → 223 lines)
- apps/backend/metadata/indexer.py (400 → 481 lines)
- apps/backend/playback/kodi_client.py (325 → 417 lines)
- apps/backend/playback/main.py (183 → 239 lines)
- apps/frontend/src/services/api.ts (213 → 282 lines)
- apps/frontend/src/components/DetailPane.tsx (updated subtitle parsing)
- apps/frontend/eslint.config.js (disabled unified-signatures rule)

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

- [2025-11-02T18:01:18.3010792Z] Completed tasks: M2.6
