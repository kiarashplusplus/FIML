import redis
import sys

try:
    r = redis.Redis(host="localhost", port=6379, socket_connect_timeout=2)
    print(f"Pinging Redis at localhost:6379...")
    response = r.ping()
    print(f"Response: {response}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
