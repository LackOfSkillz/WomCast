# WomCast — Runbook

> **Operational procedures and troubleshooting guide**  
> Updated: 2025-11-02 UTC  
> Milestone: M2 (Storage & Library)

---

## First Boot

1. **Setup Wizard**
   - Language selection
   - Wi-Fi configuration
   - System PIN creation (6-digit)
   - Theme selection (dark/light)
   - Microphone test (voice input)

2. **Verify Services**
   - Navigate to: Settings → System → About
   - Check service health endpoints:
     ```bash
     curl http://localhost:3000/healthz  # Gateway
     curl http://localhost:3001/healthz  # Metadata
     curl http://localhost:3002/healthz  # Playback
     curl http://localhost:3003/healthz  # Voice
     curl http://localhost:3004/healthz  # Search
     ```

---

## Library & Indexer Operations

### Adding Media to Library

1. **USB Drive Auto-mount** (M2.1)
   - Plug USB drive into Pi 5
   - System automatically mounts to `/media/<drive-label>`
   - Mount point registered in database
   - Indexing starts automatically (or trigger manually)

2. **Manual Index Trigger**
   - **UI**: Settings → Library → Rebuild Index
   - **CLI**: 
     ```bash
     # Development
     cd /opt/womcast
     python -m metadata.indexer /media/<drive-label>
     
     # Production (with wrapper)
     python apps/backend/perf_wrapper.py /media/<drive-label>
     ```
   - **API**:
     ```bash
     curl -X POST http://localhost:3001/v1/index/mount/<mount_id>
     ```

3. **Supported File Types**
   - **Video**: .mkv, .mp4, .avi, .mov, .wmv, .flv, .webm, .m4v
   - **Audio**: .mp3, .flac, .wav, .aac, .ogg, .m4a, .wma, .opus
   - **Photos**: .jpg, .jpeg, .png, .gif, .bmp, .tiff, .webp, .heic
   - **Games**: .iso, .cue, .bin, .chd, .7z, .zip
   - **Subtitles**: .srt, .vtt, .ass, .ssa, .sub (external files)

### Viewing Indexed Media

1. **Browse Library**
   - Navigate to: Library → Movies/TV/Music/Photos/Games
   - Grid view displays: artwork, title, duration, file size
   - Search box: Type to filter (300ms debounce)

2. **Media Details**
   - Click/select media card to open DetailPane
   - View: File info, video/audio metadata, resume position, subtitles
   - Actions: Play, Resume, Manage Subtitles

3. **Search Media**
   - **Quick Search**: Use search box in library view (client-side filtering)
   - **API Search**:
     ```bash
     curl "http://localhost:3001/v1/media/search?q=movie name"
     ```

### Managing Subtitles (M2.6)

1. **Automatic Detection**
   - Indexer scans for .srt/.vtt/.ass/.ssa/.sub files matching media names
   - Language codes recognized: en, eng, english, es, spa, spanish, fr, fra, etc. (30+ codes)
   - Patterns: `movie.srt`, `movie.en.srt`, `movie.english.vtt`

2. **During Playback**
   - **Enable/Disable**: Press 'S' key or use UI subtitle toggle
   - **Change Track**:
     ```bash
     curl -X GET http://localhost:3002/v1/subtitles  # List tracks
     curl -X POST http://localhost:3002/v1/subtitles \
       -H "Content-Type: application/json" \
       -d '{"subtitle_index": 2}'
     ```
   - **Toggle On/Off**:
     ```bash
     curl -X POST http://localhost:3002/v1/subtitles/toggle
     ```

### Resume Position Tracking (M2.6)

1. **Automatic Saving**
   - Playback position saved every 10 seconds (configurable)
   - Stored in `media_files.resume_position_seconds` column

2. **Manual Update** (API)
   ```bash
   curl -X PUT http://localhost:3001/v1/media/{media_id}/resume \
     -H "Content-Type: application/json" \
     -d '{"position_seconds": 3600.5}'
   ```

3. **Resume Playback**
   - UI shows progress bar on media cards
   - Click "Resume" button to continue from last position
   - Threshold: Shows resume if >5% watched and <95% complete

### Database Maintenance

1. **View Index Statistics**
   ```bash
   sqlite3 /data/metadata.db "SELECT media_type, COUNT(*) FROM media_files GROUP BY media_type;"
   ```

2. **Clear Deleted Files**
   - Automatic: Runs during index scan (detect_deleted_files)
   - Manual:
     ```bash
     sqlite3 /data/metadata.db "DELETE FROM media_files WHERE NOT EXISTS (SELECT 1 FROM mount_points WHERE mount_points.id = media_files.mount_point_id);"
     ```

3. **Rebuild Index from Scratch**
   - **UI**: Settings → Library → Delete & Rebuild
   - **CLI**:
     ```bash
     rm /data/metadata.db
     python -m metadata.indexer /media/<drive-label>
     ```

### Performance Monitoring (M2.7, M3.10)

#### Indexer Performance Test (M2.7)

1. **Run Indexer Performance Test**
   - **VS Code**: Run Task → perf:index
   - **PowerShell**:
     ```powershell
     .\scripts\dev\perf-index.ps1 C:\path\to\test-media
     ```
   - **Bash**:
     ```bash
     ./scripts/dev/perf-index.sh /path/to/test-media
     ```

2. **Performance Targets**
   - **Cold cache**: ≤5s for 1000 files
   - **Warm cache**: ~2-3x faster than cold
   - **Throughput**: 200+ files/s on Pi 5

3. **Interpret Results**
   ```
   Test directory:     /media/usb-drive
   Total files:        1234
   Cold cache time:    4.2s
   Warm cache time:    1.8s
   Speedup:            2.3x
   Cold throughput:    293.8 files/s
   Warm throughput:    685.6 files/s
   ✓ Performance OK: Cold cache within expected range
   ```

#### Backend API Performance Test (M3.10)

1. **Run Backend Benchmarks**
   - **Prerequisites**: Backend server must be running (`cd apps/backend && python -m gateway.main`)
   - **PowerShell**:
     ```powershell
     .\scripts\dev\perf-backend.ps1
     ```
   - **Output**: `perf-backend-results.json`

2. **Performance Thresholds**
   - **Health Check**: ≤100ms average
   - **Search Endpoints**: ≤500ms average
   - **Connector APIs**: ≤3000ms average (external API latency)
   - **Success Rate**: 100% for core endpoints, 80%+ for connectors

3. **Interpret Results**
   ```
   === Performance Summary ===
   Total tests:          18
   Successful (100%):    16
   Partial failures:     2
   
   === Slowest Endpoints ===
     Internet Archive Search: 2134.5ms avg
     NASA Live Streams: 1892.3ms avg
     PBS Featured: 1654.7ms avg
   
   === Fastest Endpoints ===
     Health Check: 12.3ms avg
     Database Stats: 45.6ms avg
     Get Playlists: 78.9ms avg
   
   ✓ Health Check within 100ms threshold
   ✓ Search within 500ms threshold
   ✓ Connector within 3000ms threshold
   ```

#### Frontend Build Performance Test (M3.10)

1. **Run Frontend Benchmarks**
   - **PowerShell**:
     ```powershell
     .\scripts\dev\perf-frontend.ps1
     ```
   - **Output**: `perf-frontend-results.json`

2. **Performance Thresholds**
   - **Total Bundle Size**: ≤5 MB
   - **JavaScript Bundle**: ≤1 MB
   - **TypeScript Compilation**: ≤30s
   - **Dev Server Startup**: ≤30s

3. **Interpret Results**
   ```
   === Bundle Size Analysis ===
   Total bundle size:    3.42 MB
   JavaScript bundle:    789.4 KB
   CSS bundle:           123.5 KB
   
   === TypeScript Compilation Performance ===
   TypeScript compilation: 8.34s
   
   === Performance Thresholds ===
   ✓ Bundle size within 5 MB threshold
   ✓ JavaScript bundle within 1 MB threshold
   ✓ TypeScript compilation within 30s threshold
   ```

#### Network Performance Test (M3.10)

1. **Run Network Benchmarks**
   - **PowerShell**:
     ```powershell
     .\scripts\dev\perf-network.ps1
     # Or with custom Kodi host:
     .\scripts\dev\perf-network.ps1 -KodiHost 192.168.1.100 -KodiPort 9090
     ```
   - **Output**: `perf-network-results.json`

2. **Performance Thresholds**
   - **Kodi JSON-RPC**: ≤100ms average
   - **DNS Resolution**: ≤100ms average per domain
   - **Connector APIs**: ≤3000ms average
   - **Success Rate**: 100% for local services, 80%+ for external APIs

3. **Interpret Results**
   ```
   === Network Performance Benchmark ===
   
   === Internet Archive Connector ===
   IA: Collections API: Avg: 1834.2ms | Min: 1623.4ms | Max: 2134.5ms
   
   === NASA API ===
   NASA: Image/Video Library Search: Avg: 892.3ms | Min: 745.6ms | Max: 1123.7ms
   
   === Kodi JSON-RPC ===
   Kodi is reachable (Ping: 23.4ms)
   Kodi: GetActivePlayers (15.6ms)
   
   === DNS Resolution Performance ===
     archive.org : 34.5ms
     images-api.nasa.gov : 28.7ms
     api.jamendo.com : 41.2ms
   
   === Performance Thresholds ===
   ✓ Kodi latency within 100ms threshold
   ✓ Average DNS resolution within 100ms threshold: 34.8ms
   ✓ All connectors within 3000ms threshold
   ```

---

## Common Tasks

### Rebuild Library Index
- **UI**: Settings → Library → Rebuild
- **CLI**: `python -m metadata.indexer /media/<drive>`
- **Expected Duration**: ~5s for 1000 files

### OTA Rollback
- **UI**: Settings → System → Updates → Previous Version
- **CLI**: `sudo systemctl start womcast-rollback.service`

### Check Service Logs
```bash
# View live logs
journalctl -u womcast-gateway -f
journalctl -u womcast-metadata -f
journalctl -u womcast-playback -f

# View last 100 lines
journalctl -u womcast-gateway -n 100
```

---

## Troubleshooting

### No HDMI-CEC Response
**Symptoms**: Remote control not working with Kodi  
**Checks**:
- Verify HDMI cable supports CEC
- Run: `cec-client -l` to list CEC devices
- Check: Settings → System → CEC → Enabled

**Fix**:
1. Restart CEC mapper: `sudo systemctl restart cec-mapper`
2. Fallback: Use IR remote or phone app
3. Test Kodi directly: Open Kodi UI and test navigation

### Indexer Not Finding Files
**Symptoms**: Media files present but not appearing in library  
**Checks**:
- Verify mount point: `ls /media/<drive-label>`
- Check file extensions match supported types
- Review indexer logs: `journalctl -u womcast-metadata -n 50`

**Fix**:
1. Trigger manual index: Settings → Library → Rebuild
2. Check file permissions: `ls -la /media/<drive-label>`
3. Verify database: `sqlite3 /data/metadata.db "SELECT COUNT(*) FROM media_files;"`

### Subtitles Not Showing
**Symptoms**: Media plays but subtitles missing  
**Checks**:
- Verify subtitle file exists: `ls /path/to/media/movie.srt`
- Check filename matches media: `movie.mp4` → `movie.srt` or `movie.en.srt`
- Review DetailPane in UI for detected subtitles

**Fix**:
1. Re-index directory: Settings → Library → Rebuild
2. Manually check subtitle track:
   ```bash
   curl http://localhost:3002/v1/subtitles
   ```
3. Enable subtitles during playback: Press 'S' or toggle in UI

### Playback Not Responding
**Symptoms**: Play button clicks but nothing happens  
**Checks**:
- Verify Kodi running: `systemctl status kodi`
- Test Kodi JSON-RPC: `curl http://localhost:8080/jsonrpc`
- Check playback service: `curl http://localhost:3002/healthz`

**Fix**:
1. Restart Kodi: `sudo systemctl restart kodi`
2. Restart playback service: `sudo systemctl restart womcast-playback`
3. Check logs: `journalctl -u womcast-playback -n 50`

### Database Locked Errors
**Symptoms**: `sqlite3.OperationalError: database is locked`  
**Checks**:
- Check for concurrent operations
- Review active connections: `lsof /data/metadata.db`

**Fix**:
1. Stop services: `sudo systemctl stop womcast-*`
2. Wait for lock release (timeout: 30s)
3. Restart services: `sudo systemctl start womcast-*`

---

## Backup/Restore

### Manual Backup
```bash
# Database
cp /data/metadata.db /storage/backup/metadata_$(date +%Y%m%d).db

# User preferences
cp /data/user_preferences.json /storage/backup/

# Full backup (UI)
# Settings → System → Export → Choose destination
```

### Restore from Backup
```bash
# Database
sudo systemctl stop womcast-metadata
cp /storage/backup/metadata_20251102.db /data/metadata.db
sudo systemctl start womcast-metadata

# UI restore
# Place archive at /storage/backup
# Settings → System → Import → Select file
```

---

## System Maintenance

### Update Services
```bash
# Pull latest images
cd /opt/womcast
git pull origin main

# Rebuild services
docker-compose build
docker-compose up -d

# Verify health
curl http://localhost:3000/healthz
```

### Clear Cache
```bash
# Metadata cache
rm -rf /data/cache/metadata/*

# Frontend cache
rm -rf ~/.cache/womcast/

# Restart services
sudo systemctl restart womcast-*
```

---

**Document Maintainer**: AI Agent (GitHub Copilot)  
**Last Updated**: 2025-11-02 18:30 UTC  
**Milestone**: M2 Storage & Library