from time import sleep
import zenoh
import numpy as np
import cv2
from struct import pack

WIDTH = 640
HEIGHT = 480
FONT_SCALE = 500 # percentage
FONT_THICKNESS = 3

def listener(sample):
  image_format = "P6" # PPM
  data_type = np.uint8
  channel_count = 3 # R,G,B
  max_color_value = 255
  conversion_code = cv2.COLOR_BGR2RGB # OpenCV (input) is BGR, we flip it to RGB for PPM

  # 1. Get the raw buffer
  # In Zenoh with SHM enabled, this is a view into shared memory
  raw_data = sample.payload.to_bytes()

  # 2. Map buffer to NumPy array (Zero-Copy)
  # Shape is (Height, Width, Channels)
  frame = np.frombuffer(raw_data, dtype=data_type).reshape(HEIGHT, WIDTH, channel_count)

  # 3. Save
  img_name = "output/basic_img.ppm"
  rgb_frame = cv2.cvtColor(frame, conversion_code) # color space conversion
  header = f"{image_format}\n{WIDTH} {HEIGHT}\n{max_color_value}\n"
  with open(img_name, "wb") as f:
    f.write(header.encode())
    f.write(rgb_frame.tobytes())

  print(f"Frame captured and saved to {img_name}")

def main():
  conf = zenoh.Config()
  conf.insert_json5("transport/shared_memory/enabled", "true")

  print("Opening Zenoh session...")
  session = zenoh.open(conf)

  # Request stream
  # passing params as an array of five unsigned shorts (uint16) 
  # '<' specifies little-endian byte order (required by the server)
  stream_config = pack('<HHHHH', WIDTH, HEIGHT, 1, FONT_SCALE, FONT_THICKNESS)
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

  # Subscribe to the same path used in your C++ code
  # Will create a thread separate from main 
  sub = session.declare_subscriber("sim/stream/1", listener)
  print("Subscribed to stream.")

  try:
    sleep(30.0)
  except KeyboardInterrupt:
    print("Keyboard interrupt, exiting...")

  sub.undeclare() # will kill the subscriber thread
  session.close()
  print("Unsubscribed to stream, and closed session")

if __name__ == "__main__":
  main()

