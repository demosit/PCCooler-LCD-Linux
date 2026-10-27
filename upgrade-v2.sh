#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE="$HOME/PCCooler-LCD-Manager-Release"
DEST="$HOME/.local/share/pccooler-lcd"

CONFIG_DIR="$HOME/.config/pccooler-lcd"
DEV_CONFIG="$HOME/.config/pccooler-lcd-dev/config.json"

STATE_DIR="$HOME/.local/state/pccooler-lcd"
DEV_STATE="$HOME/.local/state/pccooler-lcd-v2"

SERVICE="pccooler-lcd.service"

APPS="$HOME/.local/share/applications"
DESKTOP_FILE="$APPS/pccooler-lcd.desktop"

if command -v xdg-user-dir >/dev/null 2>&1; then
    DESKTOP="$(xdg-user-dir DESKTOP)"
else
    DESKTOP="$HOME/Desktop"
fi

TIMESTAMP="$(date +%Y-%m-%d_%H-%M-%S)"
BACKUP="$HOME/PCCooler-Production-Rollback-$TIMESTAMP"

STAGING="$HOME/.local/share/.pccooler-lcd-staging-$TIMESTAMP"

echo "PCCooler LCD Manager V2 Upgrade"
echo

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
)

for file in "${REQUIRED[@]}"; do
    if [[ ! -f "$SOURCE/$file" ]]; then
        echo "ERROR: Missing $file"
        exit 1
    fi
done

if [[ ! -d "$DEST" ]]; then
    echo "ERROR: Existing installation not found."
    exit 1
fi

if [[ ! -f "$DEV_CONFIG" ]]; then
    echo "ERROR: Development configuration not found."
    exit 1
fi

if [[ -e "$BACKUP" || -e "$STAGING" ]]; then
    echo "ERROR: Backup or staging directory already exists."
    exit 1
fi

if ! systemctl --user is-active --quiet "$SERVICE"; then
    echo "ERROR: Original service is not active."
    exit 1
fi

echo "Preparing rollback backup..."

mkdir -p "$BACKUP"

cp -a "$DEST" "$BACKUP/application"
cp -a "$CONFIG_DIR" "$BACKUP/config"

if [[ -f "$DESKTOP_FILE" ]]; then
    cp -a "$DESKTOP_FILE" "$BACKUP/menu.desktop"
fi

if [[ -f "$DESKTOP/PCCooler LCD Manager.desktop" ]]; then
    cp -a \
        "$DESKTOP/PCCooler LCD Manager.desktop" \
        "$BACKUP/desktop.desktop"
fi

echo "Preparing new application..."

mkdir -p "$STAGING"

for file in "${REQUIRED[@]}"; do
    install -m 644 "$SOURCE/$file" "$STAGING/$file"
done

python3 -m compileall -q "$STAGING"

echo "Preparing background library..."

if [[ ! -d "$STATE_DIR" ]]; then
    if [[ -d "$DEV_STATE" ]]; then
        cp -a "$DEV_STATE" "$STATE_DIR"
    else
        mkdir -p "$STATE_DIR"
    fi
fi

echo
echo "Rollback backup:"
echo "$BACKUP"
echo

UPGRADE_STARTED=0

rollback() {
    status=$?

    trap - ERR INT TERM EXIT

    if [[ "$UPGRADE_STARTED" -eq 1 ]]; then
        echo
        echo "ERROR: Upgrade failed. Restoring previous version..."

        systemctl --user stop "$SERVICE" || true

        if [[ -d "$BACKUP/application" ]]; then
            rm -rf -- "$DEST"
            cp -a "$BACKUP/application" "$DEST"
        fi

        if [[ -d "$BACKUP/config" ]]; then
            rm -rf -- "$CONFIG_DIR"
            cp -a "$BACKUP/config" "$CONFIG_DIR"
        fi

        if [[ -f "$BACKUP/menu.desktop" ]]; then
            cp -a "$BACKUP/menu.desktop" "$DESKTOP_FILE"
        fi

        if [[ -f "$BACKUP/desktop.desktop" ]]; then
            cp -a "$BACKUP/desktop.desktop" \
                "$DESKTOP/PCCooler LCD Manager.desktop"
        fi

        systemctl --user start "$SERVICE" || true

        echo "Rollback attempted."
        systemctl --user is-active "$SERVICE" || true
    fi

    exit "$status"
}

trap rollback ERR INT TERM

echo "Stopping original service..."

UPGRADE_STARTED=1
systemctl --user stop "$SERVICE"

if systemctl --user is-active --quiet "$SERVICE"; then
    echo "ERROR: Service did not stop."
    false
fi

echo "Installing Protocol v2..."

rm -rf -- "$DEST"
mv "$STAGING" "$DEST"

echo "Installing development OSD configuration..."

mkdir -p "$CONFIG_DIR"
cp -a "$DEV_CONFIG" "$CONFIG_DIR/config.json"

echo "Updating application shortcuts..."

ICON="$HOME/.local/share/icons/hicolor/256x256/apps/pccooler-lcd.png"

cat > "$DESKTOP_FILE" <<EOF
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

chmod 644 "$DESKTOP_FILE"

if [[ -d "$DESKTOP" ]]; then
    cp "$DESKTOP_FILE" \
        "$DESKTOP/PCCooler LCD Manager.desktop"

    chmod +x \
        "$DESKTOP/PCCooler LCD Manager.desktop"
fi

echo
echo "Starting V2 service..."
echo "LOOK AT THE PHYSICAL DISPLAY NOW."
echo

systemctl --user start "$SERVICE"

sleep 7

if ! systemctl --user is-active --quiet "$SERVICE"; then
    echo "ERROR: V2 service is not active."
    false
fi

if ! systemctl --user is-enabled --quiet "$SERVICE"; then
    echo "ERROR: Service is not enabled."
    false
fi

echo
echo "Recent service log:"

journalctl --user \
    -u "$SERVICE" \
    -n 18 \
    --no-pager

echo
echo "Checking V2 Worker stability..."

PID_BEFORE="$(systemctl --user show "$SERVICE" -p MainPID --value)"

if [[ -z "$PID_BEFORE" || "$PID_BEFORE" == "0" ]]; then
    echo "ERROR: V2 Worker has no running process."
    false
fi

sleep 5

PID_AFTER="$(systemctl --user show "$SERVICE" -p MainPID --value)"

if [[ "$PID_BEFORE" != "$PID_AFTER" ]]; then
    echo "ERROR: V2 Worker restarted unexpectedly."
    false
fi

if ! systemctl --user is-active --quiet "$SERVICE"; then
    echo "ERROR: V2 Worker is no longer active."
    false
fi

echo "V2 Worker stability: PASS"

trap - ERR INT TERM

echo
echo "===================================="
echo " V2 UPGRADE COMPLETED"
echo "===================================="
echo
echo "Service:"
systemctl --user is-active "$SERVICE"

echo
echo "Rollback backup:"
echo "$BACKUP"

echo
echo "New GUI:"
echo "python3 $DEST/manager_v2.py"
