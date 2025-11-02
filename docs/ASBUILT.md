# WomCast — As Built

- Build: ${BUILD_ID}  •  Commit: ${GIT_SHA}  •  Time (UTC): ${BUILD_UTC}

## Overview
<system that shipped>

## Hardware & OS
- Raspberry Pi 5 (8GB), USB 3.0 SSD
- Base OS: LibreELEC / Pi OS Lite

## Services & Ports
| Service | Purpose | Port/Socket | Auth | Notes |
|--------|---------|-------------|------|------|
| ai.bridge | LLM search & intents | localhost:7070 | local | — |

## Config Files
- /storage/.kodi/userdata/advancedsettings.xml — media/cache
- /storage/womcast/ai.json — AI config

## Directory Layout
/storage/womcast/
  ai/
  logs/
  media/

## Build & Release
- GitHub Actions ARM64 → signed artifacts (.img.gz, OTA .tar)

## Security Model
- LAN-only; PIN pairing; token revocation; optional TLS

## Known Deviations
- <delta> — rationale — <UTC>