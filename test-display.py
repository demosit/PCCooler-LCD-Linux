import sys
import json
import time
import struct
import zlib
from pathlib import Path

import hid

VID = 0x1D6B
PID = 0x0112
TARGET_SIZE = 5264

PROJECT = Path.home() / "PCCooler-LCD-Linux"
PACKETS = Path.home() / "CP3-analysis/cp3-packets.json"

def pad_png(png, target):
    extra = target - len(png)

    if extra < 0:
        raise RuntimeError("PNG слишком большой")

    if extra == 0:
        return png

    if extra < 12:
        raise RuntimeError("Недостаточно места")

    payload = b"x" * (extra - 12)
    chunk_type = b"vpAg"

    chunk = (
        struct.pack(">I", len(payload))
        + chunk_type
        + payload
        + struct.pack(
            ">I",
            zlib.crc32(chunk_type + payload) & 0xffffffff
        )
    )

    return png[:-12] + chunk + png[-12:]

def send_image(png):
    data = json.loads(PACKETS.read_text())

    frame = [
        bytes.fromhex(packet)
        for packet in data["frame"]
    ]

    binary = [
        p for p in frame
        if len(p) >= 25 and p[1] == 0x5C
    ]

    png = pad_png(png, TARGET_SIZE)

    packets = []
    offset = 0

    for packet in binary:
        capacity = len(packet) - 25
        chunk = png[offset:offset + capacity]
        packets.append(packet[:25] + chunk)
        offset += capacity

    if offset != TARGET_SIZE:
        raise RuntimeError("Размер пакетов не совпадает")

    device = hid.device()
    device.open(VID, PID)

    try:
        sequence = [frame[0], *packets, frame[-1]]

        for packet in sequence:
            device.write(packet)
            time.sleep(0.02)
    finally:
        device.close()

if __name__ == "__main__":
    png = (PROJECT / "preview-optimized.png").read_bytes()
    print("Отправляем PNG:", len(png), "байт")
    send_image(png)
    print("Готово!")
