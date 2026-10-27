#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

DEST="$HOME/.local/share/pccooler-lcd"
APPS="$HOME/.local/share/applications"
SERVICES="$HOME/.config/systemd/user"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"

SERVICE="pccooler-lcd.service"

if command -v xdg-user-dir >/dev/null 2>&1; then
    DESKTOP="$(xdg-user-dir DESKTOP)"
else
    DESKTOP="$HOME/Desktop"
fi

FILES=(
    main.py
    manager_v2.py
    background_editor.py
    background_jobs.py
    background_worker.py
    gif_exporter.py
    video_preview.py
    config.py
    sensors.py
    renderer.py
    display_worker.py
    usb_display.py
    usb_protocol_v2.py
)

echo "===================================="
echo " PCCooler LCD Manager Installer"
echo "===================================="
echo

if [[ -e "$DEST" ]]; then
    echo "ERROR: Existing installation detected:"
    echo "$DEST"
    echo
    echo "Use upgrade.sh to update an existing installation."
    exit 1
fi

echo "Checking application files..."

for file in "${FILES[@]}"; do
    [[ -f "$SOURCE/$file" ]] || {
        echo "ERROR: Missing $file"
        exit 1
    }
done

for file in \
    assets/pccooler-lcd.png \
    systemd/pccooler-lcd.service
do
    [[ -f "$SOURCE/$file" ]] || {
        echo "ERROR: Missing $file"
        exit 1
    }
done

echo "Checking dependencies..."

command -v python3 >/dev/null || {
    echo "ERROR: Python 3 is required."
    exit 1
}

command -v ffmpeg >/dev/null || {
    echo "ERROR: FFmpeg is required."
    exit 1
}

command -v systemctl >/dev/null || {
    echo "ERROR: systemd is required."
    exit 1
}

python3 - <<'PY'
from PySide6.QtWidgets import QApplication
from PIL import Image
import hid

print("Python dependencies: OK")
PY

echo
echo "Installing application..."

mkdir -p "$DEST" "$APPS" "$SERVICES" "$ICON_DIR"

for file in "${FILES[@]}"; do
    install -m 644 "$SOURCE/$file" "$DEST/$file"
done

install -m 644 \
    "$SOURCE/assets/pccooler-lcd.png" \
    "$ICON_DIR/pccooler-lcd.png"

ICON="$ICON_DIR/pccooler-lcd.png"

cat > "$APPS/pccooler-lcd.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=PCCooler LCD Manager
Comment=Configure PCCooler LCD display
Exec=/usr/bin/python3 $DEST/manager_v2.py
Icon=$ICON
Terminal=false
Categories=Settings;HardwareSettings;
StartupNotify=true
EOF

chmod 644 "$APPS/pccooler-lcd.desktop"

if [[ -d "$DESKTOP" ]]; then
    cp "$APPS/pccooler-lcd.desktop" \
       "$DESKTOP/PCCooler LCD Manager.desktop"

    chmod +x "$DESKTOP/PCCooler LCD Manager.desktop"
fi

install -m 644 \
    "$SOURCE/systemd/pccooler-lcd.service" \
    "$SERVICES/$SERVICE"

systemctl --user daemon-reload

echo
echo "===================================="
echo " INSTALLATION COMPLETED"
echo "===================================="
echo
echo "Application: $DEST"
echo "GUI: python3 $DEST/manager_v2.py"
echo
echo "Service installed but not started."
echo "To enable automatic startup:"
echo "  systemctl --user enable --now $SERVICE"
echo
echo "User configuration and backgrounds were preserved."
echo
echo "USB access requires the appropriate udev rule."
