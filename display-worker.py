import sys
import time
import signal
import tempfile
from pathlib import Path

from PIL import Image

from render import QApplication, render

import importlib.util

spec = importlib.util.spec_from_file_location(
    "test_display",
    Path(__file__).parent / "test-display.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
send_image = module.send_image

INTERVAL = 2
running = True

def stop(signum, frame):
    global running
    running = False

signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)

app = QApplication(sys.argv)

print("PCCooler LCD Worker запущен", flush=True)

while running:
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

        if len(png) > 5264:
            print("PNG слишком большой:", len(png))
        else:
            send_image(png)

    for _ in range(INTERVAL * 10):
        if not running:
            break
        time.sleep(0.1)

print("PCCooler LCD Worker остановлен")
