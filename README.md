# PCCooler LCD Manager for Linux

An independent Linux application for configuring and driving the LCD on tested PCCooler liquid-cooling hardware.

Developed and tested on Gentoo Linux with KDE Plasma.

## Features

- 240×320 LCD background editor with crop, scale and rotation
- OSD overlay with clock, CPU and GPU temperatures
- Editable text positions, sizes and colors
- PNG and animated-background preparation
- Background upload queue handled by a single USB worker
- USB HID communication using a reconstructed CP3 protocol
- systemd user service

## Tested hardware

**PCCooler 360 Pro ARGB Display**

USB identification reported by the tested device:

- Vendor ID: `1D6B`
- Product ID: `0112`
- Manufacturer: CP3 Inc.
- Product: CP3 USB Device

Other devices have not been tested. Compatibility is not guaranteed.

## Requirements

- Linux and Python 3
- PySide6
- Pillow
- Python hidapi bindings
- FFmpeg (for animated backgrounds)
- systemd (for automatic startup)

## Main files

- `manager_v2.py` — starts the Qt6 graphical editor
- `background_editor.py` — image and background editor
- `main.py` — shared editable OSD text items
- `config.py` — user configuration
- `sensors.py` — hardware temperature readings
- `renderer.py` — OSD PNG rendering
- `display_worker.py` — single background/USB worker
- `background_jobs.py` — background upload queue
- `background_worker.py` — queue processing
- `usb_display.py` — USB HID transport
- `usb_protocol_v2.py` — packet construction
- `gif_exporter.py`, `video_preview.py` — animated-background support
- `install.sh`, `upgrade.sh`, `uninstall.sh` — installation lifecycle scripts

## Configuration and state

Configuration:

`~/.config/pccooler-lcd/config.json`

Application state and background queue:

`~/.local/state/pccooler-lcd/`

## Installation

Run:

```bash
./install.sh
```

The installer places the application under `~/.local/share/pccooler-lcd`. It installs the systemd user service but does not enable or start it automatically.

## Disclaimer

This is an independent community project. It is not affiliated with, endorsed by, or supported by PCCooler or CP3 Inc.

PCCooler and CP3 names are used only to identify compatible hardware. Their trademarks and any third-party rights remain with their respective owners. The project license applies to this repository's own code; it does not grant rights to third-party trademarks, software, firmware, or other materials.

The USB protocol implementation was independently reconstructed through protocol analysis. No official CP3 application source code is included.

Use at your own risk.
