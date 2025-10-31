import os
import time
import json
import redis


def main():
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    r = redis.Redis.from_url(redis_url, decode_responses=True)
    last = None
    backoff = 1
    while True:
        # Mock metrics update
        payload = {
            "subscribers": 123456,
            "top3": [
                {"id": 1, "title": "Sample Video 1", "views": 1200, "likes": 120, "ctr": 4.2},
                {"id": 2, "title": "Sample Video 2", "views": 2400, "likes": 240, "ctr": 5.1},
                {"id": 3, "title": "Sample Video 3", "views": 3600, "likes": 360, "ctr": 6.0},
            ],
            "last_updated": int(time.time()),
        }
        data = json.dumps(payload)
        if data != last:
            r.publish("metrics_updates", data)
            last = data
            backoff = 1
        else:
            backoff = min(backoff * 2, 30)
        time.sleep(3 if backoff == 1 else backoff)


if __name__ == "__main__":
    main()


