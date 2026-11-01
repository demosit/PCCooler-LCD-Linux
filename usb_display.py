#!/usr/bin/env python3
"""
PCCooler LCD USB transport v2.

Uses the independently reconstructed CP3 HID protocol for packet generation and USB HID transmission.
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

    packets = build_transfer(
        data=png,
        filename=filename,
        transfer_id=transfer_id,
        sequence_number=sequence_number,
        start_date=timestamp,
        end_date=timestamp + 100,
        media_type=MEDIA_OSD,
    )

    return packets


_transfer_id = 0
_sequence_number = 100


def send_image(png):
    """
    Send a transparent OSD PNG using CP3 Protocol v2.
    """

    global _transfer_id, _sequence_number

    packets = prepare_image(
        png,
        transfer_id=_transfer_id,
        sequence_number=_sequence_number,
    )

    device = hid.device()

    try:
        device.open(VID, PID)

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

    finally:
        device.close()

    _transfer_id = (_transfer_id + 1) % 60
    _sequence_number += 2


def send_background(path):
    """
    Upload an MP4 background using CP3 Protocol v2.

    WARNING: Replaces the current background on the LCD.
    Do not call while another process owns the HID device.
    """

    global _transfer_id, _sequence_number

    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(path)

    if path.suffix.lower() not in (".png", ".mp4"):
        raise USBDisplayError(
            "Background must be a PNG or MP4 file"
        )

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

    device = hid.device()

    try:
        device.open(VID, PID)

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

    finally:
        device.close()

    _transfer_id = (_transfer_id + 1) % 60
    _sequence_number += 2

    return len(data)


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


def wake_display():
    """
    Initialize and wake the LCD controller.

    Reconstructed from the original CP3 startup sequence.
    """

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

    device = hid.device()

    try:
        device.open(VID, PID)

        for packet in packets:
            written = device.write(packet)

            if written != len(packet):
                raise USBDisplayError(
                    f"Wake command short write: "
                    f"{written}/{len(packet)}"
                )

            time.sleep(0.5)

    finally:
        device.close()

    print("PCCooler LCD awakened", flush=True)
