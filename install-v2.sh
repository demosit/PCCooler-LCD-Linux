#!/usr/bin/env bash
set -euo pipefail

SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.local/share/pccooler-lcd"
APPS="$HOME/.local/share/applications"
SERVICES="$HOME/.config/systemd/user"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"

if command -v xdg-user-dir >/dev/null 2>&1; then
    DESKTOP="$(xdg-user-dir DESKTOP)"
else
    DESKTOP="$HOME/Desktop"
fi

REQUIRED=(
    main.py
    manager_v2.py
    background_editor.py
    background_jobs.py
    background_worker.py
    config.py
    sensors.py
    renderer.py
    usb_display.py
    usb_protocol_v2.py
    display_worker.py
    assets/pccooler-lcd.png
    systemd/pccooler-lcd.service
)

echo "PCCooler LCD Manager V2 Installer"
echo

for file in "${REQUIRED[@]}"; do
    if [[ ! -f "$SOURCE/$file" ]]; then
        echo "ERROR: Missing $file"
        exit 1
    fi
done

if [[ -e "$DEST" ]]; then
    echo "ERROR: Existing installation detected:"
    echo "$DEST"
    echo "Installation cancelled to avoid overwriting files."
    exit 1
fi

mkdir -p "$DEST" "$APPS" "$SERVICES" "$ICON_DIR"

for file in \
    main.py \
    manager_v2.py \
    background_editor.py \
    background_jobs.py \
    background_worker.py \
    config.py \
    sensors.py \
    renderer.py \
    usb_display.py \
    usb_protocol_v2.py \
    display_worker.py
do
    install -m 644 "$SOURCE/$file" "$DEST/$file"
done

install -m 644 \
    "$SOURCE/assets/pccooler-lcd.png" \
    "$ICON_DIR/pccooler-lcd.png"

ICON_PATH="$ICON_DIR/pccooler-lcd.png"

cat > "$APPS/pccooler-lcd.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=PCCooler LCD Manager
Comment=Configure PCCooler LCD display
Exec=/usr/bin/python3 $DEST/manager_v2.py
Icon=$ICON_PATH
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
    "$SERVICES/pccooler-lcd.service"

systemctl --user daemon-reload

echo
echo "Installation completed:"
echo "$DEST"
echo
echo "GUI:"
echo "python3 $DEST/manager_v2.py"
echo
echo "Service installed but not started."
echo "User settings and backgrounds were not modified."
