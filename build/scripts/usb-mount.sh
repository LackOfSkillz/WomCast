#!/bin/bash
# WomCast USB Auto-Mount Service
# Mounts USB drives to /media/<label> or /media/usb-<device>
# Called by udev rule on USB insertion

set -e

# Configuration
MOUNT_BASE="/media"
LOG_FILE="/var/log/womcast/usb-mount.log"
ALLOWED_FS="vfat,exfat,ntfs,ext4,ext3,ext2"

# Get device info
DEVICE="$1"
ACTION="$2"

log() {
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $*" >> "$LOG_FILE"
}

if [ -z "$DEVICE" ] || [ -z "$ACTION" ]; then
    log "ERROR: Missing device or action parameter"
    exit 1
fi

# Get device label or use device name
LABEL=$(blkid -s LABEL -o value "$DEVICE" 2>/dev/null | tr ' ' '_')
if [ -z "$LABEL" ]; then
    LABEL="usb-$(basename "$DEVICE")"
fi

MOUNT_POINT="$MOUNT_BASE/$LABEL"

case "$ACTION" in
    add)
        # Check filesystem type
        FS_TYPE=$(blkid -s TYPE -o value "$DEVICE" 2>/dev/null)
        
        if ! echo "$ALLOWED_FS" | grep -qw "$FS_TYPE"; then
            log "WARNING: Unsupported filesystem $FS_TYPE on $DEVICE, skipping"
            exit 0
        fi
        
        # Check if already mounted
        if mountpoint -q "$MOUNT_POINT"; then
            log "INFO: $MOUNT_POINT already mounted"
            exit 0
        fi
        
        # Create mount point
        mkdir -p "$MOUNT_POINT"
        
        # Mount with appropriate options
        case "$FS_TYPE" in
            vfat|exfat)
                mount -o uid=1000,gid=1000,umask=022,iocharset=utf8 "$DEVICE" "$MOUNT_POINT"
                ;;
            ntfs)
                mount -o uid=1000,gid=1000,umask=022,windows_names "$DEVICE" "$MOUNT_POINT"
                ;;
            ext*)
                mount -o defaults "$DEVICE" "$MOUNT_POINT"
                chown -R womcast:womcast "$MOUNT_POINT"
                ;;
        esac
        
        if [ $? -eq 0 ]; then
            log "SUCCESS: Mounted $DEVICE ($FS_TYPE) at $MOUNT_POINT"
            
            # Trigger metadata indexer (notify via HTTP)
            curl -X POST http://localhost:3001/api/scan \
                -H "Content-Type: application/json" \
                -d "{\"path\":\"$MOUNT_POINT\"}" \
                --max-time 2 --silent || true
        else
            log "ERROR: Failed to mount $DEVICE"
            rmdir "$MOUNT_POINT" 2>/dev/null || true
            exit 1
        fi
        ;;
        
    remove)
        if mountpoint -q "$MOUNT_POINT"; then
            umount "$MOUNT_POINT"
            if [ $? -eq 0 ]; then
                log "SUCCESS: Unmounted $MOUNT_POINT"
                rmdir "$MOUNT_POINT" 2>/dev/null || true
            else
                log "ERROR: Failed to unmount $MOUNT_POINT"
                exit 1
            fi
        fi
        ;;
        
    *)
        log "ERROR: Unknown action $ACTION"
        exit 1
        ;;
esac

exit 0
