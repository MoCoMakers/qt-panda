#!/usr/bin/env python3

import os
import re
import shutil
from PIL import Image

PREFIX = "image_adc_"
EXT = ".png"
PROCESSED_DIR = "processed"


def extract_timestamp(filename):
    match = re.search(r'image_adc_(\d+)\.png', filename)
    if match:
        return int(match.group(1))
    return None


def main():
    # Get matching PNG files
    png_files = [f for f in os.listdir(".") if f.startswith(PREFIX) and f.endswith(EXT)]

    if not png_files:
        print("No matching PNG files found.")
        return

    # Sort PNGs by timestamp
    png_files.sort(key=extract_timestamp)

    # Name GIF after first timestamp
    first_ts = extract_timestamp(png_files[0])
    gif_name = f"image_adc_{first_ts}.gif"

    print(f"Creating GIF: {gif_name}")

    # Load images
    images = []
    for file in png_files:
        img = Image.open(file)
        images.append(img)

    # Save GIF
    images[0].save(
        gif_name,
        save_all=True,
        append_images=images[1:],
        duration=200,
        loop=0
    )

    print("GIF created.")

    # Ensure processed directory exists
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    # Move PNG files
    for file in png_files:
        shutil.move(file, os.path.join(PROCESSED_DIR, file))

    print(f"Moved {len(png_files)} PNG files to '{PROCESSED_DIR}'")

    # Move TXT files
    txt_files = [f for f in os.listdir(".") if f.endswith(".txt")]

    for file in txt_files:
        shutil.move(file, os.path.join(PROCESSED_DIR, file))

    print(f"Moved {len(txt_files)} TXT files to '{PROCESSED_DIR}'")


if __name__ == "__main__":
    main()
