# WomCast — Open Entertainment Box

> **Local-first, privacy-focused entertainment OS for Raspberry Pi 5**  
> Unifying local media, free streaming, retro gaming, AI-powered discovery, voice control, and casting—all in a plug-and-play 10-foot interface.

[![License](https://img.shields.io/badge/license-TBD-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0--alpha-orange.svg)](CHANGELOG.md)
[![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%205-c51a4a.svg)](https://www.raspberrypi.com/)
[![Node](https://img.shields.io/badge/node-20%20LTS-339933.svg)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/python-3.11-3776ab.svg)](https://www.python.org/)

---

## Executive Summary

**WomCast** is an open-source entertainment operating system designed for Raspberry Pi 5 that brings together your entire media universe under one unified, privacy-respecting interface. Whether you're browsing your local movie collection, streaming free content from public archives, playing retro games, or using voice commands to find content across all sources, WomCast delivers a seamless 10-foot TV experience without subscriptions, tracking, or vendor lock-in.

Unlike commercial streaming boxes that fragment your content across multiple apps and harvest your viewing data, WomCast operates **local-first**: your data stays on your device, your media lives on your USB drives or network shares, and AI-powered search runs entirely on-device using open models (Ollama, Whisper, ChromaDB). Cast from your phone, control via voice, or navigate with your TV remote—all while maintaining complete ownership of your entertainment experience.

### Quick Facts

- 🎯 **Target Platform**: Raspberry Pi 5 (8GB recommended)
- 📦 **Delivery**: Bootable `.img.gz` (< 2.5GB) ready to flash
- 🔒 **Privacy**: No telemetry, no cloud dependencies, no DRM bypass attempts
- 🎮 **Features**: Local media + free streaming + retro gaming + Live TV + casting + AI voice
- 🛠️ **Stack**: TypeScript/React/Electron frontend, Python/FastAPI backend, Kodi/mpv playback
- 📋 **License**: TBD (open-source, pending final selection)

---

## Why WomCast?

### The Problem with Current Solutions

**Fragmented Experience**  
Commercial streaming boxes force you to juggle multiple apps (Netflix, Hulu, Disney+, etc.) with no unified search. Your local media library sits in a separate app, retro games require yet another interface, and free/public-domain content is hidden across the web.

**Privacy Invasion**  
Smart TVs and streaming devices collect viewing habits, sell data to advertisers, and require constant internet connectivity. Every click, search, and pause is logged and monetized.

**Vendor Lock-in**  
Proprietary ecosystems tie you to specific app stores, force software updates that degrade performance, and abandon older devices with no upgrade path.

**Missing Features**  
Want to add your own Live TV streams via M3U? Use voice search across *all* your content? Cast from your phone without a $50 Chromecast? Control everything with your TV remote via HDMI-CEC? These basic features are either paywalled or don't exist.

### The WomCast Solution

**Unified Interface**  
One 10-foot UI for local media (USB/NFS/SMB), free streaming sources (Internet Archive, PBS, NASA TV, Jamendo), user-added Live TV (M3U/HLS/DASH), retro games (NES→PS1), and cloud service passthrough (no DRM bypass—just QR codes to open provider apps legally).

**Privacy by Design**  
- **Local-first architecture**: All indexing, search, and AI inference run on-device
- **No telemetry**: Zero phone-home; your viewing habits never leave your Pi
- **Optional connectivity**: Works offline; internet only needed for streaming sources
- **Transparent code**: Fully open-source; audit every line

**Open Ecosystem**  
- **Hackable**: Modify, extend, or replace any component
- **Standard formats**: Kodi JSON-RPC, SQLite, WebRTC, M3U—no proprietary protocols
- **Community-driven**: Built with spec-driven development; every feature documented

**AI-Powered Discovery**  
- **Semantic search**: "Find sci-fi movies from the 90s" works across local library + free connectors
- **Voice control**: Push-to-talk via TV remote or phone microphone (Whisper STT, Ollama LLM)
- **Intent routing**: "Play The Matrix" → automatically finds and plays from best available source

**Casting Without Compromise**  
- **Phone/tablet casting**: WebRTC-based pairing (no Google/Apple dependencies)
- **Remote control**: PWA lets your phone act as a full-featured remote + voice input
- **Low latency**: LAN-first design; <2s pairing, <3s voice RTT

**Retro Gaming Built-in**  
- **RetroArch integration**: NES, SNES, Genesis, PS1 cores pre-configured
- **Bluetooth controllers**: Pair via on-screen wizard; per-controller mapping profiles
- **Save states**: Pick up where you left off across sessions

---

## Features

### Core Capabilities

#### 🎬 **Local Media Library**
- **Auto-mounting**: USB3 drives detected and indexed automatically (≤5s for 1k files)
- **Format support**: .mkv, .mp4, .avi, .flv, .swf, .mp3, .m4a, .flac, and more
- **Metadata extraction**: Artwork, title, album, artist, duration scraped from files
- **Resume position**: Pick up playback where you left off
- **Subtitles**: Auto-load SRT/VTT with font fallback rules
- **Network shares**: Optional SMB/NFS mounting via settings

#### 📺 **Free Streaming Connectors**
- **Internet Archive**: Browse public-domain movies, music, and educational content
- **PBS**: Access PBS shows and documentaries
- **NASA TV**: Live streams and mission archives
- **Jamendo**: Free-to-stream music library
- **Rate limiting**: Backoff/retry logic prevents bans; user-facing error messages

#### 📡 **Live TV & EPG**
- **M3U/HLS/DASH ingest**: Paste URL or upload file; channels load instantly
- **Validation**: Cleanup and sanity checks applied automatically
- **EPG-lite**: Now/Next derived from M3U hints or simple EPG URL (when provided)
- **Logo display**: Channel grid with artwork

#### 🎮 **Retro Gaming**
- **RetroArch cores**: NES, SNES, Genesis, Game Boy, PS1 pre-installed
- **Save states**: Full state save/restore per game
- **Bluetooth pairing**: On-screen wizard for controller setup
- **Controller profiles**: Per-device mapping save/restore

#### 🗣️ **AI-Powered Voice & Search**
- **Whisper STT**: Small quantized model; ≤1.2s p50 latency
- **Ollama intent parsing**: "Play the latest Jamendo jazz" → action + args API
- **ChromaDB semantic search**: Embeddings for "Find documentaries about space"
- **Unified search UX**: Text, semantic, and voice inputs converge in one interface
- **Phone-mic relay**: Hold push-to-talk on your phone when TV lacks microphone
- **Server-side processing**: Option to offload STT/LLM when device is underpowered

#### 📱 **Casting & Remote Control**
- **mDNS discovery**: Phone/tablet finds WomCast on LAN automatically
- **QR pairing**: On-screen QR encodes `womcast.local` + session credentials
- **WebRTC signaling**: Direct peer connection; no relay servers needed (TURN optional)
- **PWA remote**: Install on home screen; navigate, play/pause, push-to-talk voice
- **Service worker**: Offline cache; reconnect handling when network drops

#### ☁️ **Cloud Service Passthrough**
- **Legal compliance**: No DRM bypass; badges open provider login pages (Netflix, Disney+, etc.)
- **QR codes**: Mobile signin for services that require it
- **HDMI-CEC integration**: Auto-switch TV input when launching cloud apps (with fallback UI)
- **Acknowledgment tracking**: First-use terms shown; stored in settings

#### 🔒 **Privacy & Security**
- **No PII in logs**: Structured logging with privacy filters
- **Data purge**: One-click deletion of voice history, embeddings, recents
- **Local export**: Download your data as file (no cloud upload)
- **WAL mode**: SQLite corruption protection + nightly backup script
- **License scanning**: CI blocks forbidden dependencies (GPL violations, etc.)
- **Security audits**: pip-audit and npm audit run on every PR; high/critical = fail

#### ⚡ **Performance Budgets**
- **Boot**: ≤15s from power-on to UI
- **Index**: ≤5s for 1k files (cold cache)
- **Cast pairing**: ≤2s on LAN
- **Voice RTT**: ≤3s (capture → transcript → intent → action)
- **AI inference**: ≤3s p50 for intent resolution
- **CI gates**: Perf smoke tests block regressions

#### ♿ **Accessibility**
- **WCAG AA contrast**: All UI elements pass accessibility checks
- **Keyboard/CEC navigation**: Full control without mouse
- **Reduced motion**: Toggle for users sensitive to animations
- **Screen reader hints**: ARIA labels on critical elements

---

## What Makes WomCast Different?

### vs. Commercial Streaming Boxes (Roku, Fire TV, Apple TV)

| Feature | WomCast | Commercial Boxes |
|---------|---------|------------------|
| **Privacy** | Zero telemetry, local-first | Extensive tracking, ad targeting |
| **Local media** | First-class support (USB/NFS/SMB) | Afterthought (requires Plex/Jellyfin) |
| **Free content** | Integrated connectors (Archive, PBS, NASA) | Hidden or requires separate apps |
| **Voice search** | Works across ALL sources (local + streaming + Live TV) | Siloed per app; requires cloud |
| **Retro gaming** | Built-in (RetroArch) | Not available or requires hacks |
| **Casting** | Open WebRTC (no Google/Apple) | Proprietary (Chromecast/AirPlay only) |
| **Customization** | Fully hackable; open-source | Locked ecosystem; no access to code |
| **Cost** | Free (DIY Pi5 + USB drive) | $50-200 + subscriptions |

### vs. Kodi/LibreELEC

| Feature | WomCast | Kodi/LibreELEC |
|---------|---------|----------------|
| **AI search** | Semantic + voice built-in (Ollama + Whisper) | Requires plugins; no unified search |
| **Casting** | Native WebRTC implementation | Requires separate Chromecast add-on |
| **Free connectors** | Pre-integrated (Archive, PBS, Jamendo) | Manual add-on installation per source |
| **Voice control** | Phone-mic relay + on-device STT | Limited; requires external mic + plugin |
| **UI/UX** | Modern React 10-foot design | Confluence skin (dated) |
| **Developer experience** | TypeScript + Python monorepo | C++ plugins; steep learning curve |
| **Retro gaming** | RetroArch integrated | Separate install (RetroPie, etc.) |

### vs. Plex/Jellyfin

| Feature | WomCast | Plex | Jellyfin |
|---------|---------|------|----------|
| **Privacy** | Local-only | Phone-home to plex.tv | Local-only |
| **Free streaming** | Built-in connectors | Not available | Plugin ecosystem |
| **Voice control** | On-device AI (Whisper + Ollama) | Cloud-based (Alexa/Google) | Not available |
| **Live TV** | M3U/HLS/DASH native | DVR add-on (Plex Pass) | Plugin-based |
| **Retro gaming** | Integrated | Not available | Not available |
| **Casting** | WebRTC (no intermediary) | Requires Plex server running | DLNA/Chromecast |
| **First-boot wizard** | Guided setup (PIN, shares, models) | Complex server install | Manual config |

### vs. RetroArch/RetroPie

| Feature | WomCast | RetroArch/RetroPie |
|---------|---------|-------------------|
| **Media playback** | Full-featured (local + streaming) | Not available |
| **Unified UI** | Single 10-foot interface | Separate EmulationStation UI |
| **Voice search** | "Play Mario 3" across media + games | Not available |
| **Live TV** | Integrated | Not available |
| **Cloud passthrough** | QR codes for legal streaming apps | Not available |

---

## Architecture Overview

### Tech Stack

**Frontend**
- **Electron 31+**: Chromium-based shell for 10-foot UI
- **React 18+**: Component-based UI with hooks
- **TypeScript 5+**: Type-safe codebase
- **Vite**: Fast build tooling
- **PWA**: Service worker for offline mobile remote

**Backend**
- **FastAPI**: Python async web framework for microservices
- **Uvicorn**: ASGI server
- **Pydantic v2**: Data validation
- **SQLite**: Media library, settings, recents
- **ChromaDB 0.5+**: Vector embeddings for semantic search

**Playback**
- **Kodi 21 (Omega)**: JSON-RPC bridge for media playback (primary)
- **mpv/libmpv**: Fallback option for minimal setups

**AI Stack**
- **Whisper (small)**: Speech-to-text (quantized for Pi5)
- **Ollama**: Local LLM for intent parsing (small fast models)
- **ChromaDB**: Semantic search via embeddings

**DevOps**
- **GitHub Actions**: CI/CD pipeline (lint, test, security, perf, docs)
- **Pi OS Lite**: Base image (Debian-based)
- **Systemd**: Service management
- **udev**: USB auto-mount rules

### Repository Structure

```
WomCast/
├── apps/
│   ├── frontend/          # Electron + React + TypeScript
│   │   ├── electron/      # Main process, IPC, window management
│   │   ├── src/           # React components, views, hooks
│   │   │   ├── views/     # Library, Connectors, LiveTV, Retro, Search, Settings
│   │   │   └── components/ # Voice, Player, QRPairing, ErrorBoundary
│   │   └── pwa/           # Service worker for mobile remote
│   └── backend/           # Python FastAPI microservices
│       ├── common/        # Shared models, config, logging, metrics
│       ├── indexer/       # Library scanning, metadata extraction
│       ├── media/         # Kodi JSON-RPC bridge, playback control
│       ├── connectors/    # Free streaming sources (Archive, PBS, NASA, Jamendo)
│       ├── livetv/        # M3U/HLS/DASH ingest, EPG parsing
│       ├── cast/          # WebRTC signaling, mDNS advertisement
│       └── ai/            # Whisper STT, Ollama intent, ChromaDB search
├── build/
│   ├── image/             # Pi OS customization scripts
│   └── scripts/           # Build automation, image signing
├── docs/
│   ├── ASBUILT.md         # System as-built documentation
│   ├── RUNBOOK.md         # Operations guide (troubleshooting, backups, rollback)
│   ├── SPEC_PROMPT_WOMCAST.md  # Master specification
│   └── spec/
│       ├── TASKS.md       # Human-readable task breakdown (73 tasks)
│       └── TASKS.json     # Machine-readable task tracking
├── scripts/
│   └── dev/               # Developer helpers (lint, perf, task tracking)
├── .github/
│   └── workflows/         # CI/CD pipelines (lint-test, security, build-image, perf, docs)
├── .speckit/
│   ├── constitution.md    # Project governance (20 sections)
│   └── plan.md            # Technical implementation plan (7 ADRs)
├── CHANGELOG.md           # Keep-a-Changelog format with UTC timestamps
└── README.md              # This file
```

### Key Design Decisions (ADRs)

1. **Frontend: React + Electron** → 10-foot UI optimized for TV; keyboard/CEC navigation
2. **Backend: FastAPI microservices** → Separate services per domain (indexer, media, cast, ai, connectors)
3. **Playback: Kodi JSON-RPC** → Mature media player with HDMI-CEC support; mpv fallback
4. **Database: SQLite + ChromaDB** → Simple, file-based storage; vector embeddings for semantic search
5. **AI Stack: Whisper + Ollama + ChromaDB** → On-device inference; privacy-preserving; quantized models for Pi5
6. **Security: LAN-only default** → No remote access in MVP; optional TURN for Phase 2
7. **Image: Pi OS Lite base** → Minimal footprint; systemd services; <2.5GB final image

---

## Getting Started

### Hardware Requirements

**Minimum**
- Raspberry Pi 5 (4GB model)
- 32GB microSD card (Class 10/U1)
- HDMI 2.0 cable
- USB keyboard (for initial setup)
- Power supply (official Pi5 adapter recommended)

**Recommended**
- Raspberry Pi 5 (8GB model)
- 64GB+ microSD card (U3/A2)
- USB3 external drive (for media library)
- Bluetooth game controller (optional)
- TV remote with HDMI-CEC support

### Installation

**Option 1: Flash Pre-built Image** (Recommended)

1. Download the latest `.img.gz` from [Releases](https://github.com/LackOfSkillz/WomCast/releases)
2. Verify checksum:
   ```powershell
   # Windows (PowerShell)
   Get-FileHash -Algorithm SHA256 womcast-0.1.0-pi5.img.gz
   ```
   ```bash
   # Linux/macOS
   sha256sum womcast-0.1.0-pi5.img.gz
   ```
3. Flash to microSD using [Raspberry Pi Imager](https://www.raspberrypi.com/software/) or [balenaEtcher](https://www.balena.io/etcher/)
4. Insert card into Pi5, connect HDMI, power on
5. Follow first-boot wizard (setup PIN, optional network shares, optional AI model download)

**Option 2: Build from Source**

See [docs/RUNBOOK.md](docs/RUNBOOK.md) for detailed build instructions.

### First Launch

1. **Network Setup**: Connect Pi5 to LAN via Ethernet or WiFi
2. **First-Boot Wizard**:
   - Set access PIN (optional but recommended)
   - Configure network shares (SMB/NFS) if desired
   - Download AI models (Whisper small, Ollama llama3.2:1b) if you want voice features
3. **Add Content**:
   - Plug in USB drive with media files (auto-mounts to `/media/usb*`)
   - Wait for indexer to complete (progress bar shown)
4. **Start Watching**: Navigate with arrow keys or TV remote (HDMI-CEC)

---

## Usage

### Media Library

- **Add Media**: Plug in USB3 drive; indexer runs automatically
- **Browse**: Navigate grid with arrow keys; press Enter to play
- **Search**: Type in search box; semantic search finds content by description
- **Details**: Highlight item and press Info/Details button for metadata

### Live TV

- **Add Channels**: Settings → Live TV → Paste M3U URL or upload file
- **Watch**: Select channel from grid; playback starts immediately
- **EPG**: If M3U includes EPG URL, Now/Next info displays automatically

### Retro Gaming

- **Add ROMs**: Copy to USB drive under `/retro/roms/{system}/` (e.g., `/retro/roms/nes/`)
- **Launch Game**: Browse retro section; select game; press Play
- **Save State**: In-game menu (controller hotkey or on-screen button)
- **Pair Controller**: Settings → Controllers → Bluetooth Pairing

### Voice Control

- **TV Remote**: Hold voice/mic button; speak command; release
- **Phone App**: Open PWA (`http://womcast.local`); tap mic button; hold and speak
- **Example Commands**:
  - "Play The Matrix"
  - "Find documentaries about space"
  - "Show me jazz albums from Jamendo"
  - "Resume my last movie"

### Casting from Phone/Tablet

1. Ensure phone/tablet is on same LAN as WomCast
2. Open browser; navigate to `http://womcast.local` (or scan QR from TV)
3. Enter pairing PIN (shown on TV screen)
4. Use PWA as remote: navigate, play/pause, voice input

### Cloud Services

- **Access**: Browse to Connectors → Cloud Services
- **Login**: Tap service badge (Netflix, Disney+, etc.); QR code appears on TV
- **Scan with Phone**: Open provider app; sign in normally
- **Note**: WomCast does **not** bypass DRM; this is legal passthrough only

---

## Development

### Quick Start

**Prerequisites**
- Node 20 LTS
- Python 3.11
- Git

**Clone and Setup**

```bash
git clone https://github.com/LackOfSkillz/WomCast.git
cd WomCast

# Install frontend dependencies
cd apps/frontend
npm install
cd ../..

# Install backend dependencies
cd apps/backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
cd ../..
```

**Run Development Environment**

```bash
# Option 1: VS Code launch configs (F5)
# Open in VS Code, press F5, select "Launch All"

# Option 2: Manual launch
# Terminal 1: Backend services
cd apps/backend
uvicorn indexer.main:app --reload --port 8001 &
uvicorn media.main:app --reload --port 8002 &
uvicorn cast.main:app --reload --port 8003 &
uvicorn ai.main:app --reload --port 8004 &

# Terminal 2: Frontend
cd apps/frontend
npm run dev
```

**Run Tests**

```bash
# Python
pytest -q

# JavaScript
npm test --silent

# All quality gates
npm run gate:all  # Runs lint + test for both Python and JS
```

### Project Milestones

See [docs/spec/TASKS.md](docs/spec/TASKS.md) for complete task breakdown.

- **M1: System Setup** (5.5 days) — Monorepo, tooling, CI, "Hello TV" shell
- **M2: Storage & Library** (7.5 days) — USB auto-mount, indexer, playback
- **M3: Free Streaming + Live TV + Casting + Voice** (12.5 days) — Connectors, M3U, WebRTC, Whisper
- **M4: Cloud Mapper + CEC + Server Voice** (5 days) — QR flows, HDMI-CEC, privacy controls
- **M5: AI Bridge + PWA + Docs** (7 days) — Ollama, ChromaDB, mobile remote
- **M6: Retro + UI Polish + Final Image** (5.75 days) — RetroArch, accessibility, release

**Total Estimated**: 43-49 days (with parallel optimization)

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines (coming soon).

**Key Principles** (from [.speckit/constitution.md](.speckit/constitution.md)):
- **Code Quality**: No new `any` types (TypeScript); 80% test coverage minimum
- **Security**: pip-audit and npm audit pass on every PR; no GPL violations
- **Performance**: All budgets enforced (boot ≤15s, index ≤5s, voice ≤3s, cast ≤2s)
- **Documentation**: ASBUILT.md delta required for /apps or /build changes
- **Conventional Commits**: Enforced via CODEOWNERS + PR templates

---

## Roadmap

### MVP (v0.1.0) — Target: Q1 2026

- ✅ Core architecture scaffolded
- ✅ Task breakdown complete (73 tasks)
- ⏳ M1: System Setup (in progress)
- ⏳ M2: Storage & Library
- ⏳ M3: Free Streaming + Live TV + Casting + Voice
- ⏳ M4: Cloud Mapper + CEC + Server Voice
- ⏳ M5: AI Bridge + PWA + Docs
- ⏳ M6: Retro + UI Polish + Final Image

### Phase 2 (v0.2.0) — TBD

**WomCast Link** — Secure remote access

- WireGuard or WebRTC tunneling to `womcast.ai` / `wamcast.ai`
- NAT traversal for remote streaming when away from home
- Optional feature; MVP is LAN-only

### Future Enhancements

- **Plugin System**: Community-contributed connectors, themes, AI models
- **Multi-room Audio**: Sync playback across multiple WomCast instances
- **DVR Functionality**: Record Live TV streams to USB/NAS
- **4K HDR**: Optimize for Pi5's HDMI 2.1 capabilities
- **Smart Home Integration**: MQTT/HomeKit bridge for automation
- **Parental Controls**: Content filtering, viewing time limits

---

## Community & Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/LackOfSkillz/WomCast/issues)
- **Discussions**: [Ask questions, share configs](https://github.com/LackOfSkillz/WomCast/discussions)
- **Documentation**: [RUNBOOK.md](docs/RUNBOOK.md), [ASBUILT.md](docs/ASBUILT.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

## License

TBD — Open-source license pending final selection. See [LICENSE](LICENSE) for details.

---

## Acknowledgments

**Built on the shoulders of giants:**

- [Kodi](https://kodi.tv/) — Mature media player foundation
- [RetroArch](https://www.retroarch.com/) — Unified retro gaming interface
- [Whisper](https://github.com/openai/whisper) — Open-source speech recognition
- [Ollama](https://ollama.ai/) — Local LLM inference
- [ChromaDB](https://www.trychroma.com/) — Vector database for semantic search
- [FastAPI](https://fastapi.tiangolo.com/) — Modern Python web framework
- [React](https://react.dev/) — Component-based UI library
- [Electron](https://www.electronjs.org/) — Cross-platform desktop apps
- [Raspberry Pi](https://www.raspberrypi.com/) — Accessible, powerful hardware

---

## FAQ

**Q: Can I use WomCast to pirate content?**  
A: No. WomCast does not bypass DRM, crack copy protection, or facilitate piracy. Free streaming connectors (Internet Archive, PBS, NASA, Jamendo) only access legally available public-domain or freely licensed content. Cloud service passthrough is a legal convenience (like a bookmark) that opens provider apps where you must authenticate normally.

**Q: Does WomCast require an internet connection?**  
A: No for local media and retro gaming. Yes for free streaming connectors, Live TV (if streams are online), and cloud services. AI features (voice/search) work offline after models are downloaded.

**Q: Can I run WomCast on older Raspberry Pi models?**  
A: Pi5 is the target platform due to performance requirements (AI inference, 4K playback). Pi4 (8GB) may work with reduced features; Pi3 and earlier are not supported.

**Q: How is this different from just installing Kodi?**  
A: WomCast integrates AI search/voice, casting, free streaming connectors, retro gaming, and modern UI into a cohesive 10-foot experience. Kodi requires manual add-on installation, lacks unified search, and has a steeper learning curve for newcomers.

**Q: Is WomCast production-ready?**  
A: Not yet. Currently in active development (v0.1.0-alpha). MVP target: Q1 2026. Follow [releases](https://github.com/LackOfSkillz/WomCast/releases) for updates.

**Q: Can I contribute?**  
A: Yes! See [CONTRIBUTING.md](CONTRIBUTING.md) (coming soon) and [docs/spec/TASKS.md](docs/spec/TASKS.md) for open tasks.

---

**Made with ❤️ by the WomCast community**  
*Reclaim your entertainment. Own your media. Respect your privacy.*
