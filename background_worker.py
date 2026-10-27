#!/usr/bin/env python3
"""
PCCooler LCD Manager - Background job processor.

Must run inside the single USB-owning Worker.
"""

from pathlib import Path

from background_jobs import (
    BACKGROUNDS,
    pending_jobs,
    complete_job,
    fail_job,
)

from usb_display import send_background


class BackgroundJobError(Exception):
    pass


def process_background_jobs():
    """
    Process at most one background job per call.

    Returns True if a job was processed.
    """

    for job_path, job in pending_jobs():
        if job.get("type") != "set_background":
            raise BackgroundJobError(
                f"Unknown job type: {job.get('type')}"
            )

        filename = job.get("file")

        if not isinstance(filename, str):
            raise BackgroundJobError("Invalid filename")

        if Path(filename).name != filename:
            raise BackgroundJobError("Unsafe filename")

        path = BACKGROUNDS / filename

        if not path.is_file():
            raise BackgroundJobError(
                f"Background not found: {path}"
            )

        if path.suffix.lower() not in (".png", ".mp4"):
            raise BackgroundJobError(
                f"Unsupported format: {path.suffix}"
            )

        print(
            f"Uploading background: {path.name}",
            flush=True,
        )

        try:
            send_background(path)
        except Exception as exc:
            fail_job(job_path, job, exc)

            print(
                f"Background upload failed: {exc}",
                flush=True,
            )

            return False

        complete_job(job_path, job)

        print(
            f"Background uploaded: {path.name}",
            flush=True,
        )

        return True

    return False
