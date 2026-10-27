#!/usr/bin/env python3
"""
PCCooler LCD Manager - Background job queue.

GUI writes requests.
Worker processes them.

No USB communication in this module.
"""

import json
import os
import time
import uuid
from pathlib import Path


BASE = Path.home() / ".local/state/pccooler-lcd"
BACKGROUNDS = BASE / "backgrounds"
JOBS = BASE / "jobs"
FAILED = BASE / "failed"
STATE = BASE / "background-state.json"


def ensure_directories():
    BACKGROUNDS.mkdir(parents=True, exist_ok=True)
    JOBS.mkdir(parents=True, exist_ok=True)
    FAILED.mkdir(parents=True, exist_ok=True)


def create_background_job(image_data, extension=".png"):
    if not isinstance(image_data, bytes):
        raise TypeError("image_data must be bytes")

    if not image_data:
        raise ValueError("Empty background")

    if extension not in (".png", ".mp4"):
        raise ValueError("Unsupported background format")

    ensure_directories()

    job_id = uuid.uuid4().hex

    background_path = BACKGROUNDS / f"{job_id}{extension}"

    with open(background_path, "xb") as file:
        file.write(image_data)
        file.flush()
        os.fsync(file.fileno())

    job = {
        "id": job_id,
        "type": "set_background",
        "file": background_path.name,
        "created": time.time(),
    }

    temporary = JOBS / f"{job_id}.json.tmp"
    final = JOBS / f"{job_id}.json"

    temporary.write_text(
        json.dumps(job, ensure_ascii=False, indent=2)
    )

    os.replace(temporary, final)

    return job_id


def pending_jobs():
    ensure_directories()

    for path in sorted(JOBS.glob("*.json")):
        try:
            job = json.loads(path.read_text())
            yield path, job
        except (OSError, json.JSONDecodeError):
            continue


def complete_job(path, job):
    ensure_directories()

    state = {
        "current_background": job["file"],
        "updated": time.time(),
    }

    temporary = STATE.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(state, ensure_ascii=False, indent=2)
    )

    os.replace(temporary, STATE)
    path.unlink()


def fail_job(path, job, error):
    """
    Move failed job out of the pending queue.
    """

    ensure_directories()

    job["status"] = "failed"
    job["error"] = str(error)
    job["failed_at"] = time.time()

    destination = FAILED / path.name
    temporary = FAILED / (path.name + ".tmp")

    temporary.write_text(
        json.dumps(job, ensure_ascii=False, indent=2)
    )

    os.replace(temporary, destination)
    path.unlink()


def get_current_background():
    if not STATE.is_file():
        return None

    try:
        state = json.loads(STATE.read_text())
        filename = Path(state["current_background"]).name
        path = BACKGROUNDS / filename
        return path if path.is_file() else None
    except (OSError, ValueError, KeyError):
        return None
