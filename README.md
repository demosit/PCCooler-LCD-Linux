# PCCooler LCD Manager

Open-source LCD display manager for PCCooler liquid cooling systems.

Developed and tested on Gentoo Linux with KDE Plasma.

## Current features

- CPU temperature monitoring
- GPU temperature monitoring
- Clock display
- Transparent 240x320 OSD
- Qt6 graphical configuration editor
- Drag-and-drop positioning
- Font size adjustment
- Text color customization
- JSON configuration
- Automatic display updates
- systemd user service
- USB HID communication without the official Windows CP3 software

## Tested hardware

PCCooler 360 Pro ARGB Display

USB identification:

- Vendor ID: `1D6B`
- Product ID: `0112`
- Manufacturer: CP3 Inc.
- Product: CP3 USB Device

Other devices have not been tested.

## Requirements

- Linux
- Python 3
- PySide6
- Pillow
- Python hidapi bindings
- systemd (for automatic startup)

## Project structure

- `main.py` — Qt6 graphical editor
- `config.py` — configuration management
- `sensors.py` — hardware temperature sensors
- `renderer.py` — PNG rendering
- `usb_display.py` — USB HID communication
- `display_worker.py` — background display updater
- `data/cp3-packets.json` — captured HID packet templates

## Configuration

User configuration:

`~/.config/pccooler-lcd/config.json`

The editor allows changing text positions, colors and font sizes.

## Development status

The Linux prototype is functional.

The installer, hardware compatibility improvements and Windows support
are under development.

## Planned features

- Temperature graphs
- Sensor selection
- Intel and NVIDIA support
- Background image customization
- Windows version
- Support for additional compatible displays

## Disclaimer

This is an independent community project.

It is not affiliated with PCCooler or CP3 Inc.

Use it at your own risk.
