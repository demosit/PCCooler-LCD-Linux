#!/usr/bin/env bash
set -euo pipefail

DEST="$HOME/.local/share/pccooler-lcd"
APPS="$HOME/.local/share/applications/pccooler-lcd.desktop"
SERVICE="$HOME/.config/systemd/user/pccooler-lcd.service"
DESKTOP="$HOME/Desktop/PCCooler LCD Manager.desktop"

echo "====================================="
echo " PCCooler LCD Manager Uninstaller"
echo "====================================="
echo

read -r -p "Remove PCCooler LCD Manager? [y/N]: " answer

if [[ ! "$answer" =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo "Stopping the new service (if present)..."

systemctl --user disable --now pccooler-lcd.service 2>/dev/null || true

rm -f "$SERVICE"
systemctl --user daemon-reload

rm -f "$HOME/.local/share/icons/hicolor/256x256/apps/pccooler-lcd.png"
rm -f "$APPS"
rm -f "$DESKTOP"

if [[ -d "$DEST" ]]; then
    rm -r -- "$DEST"
fi

echo
echo "Application removed."
echo "User configuration was preserved."
echo "Existing cp3-monitor.service was not modified."
