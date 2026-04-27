import zenoh
import numpy as np
import cv2
import threading
from struct import pack
from os import _exit

# --- Grid Configuration ---
COUNT = 2000
QUAD_H = 16 
QUAD_W = 32 
FONT_SCALE = 0.25 # percentage
FONT_THICKNESS = 1

data_lock = threading.Lock()

def listener(sample, row, col, out_data):
  raw_data = sample.payload.to_bytes()
  # Assuming the incoming payload is BGR.
  expected_size = QUAD_H * QUAD_W * 3
  if len(raw_data) != expected_size:
    return
  frame = np.frombuffer(raw_data, dtype=np.uint8).reshape((QUAD_H, QUAD_W, 3))

  with data_lock:
    out_data[(row, col)] = frame

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
  conf = zenoh.Config()
  conf.insert_json5("transport/shared_memory/enabled", "true")

  print("Opening Zenoh session...")
  session = zenoh.open(conf)

  # Request stream
  # passing params as a packed struct.
  # H is unsigned short (uint16), f is float (float32)
  # '<' specifies little-endian byte order (required by the server)
  stream_config = pack('<HHHfH', QUAD_W, QUAD_H, COUNT, FONT_SCALE, FONT_THICKNESS)
  # Use 'get' to send the payload to the Queryable
  # We pass the stream_config as the payload of the query
  replies = session.get("sim/stream", payload=stream_config)
  # Wait for Response
  for reply in replies:
    if reply.ok is not None:
      print("Success.")
    else:
      print("Error connecting.")
      return

  # try to uniformly split COUNT into rows and cols 
  from math import sqrt, ceil
  cols = ceil(sqrt(COUNT))
  rows = ceil(COUNT / cols)

  img_raw_data = {}

  # Subscribe topics and assign them to a (row, column) position
  # (0, 0) is top-left.
  subs = []
  for i in range(COUNT):
    r = i // cols # r0 -> 0 * cols, r1 -> 1 * cols, r2 -> 2 * cols...
    c = i % cols # wrap
    topic = f"sim/stream/{i+1}"
    subs.append(
      session.declare_subscriber(
        topic,
        lambda s, r=r, c=c, data=img_raw_data: listener(s, r, c, data)
      )
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
      cv2.imshow("Zenoh Live Grid", display_frame)

      # Wait ~33ms (approx 30 FPS). Also captures keyboard input for the active window.
      if cv2.waitKey(33) & 0xFF == ord('q'):
        print("\n'q' pressed, exiting...")
        break

  except KeyboardInterrupt:
      print("\nKeyboard interrupt, exiting...")
  
  finally:
    session.get("sim/stream/end")
    # Clean up gracefully
    cv2.destroyAllWindows()
    cv2.waitKey(1) # CRITICAL: Gives OpenCV time to actually close the windows on Windows

    for sub in subs:
      sub.undeclare()
    session.close()
    
    print("Unsubscribed, closed session, and destroyed windows.")

    # Force the OS to terminate the process, bypassing Python's hanging thread shutdown
    _exit(0)

if __name__ == "__main__":
  main()
