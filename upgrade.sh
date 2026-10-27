#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.local/share/pccooler-lcd"

SERVICE="pccooler-lcd.service"

BACKUP_ROOT="$HOME/PCCooler-Upgrade-Backups"
TIMESTAMP="$(date +%Y-%m-%d_%H-%M-%S)"

BACKUP="$BACKUP_ROOT/$TIMESTAMP"
STAGING="$HOME/.local/share/.pccooler-staging-$TIMESTAMP"

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
echo " PCCooler LCD Manager Upgrader"
echo "===================================="
echo

if [[ ! -d "$DEST" ]]; then
    echo "ERROR: Existing installation not found."
    echo "Use install.sh for a fresh installation."
    exit 1
fi

for file in "${FILES[@]}"; do
    if [[ ! -f "$SOURCE/$file" ]]; then
        echo "ERROR: Missing $file"
        exit 1
    fi
done

echo "Checking Python syntax..."

python3 - "$SOURCE" "${FILES[@]}" <<'PY'
import ast
import sys
from pathlib import Path

root = Path(sys.argv[1])

for name in sys.argv[2:]:
    ast.parse((root / name).read_text(encoding="utf-8"))

print("Python syntax: PASS")
PY

mkdir -p "$BACKUP_ROOT"

if [[ -e "$BACKUP" || -e "$STAGING" ]]; then
    echo "ERROR: Backup or staging already exists."
    exit 1
fi

echo "Creating backup..."

mkdir "$BACKUP"
cp -a "$DEST" "$BACKUP/application"

echo "Preparing update..."

mkdir "$STAGING"

for file in "${FILES[@]}"; do
    install -m 644 "$SOURCE/$file" "$STAGING/$file"
done

python3 -m compileall -q "$STAGING"

WAS_ACTIVE=0

if systemctl --user is-active --quiet "$SERVICE"; then
    WAS_ACTIVE=1
fi

rollback() {
    local status=$?

    trap - ERR INT TERM

    echo
    echo "ERROR: Upgrade failed (status $status)."
    echo "Restoring previous application..."

    systemctl --user stop "$SERVICE" || true

    if [[ -d "$BACKUP/application" ]]; then
        rm -rf -- "$DEST"
        cp -a "$BACKUP/application" "$DEST"
    fi

    if (( WAS_ACTIVE )); then
        systemctl --user start "$SERVICE" || true
    fi

    echo "Rollback completed."
    exit "$status"
}

trap rollback ERR INT TERM

echo
echo "Stopping Worker for update..."

systemctl --user stop "$SERVICE"

echo "Replacing application files..."

rm -rf -- "$DEST"
mv "$STAGING" "$DEST"

echo "Restoring Worker state..."

if (( WAS_ACTIVE )); then
    systemctl --user start "$SERVICE"

    sleep 5

    systemctl --user is-active --quiet "$SERVICE"

    PID_BEFORE="$(systemctl --user show "$SERVICE" -p MainPID --value)"

    [[ -n "$PID_BEFORE" && "$PID_BEFORE" != "0" ]]

    sleep 5

    PID_AFTER="$(systemctl --user show "$SERVICE" -p MainPID --value)"

    [[ "$PID_BEFORE" == "$PID_AFTER" ]]
fi

trap - ERR INT TERM

echo
echo "===================================="
echo " UPGRADE COMPLETED"
echo "===================================="
echo
echo "Backup: $BACKUP"
echo "Configuration: preserved"
echo "Backgrounds: preserved"
echo "Worker state: restored"
