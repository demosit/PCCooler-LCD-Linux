#!/usr/bin/env python3
"""
PCCooler / CP3 USB HID protocol.

Offline packet generator.
No USB communication in this module.
"""

CHUNK_SIZE = 1000
HEADER_SIZE = 25


def escape_bytes(data):
    result = bytearray()

    for byte in data:
        if byte == 0x5A:
            result.extend(b"\x5b\x01")
        elif byte == 0x5B:
            result.extend(b"\x5b\x02")
        else:
            result.append(byte)

    return bytes(result)


def unescape_bytes(data):
    result = bytearray()
    index = 0

    while index < len(data):
        if data[index] == 0x5B:
            if index + 1 >= len(data):
                raise ValueError("Incomplete escape sequence")

            code = data[index + 1]

            if code == 1:
                result.append(0x5A)
            elif code == 2:
                result.append(0x5B)
            else:
                raise ValueError(
                    f"Unknown escape sequence: {code}"
                )

            index += 2
        else:
            result.append(data[index])
            index += 1

    return bytes(result)


def make_text_packet(body):
    if isinstance(body, str):
        body = body.encode("utf-8")

    # 4-byte header + body + checksum
    declared_length = 4 + len(body) + 1

    header = (
        b"\x00\x5a"
        + declared_length.to_bytes(2, "big")
    )

    checksum = (
        sum(header[2:4]) + sum(body)
    ) & 0xFF

    payload = escape_bytes(
        body + bytes([checksum])
    )

    return header + payload + b"\x5a"


def make_binary_packets(data, transfer_id, media_type=0):
    if not 0 <= transfer_id <= 255:
        raise ValueError("Invalid transfer ID")

    count = (
        len(data) + CHUNK_SIZE - 1
    ) // CHUNK_SIZE

    if count > 65535:
        raise ValueError("File too large")

    packets = []

    for index in range(count):
        chunk = data[
            index * CHUNK_SIZE:
            (index + 1) * CHUNK_SIZE
        ]

        packet_length = HEADER_SIZE + len(chunk)

        header = bytearray(HEADER_SIZE)

        header[0] = 0x00
        header[1] = 0x5C

        header[2:4] = (
            packet_length - 4
        ).to_bytes(2, "big")

        header[4] = transfer_id

        header[5:7] = count.to_bytes(2, "big")
        header[7:9] = index.to_bytes(2, "big")

        # 0 = background media, 1 = OSD overlay
        header[9] = media_type

        packets.append(bytes(header) + chunk)

    return packets


import json


def build_command(method, seq, date, payload):
    """
    Build a CP3 text command.

    method: transport / transported
    seq: SeqNumber
    date: Date field
    payload: JSON dictionary
    """

    json_data = json.dumps(
        payload,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")

    body = (
        f"POST {method} 1\r\n"
        f"SeqNumber={seq}\r\n"
        f"Date={date}\r\n"
        f"ContentType=json\r\n"
        f"ContentLength={len(json_data)}\r\n"
        f"\r\n"
    ).encode("utf-8") + json_data

    return make_text_packet(body)


def build_transfer(
    data,
    filename,
    transfer_id,
    sequence_number,
    start_date,
    end_date,
    media_type=0
):
    """
    Build complete HID transfer.
    Does NOT access USB.
    """

    start_payload = {
        "type": "media",
        "fileSize": len(data),
        "fileName": filename
    }

    end_payload = {
        "md5": "todo",
        "fileName": filename
    }

    start = build_command(
        "transport",
        sequence_number,
        start_date,
        start_payload
    )

    binary = make_binary_packets(
        data,
        transfer_id,
        media_type
    )

    end = build_command(
        "transported",
        sequence_number + 1,
        end_date,
        end_payload
    )

    return [start, *binary, end]
