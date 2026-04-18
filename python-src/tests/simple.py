import zenoh
from time import sleep 

def listener(sample):
    # Option A: Convert to bytes first, then decode
    payload_bytes = bytes(sample.payload)
    print(f">> Received {sample.kind} ('{sample.key_expr}'): '{payload_bytes.decode()}'")

    # Option B: Or use the built-in string conversion if available
    # print(f">> Received: {sample.payload.to_string()}")

if __name__ == "__main__":
  conf = zenoh.Config()
  conf.insert_json5("transport/shared_memory/enabled", "true")

  session = zenoh.open(conf)

  # Subscribe to the same path used in your C++ code
  sub = session.declare_subscriber("demo/example/simple", listener)
  
  print("Waiting for data... Press Ctrl+C to stop.")
  try:
    while True:
        sleep(1)
  except KeyboardInterrupt:
    print("\nClosing session...")
    session.close()

