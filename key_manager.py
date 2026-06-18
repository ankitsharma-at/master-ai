import os
import time
from dotenv import load_dotenv

load_dotenv()


class APIKeyManager:
    def __init__(self):
        self.keys = [
            os.getenv("GEMINI_KEY_1"),
            os.getenv("GEMINI_KEY_2"),
            os.getenv("GEMINI_KEY_3"),
            os.getenv("GEMINI_KEY_4"),
        ]

        self.keys = [k for k in self.keys if k]
        self.blocked = {}

    def get_key(self):
        now = time.time()

        for key in self.keys:

            if key not in self.blocked:
                return key

            if self.blocked[key] < now:
                del self.blocked[key]
                return key

        raise Exception("All Gemini keys are rate limited")

    def block_key(self, key, seconds=60):
        self.blocked[key] = time.time() + seconds

        print(
            f"[KEY_MANAGER] Blocked key "
            f"{key[:10]}... "
            f"for {seconds}s"
        )
key_manager = APIKeyManager()