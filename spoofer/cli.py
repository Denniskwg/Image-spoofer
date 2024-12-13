#!/usr/bin/python3
import numpy as np
import hashlib
from PIL import Image
import threading
import io
import struct
import zlib
import asyncio
from pebble import ThreadPool
from functools import partial
import click


def modify_lsb_parallel(input_file, output_image, prefix, max_attempts, num_workers=4):
    """
    Modify the LSBs of pixel values in parallel until the hash has the desired prefix.
    Args:
        input_file: path to file to alter
        prefix (str): The desired hash prefix (e.g., '24').
        max_attempts (int): Maximum number of iterations.
        num_workers (int): Number of parallel workers.

    Returns:
        numpy.ndarray: Modified image data with the desired hash prefix.
    """
    modified_data = None
    with open(input_file, "rb") as f:
        png_data = f.read()
        # Validate PNG signature
        signature = png_data[:8]
        if signature != b'\x89PNG\r\n\x1a\n':
            raise ValueError("Input file is not a valid PNG.")
        # Parse chunks
        chunks = []
        idx = 8
        while idx < len(png_data):
            length = struct.unpack(">I", png_data[idx:idx+4])[0]
            chunk_type = png_data[idx+4:idx+8].decode("ascii")
            chunk_data = bytearray(png_data[idx+8:idx+8+length])
            crc = png_data[idx+8+length:idx+12+length]
            chunks.append((chunk_type, chunk_data, crc))
            idx += 12 + length

    # Set up the number of iterations per worker
    attempts_per_worker = max_attempts // num_workers
    if max_attempts % num_workers != 0:
        attempts_per_worker += 1

    print("WORKING....")
    with ThreadPool(max_workers=num_workers) as executor:
        futures = [executor.schedule(partial(modify_png_for_hash, chunks, output_image, signature, prefix, attempts_per_worker)) for _ in range(num_workers)]
        try:
            for future in futures:
                if future.done():
                    continue
                try:
                    modified_data = future.result(timeout=0)
                    if modified_data is not None:
                        executor.stop()
                        #return modified_data
                except TimeoutError:
                    continue
                except Exception as e:
                    continue
                    #print(f"Worker failed with exception: {e}")
        finally:
            executor.stop()

def convert_to_png(input_file):
    """
    Convert an image to PNG format.

    Args:
        input_file (str): Path to the input image file.
        output_file (str): Path to save the PNG image.
    """
    try:
        # Open the input image
        img = Image.open(input_file)
        # Convert and save as PNG
        img.save("output.png", format="PNG")
        #print("Image successfully converted to PNG and saved")
    except Exception as e:
        print(f"An error occurred: {e}")



def modify_png_for_hash(data, output_image, signature, desired_prefix, max_attempts):
    """
    Modify PNG chunks to achieve a file hash with a specific prefix.

    Args:
        data: image file data including headers, pixel data.
        signature: png file signature
        desired_prefix (str): Desired hash prefix (e.g., "24").
        max_attempts (int): Maximum number of modification attempts.
        
        Returns:
            Image: Modified image with hash that starts with prefix.
    """
    modified_chunks = data.copy()
    for attempt in range(max_attempts):
        modified = False
        for chunk_type, chunk_data, crc in data:
            if chunk_type == "IDAT":
                for i in range(len(chunk_data)):
                    chunk_data[i] ^= 1  # Flip the least significant bit
                    modified = True
                    break
                # Recalculate CRC
                new_crc = zlib.crc32(chunk_type.encode("ascii") + chunk_data).to_bytes(4, "big")
                modified_chunks.append((chunk_type, chunk_data, new_crc))
            else:
                modified_chunks.append((chunk_type, chunk_data, crc))

        if not modified:
            raise ValueError("No modifiable chunks found in the PNG file.")
        # Reassemble the PNG
        rebuilt_png = signature
        for chunk_type, chunk_data, crc in modified_chunks:
            length = len(chunk_data).to_bytes(4, "big")
            rebuilt_png += length + chunk_type.encode("ascii") + chunk_data + crc
        # Calculate hash
        current_hash = hashlib.sha256(rebuilt_png).hexdigest()
        if current_hash.startswith(desired_prefix):
            #print(f"Hash achieved: {current_hash}")
            with open(output_image, "wb") as f:
                f.write(rebuilt_png)
            return rebuilt_png
    return None

@click.command()
@click.argument("string", required=True)
@click.argument("original_image", required=True)
@click.argument("output_image", required=True)
def cli(string: str, original_image: str, output_image= str):
    try:
        convert_to_png(original_image)
        desired_prefix = string[2:]
        print(desired_prefix)
        modify_lsb_parallel("output.png", output_image, desired_prefix, max_attempts=400, num_workers=8)
        with open(output_image, "rb") as f:
            data = f.read()
            current_hash = hashlib.sha256(data).hexdigest()
            if current_hash.startswith(desired_prefix):
                print(f"Hash achieved: {current_hash}")
            else:
                raise ValueError("Failed to achieve target hash prefix within the maximum attempts.")
        print("Successfully modified PNG file.")
    except ValueError as e:
        print(e)
    except FileNotFoundError as e:
        print("Failed to achieve target hash prefix within the maximum attempts.")

if __name__ == "__main__":
    cli()
