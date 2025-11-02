#!/bin/bash
# WomCast Pi 5 Installation Script
# Installs and configures WomCast services on Raspberry Pi OS Lite

set -e

INSTALL_DIR="/opt/womcast"
LOG_DIR="/var/log/womcast"
DATA_DIR="/data"
MEDIA_DIR="/media"

echo "=== WomCast Pi 5 Installation ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Must run as root (use sudo)"
    exit 1
fi

# Check if Pi 5
if ! grep -q "Raspberry Pi 5" /proc/cpuinfo; then
    echo "WARNING: Not running on Raspberry Pi 5, continuing anyway..."
fi

# Create directories
echo "Creating directories..."
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"
mkdir -p "$MEDIA_DIR"
chown -R womcast:womcast "$LOG_DIR" "$DATA_DIR"

# Install udev rule
echo "Installing USB auto-mount udev rule..."
cp "$INSTALL_DIR/build/scripts/99-womcast-usb.rules" /etc/udev/rules.d/
cp "$INSTALL_DIR/build/scripts/usb-mount.sh" "$INSTALL_DIR/build/scripts/"
chmod +x "$INSTALL_DIR/build/scripts/usb-mount.sh"
udevadm control --reload-rules
udevadm trigger

# Create systemd service for gateway
echo "Creating systemd services..."

cat > /etc/systemd/system/womcast-gateway.service <<EOF
[Unit]
Description=WomCast API Gateway
After=network.target

[Service]
Type=simple
User=womcast
WorkingDirectory=$INSTALL_DIR/apps/backend
Environment="PATH=$INSTALL_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$INSTALL_DIR/.venv/bin/uvicorn gateway.main:app --host 0.0.0.0 --port 3000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Metadata service
cat > /etc/systemd/system/womcast-metadata.service <<EOF
[Unit]
Description=WomCast Metadata Service
After=network.target

[Service]
Type=simple
User=womcast
WorkingDirectory=$INSTALL_DIR/apps/backend
Environment="PATH=$INSTALL_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="DB_PATH=$DATA_DIR/metadata.db"
ExecStart=$INSTALL_DIR/.venv/bin/uvicorn metadata.main:app --host 0.0.0.0 --port 3001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Playback service
cat > /etc/systemd/system/womcast-playback.service <<EOF
[Unit]
Description=WomCast Playback Service
After=network.target kodi.service

[Service]
Type=simple
User=womcast
WorkingDirectory=$INSTALL_DIR/apps/backend
Environment="PATH=$INSTALL_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$INSTALL_DIR/.venv/bin/uvicorn playback.main:app --host 0.0.0.0 --port 3002
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Voice service
cat > /etc/systemd/system/womcast-voice.service <<EOF
[Unit]
Description=WomCast Voice Service
After=network.target

[Service]
Type=simple
User=womcast
WorkingDirectory=$INSTALL_DIR/apps/backend
Environment="PATH=$INSTALL_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="WHISPER_CACHE_DIR=$DATA_DIR/models/whisper"
ExecStart=$INSTALL_DIR/.venv/bin/uvicorn voice.main:app --host 0.0.0.0 --port 3003
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Search service
cat > /etc/systemd/system/womcast-search.service <<EOF
[Unit]
Description=WomCast Search Service
After=network.target

[Service]
Type=simple
User=womcast
WorkingDirectory=$INSTALL_DIR/apps/backend
Environment="PATH=$INSTALL_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="CHROMA_DB_PATH=$DATA_DIR/chroma"
ExecStart=$INSTALL_DIR/.venv/bin/uvicorn search.main:app --host 0.0.0.0 --port 3004
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Enable services (don't start yet)
echo "Enabling services..."
systemctl enable womcast-gateway
systemctl enable womcast-metadata
systemctl enable womcast-playback
systemctl enable womcast-voice
systemctl enable womcast-search

# Configure Avahi for mDNS
echo "Configuring mDNS (womcast.local)..."
cat > /etc/avahi/services/womcast.service <<EOF
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">WomCast on %h</name>
  <service>
    <type>_http._tcp</type>
    <port>3000</port>
    <txt-record>version=0.1.0</txt-record>
    <txt-record>device=womcast</txt-record>
  </service>
</service-group>
EOF

systemctl restart avahi-daemon

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Services installed but NOT started. To start:"
echo "  sudo systemctl start womcast-gateway"
echo "  sudo systemctl start womcast-metadata"
echo "  sudo systemctl start womcast-playback"
echo "  sudo systemctl start womcast-voice"
echo "  sudo systemctl start womcast-search"
echo ""
echo "Access WomCast at: http://womcast.local:3000"
echo "                or http://$(hostname -I | awk '{print $1}'):3000"
echo ""
echo "USB drives will auto-mount to /media/<label>"
echo ""
