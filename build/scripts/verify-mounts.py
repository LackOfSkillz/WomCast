#!/usr/bin/env python3
"""
WomCast USB Mount Verification Script
Tests USB auto-mount functionality and permissions.
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple


def check_mount_point(path: str) -> Tuple[bool, str]:
    """Check if path is mounted and accessible."""
    path_obj = Path(path)
    
    if not path_obj.exists():
        return False, f"Path does not exist: {path}"
    
    if not path_obj.is_mount():
        return False, f"Path is not a mount point: {path}"
    
    # Check read access
    if not os.access(path, os.R_OK):
        return False, f"No read access to: {path}"
    
    # Check write access (for womcast user)
    test_file = path_obj / ".womcast_test"
    try:
        test_file.touch()
        test_file.unlink()
        return True, f"Mount point OK: {path}"
    except PermissionError:
        return False, f"No write access to: {path}"
    except Exception as e:
        return False, f"Error testing write access: {e}"


def list_usb_mounts() -> List[str]:
    """List all USB mount points in /media/."""
    media_dir = Path("/media")
    
    if not media_dir.exists():
        print("WARNING: /media directory does not exist")
        return []
    
    mounts = []
    for item in media_dir.iterdir():
        if item.is_dir() and item.is_mount():
            mounts.append(str(item))
    
    return mounts


def check_system_exclusions() -> List[str]:
    """Check that system directories are not included in media mounts."""
    forbidden_mounts = ["/boot", "/", "/home", "/usr", "/var", "/etc"]
    
    issues = []
    for mount in forbidden_mounts:
        if Path(mount).exists() and Path(mount).is_mount():
            # Check if it's in our media directory (shouldn't be)
            media_path = Path("/media") / Path(mount).name
            if media_path.exists():
                issues.append(f"System mount {mount} incorrectly in /media")
    
    return issues


def main() -> int:
    """Run mount verification checks."""
    print("=== WomCast USB Mount Verification ===\n")
    
    # Check if running as correct user
    user = os.environ.get("USER", "unknown")
    print(f"Running as: {user}")
    
    if user != "womcast" and os.geteuid() != 0:
        print("WARNING: Should run as 'womcast' user or root\n")
    
    # List all USB mounts
    print("\n--- Detected USB Mounts ---")
    mounts = list_usb_mounts()
    
    if not mounts:
        print("No USB drives mounted in /media/")
        print("\nTo test: Insert a USB drive and check logs:")
        print("  tail -f /var/log/womcast/usb-mount.log")
        return 0
    
    print(f"Found {len(mounts)} USB mount(s):\n")
    
    all_ok = True
    for mount in mounts:
        ok, message = check_mount_point(mount)
        status = "✓" if ok else "✗"
        print(f"  {status} {message}")
        if not ok:
            all_ok = False
    
    # Check system exclusions
    print("\n--- System Directory Exclusions ---")
    issues = check_system_exclusions()
    
    if issues:
        print("✗ Issues found:")
        for issue in issues:
            print(f"  - {issue}")
        all_ok = False
    else:
        print("✓ No system directories in media mounts")
    
    # Check udev rule
    print("\n--- Configuration Files ---")
    udev_rule = Path("/etc/udev/rules.d/99-womcast-usb.rules")
    mount_script = Path("/opt/womcast/build/scripts/usb-mount.sh")
    
    if udev_rule.exists():
        print(f"✓ udev rule installed: {udev_rule}")
    else:
        print(f"✗ udev rule missing: {udev_rule}")
        all_ok = False
    
    if mount_script.exists() and os.access(mount_script, os.X_OK):
        print(f"✓ Mount script installed: {mount_script}")
    else:
        print(f"✗ Mount script missing or not executable: {mount_script}")
        all_ok = False
    
    # Final result
    print("\n" + "="*50)
    if all_ok:
        print("✓ All checks passed!")
        return 0
    else:
        print("✗ Some checks failed (see above)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
