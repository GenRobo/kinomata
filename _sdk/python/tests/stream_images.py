import numpy as np
import cv2
import threading
from os import _exit

from pynomata.client import KinoClient
from pynomata.common_types import *
from pynomata.sensor_utils import to_np_dtype
from pynomata.color_utils import convert_color

# --- Grid Configuration ---
COUNT = 1000
QUAD_H = 32 
QUAD_W = 64 
FONT_SCALE = 0.5 # float
FONT_THICKNESS = 1

data_lock = threading.Lock()

def listener(sample, row, col, metadata, out_data):
  d_type = to_np_dtype(metadata.data_type)
  frame = np.frombuffer(sample.payload.to_bytes(), dtype=d_type).reshape(
    metadata.height, metadata.width, metadata.channel_count)

  with data_lock:
    out_data[(row, col)] = convert_color(frame, metadata.color_space, ColorSpace.BGR)

def update_combined_image(out_image, data):
  # Iterate through available frames and drop them into the correct coordinates
  for (r, c), frame in data.items():
    y1 = r * QUAD_H
    y2 = (r + 1) * QUAD_H
    x1 = c * QUAD_W
    x2 = (c + 1) * QUAD_W
    
    # Numpy slicing injects the quad into the larger canvas
    out_image[y1:y2, x1:x2] = frame

def main():
  client = KinoClient()

  # Request stream
  metadata = client.sim_start_stream(QUAD_W, QUAD_H, COUNT, FONT_SCALE, FONT_THICKNESS)
  if not metadata:
    print("Error while requesting for stream")
    client.stop()
    return

  # try to uniformly split COUNT into rows and cols 
  from math import sqrt, ceil
  cols = ceil(sqrt(COUNT))
  rows = ceil(COUNT / cols)

  img_raw_data = {}

  # Subscribe topics and assign them to a (row, column) position
  # (0, 0) is top-left.
  for i in range(COUNT):
    r = i // cols # r0 -> 0 * cols, r1 -> 1 * cols, r2 -> 2 * cols...
    c = i % cols # wrap
    topic = f"sim/stream/{i+1}"
    client.sub(topic,
      lambda s, r=r, c=c, meta=metadata, out_data=img_raw_data:
        listener(s, r, c, meta, out_data),
    )

  print("Subscribed to stream topics.")
  print(f"Now showing {cols}x{rows} live grid with active {COUNT} {QUAD_W}x{QUAD_H} streams...")
  print("Press 'q' in the video window to exit.")

  try:
    # Initialize the blank canvas
    full_image = np.zeros((rows * QUAD_H, cols * QUAD_W, 3), dtype=np.uint8)
    while True:
      with data_lock:
        update_combined_image(full_image, img_raw_data)
        # Copy the frame so we can release the lock before rendering the UI
        display_frame = full_image.copy()

      # Display the combined grid
      cv2.imshow("Live Image Grid", display_frame)

      # Wait ~33ms (approx 30 FPS). Also captures keyboard input for the active window.
      if cv2.waitKey(33) & 0xFF == ord('q'):
        print("\n'q' pressed, exiting...")
        break

  except KeyboardInterrupt:
      print("\nKeyboard interrupt, exiting...")
  
  finally:
    client.sim_end_stream()

    # Clean up gracefully
    cv2.destroyAllWindows()
    cv2.waitKey(1) # CRITICAL: Gives OpenCV time to actually close the windows on Windows

    client.stop()
    
    print("Clean up done, and destroyed windows. Now exiting...")

    # Force the OS to terminate the process, bypassing Python's hanging thread shutdown
    _exit(0)

if __name__ == "__main__":
  main()
