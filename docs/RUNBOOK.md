# WomCast — Runbook

## First Boot
1) Setup wizard (language, Wi-Fi, PIN, theme, mic test)
2) Verify services via System → About

## Common Tasks
### Rebuild Library Index
- UI: Settings → Library → Rebuild

### OTA Rollback
- Settings → System → Updates → Previous Version

## Troubleshooting
### No HDMI-CEC response
Checks: cable supports CEC; run cec-client -l
Fix: restart CEC mapper; use IR fallback

## Backup/Restore
- Backup: Settings → System → Export
- Restore: place archive at /storage/backup then Import