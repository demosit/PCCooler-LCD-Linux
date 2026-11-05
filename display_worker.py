import sys
import time
import signal
import tempfile
from pathlib import Path

from PIL import Image

from renderer import QApplication, render
from usb_display import send_image, wake_display, close_display
from background_worker import process_background_jobs

INTERVAL = 2
running = True


def stop(signum, frame):
    global running
    running = False


signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)

app = QApplication(sys.argv)

print("PCCooler LCD Worker запущен", flush=True)

try:
    try:
        wake_display()
    except Exception as exc:
        print(f"LCD wake failed: {exc}", flush=True)

    while running:
        try:
            process_background_jobs()
        except Exception as exc:
            print(
                f"Background job failed: {exc}",
                flush=True,
            )

        with tempfile.TemporaryDirectory() as tmp:
            png_path = Path(tmp) / "frame.png"

            render(png_path)

            image = Image.open(png_path).convert("RGBA")
            image = image.quantize(
                colors=32,
                method=Image.Quantize.FASTOCTREE
            )

            output = Path(tmp) / "optimized.png"
            image.save(output, "PNG", optimize=True)

            png = output.read_bytes()
            send_image(png)

        for _ in range(INTERVAL * 10):
            if not running:
                break
            time.sleep(0.1)

finally:
    close_display()
    print("PCCooler LCD Worker остановлен", flush=True)
