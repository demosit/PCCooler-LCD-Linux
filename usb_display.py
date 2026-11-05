#!/usr/bin/env python3
"""
PCCooler LCD USB transport v2.

Keeps one HID connection open and reuses it for OSD frames,
background uploads, and wake commands.
"""

import time
import hid
from pathlib import Path

from usb_protocol_v2 import build_transfer, build_command, make_text_packet


VID = 0x1D6B
PID = 0x0112

MEDIA_BACKGROUND = 0
MEDIA_OSD = 1

MAX_FILE_SIZE = 65535 * 1000


class USBDisplayError(Exception):
    pass


_device = None
_transfer_id = 0
_sequence_number = 100


def _get_device():
    """Return the shared HID device, opening it only when necessary."""
    global _device

    if _device is None:
        device = hid.device()
        try:
            device.open(VID, PID)
        except Exception:
            try:
                device.close()
            except Exception:
                pass
            raise
        _device = device

    return _device


def _disconnect():
    """Close and forget the shared HID handle."""
    global _device

    device = _device
    _device = None

    if device is not None:
        try:
            device.close()
        except Exception:
            pass


def close_display():
    """Close the persistent HID connection during worker shutdown."""
    _disconnect()


def _write_packets(packets):
    """Write packets through the shared connection."""
    try:
        device = _get_device()

        for index, packet in enumerate(packets):
            if len(packet) > 1025:
                raise USBDisplayError(
                    f"Packet {index} exceeds HID report size"
                )

            written = device.write(packet)

            if written != len(packet):
                raise USBDisplayError(
                    f"Short HID write: packet {index}, "
                    f"{written}/{len(packet)} bytes"
                )

            time.sleep(0.02)

    except Exception:
        # A failed handle is discarded; the next operation can reopen it.
        _disconnect()
        raise


def prepare_image(
    png,
    transfer_id=1,
    sequence_number=100,
):
    """
    Generate HID packets for an OSD PNG.

    No USB communication.
    """

    if not isinstance(png, bytes):
        raise TypeError("PNG data must be bytes")

    if not png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise USBDisplayError("Invalid PNG signature")

    if not png:
        raise USBDisplayError("Empty PNG")

    if len(png) > MAX_FILE_SIZE:
        raise USBDisplayError("Image exceeds protocol size limit")

    timestamp = int(time.time() * 1000)
    filename = f"{timestamp}.osd"

    return build_transfer(
        data=png,
        filename=filename,
        transfer_id=transfer_id,
        sequence_number=sequence_number,
        start_date=timestamp,
        end_date=timestamp + 100,
        media_type=MEDIA_OSD,
    )


def send_image(png):
    """Send a transparent OSD PNG using CP3 Protocol v2."""
    global _transfer_id, _sequence_number

    packets = prepare_image(
        png,
        transfer_id=_transfer_id,
        sequence_number=_sequence_number,
    )

    _write_packets(packets)

    _transfer_id = (_transfer_id + 1) % 60
    _sequence_number += 2


def send_background(path):
    """
    Upload an MP4 background using CP3 Protocol v2.

    WARNING: Replaces the current background on the LCD.
    """

    global _transfer_id, _sequence_number

    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(path)

    if path.suffix.lower() not in (".png", ".mp4"):
        raise USBDisplayError("Background must be a PNG or MP4 file")

    data = path.read_bytes()

    if not data:
        raise USBDisplayError("Background file is empty")

    if len(data) > MAX_FILE_SIZE:
        raise USBDisplayError("Background exceeds protocol size limit")

    timestamp = int(time.time() * 1000)

    packets = build_transfer(
        data=data,
        filename=path.name,
        transfer_id=_transfer_id,
        sequence_number=_sequence_number,
        start_date=timestamp,
        end_date=timestamp + 100,
        media_type=MEDIA_BACKGROUND,
    )

    _write_packets(packets)

    _transfer_id = (_transfer_id + 1) % 60
    _sequence_number += 2

    return len(data)


def wake_display():
    """Initialize and wake the LCD controller."""
    timestamp = int(time.time() * 1000)

    packets = [
        make_text_packet(
            f"POST conn 1\\r\\n"
            f"SeqNumber=0\\r\\n"
            f"Date={timestamp}\\r\\n\\r\\n"
        ),
        build_command(
            "power",
            1,
            timestamp + 1,
            {"event": "resume"},
        ),
        build_command(
            "timeout",
            2,
            timestamp + 2,
            {"value": 0},
        ),
    ]

    _write_packets(packets)
    print("PCCooler LCD awakened", flush=True)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python3 usb_display.py image.png")
        sys.exit(1)

    path = Path(sys.argv[1])
    png = path.read_bytes()
    packets = prepare_image(png)

    print("PCCooler USB Protocol v2")
    print("File:", path)
    print("Size:", len(png), "bytes")
    print("HID packets:", len(packets))
    print("Binary packets:", len(packets) - 2)
    print("First packet:", len(packets[0]), "bytes")
    print("Last packet:", len(packets[-1]), "bytes")
    print("USB communication: DISABLED")
