import google.generativeai as genai

from core.config import get_settings
from key_manager import key_manager


class GeminiService:

    def __init__(self):
        self.settings = get_settings()

    def generate(self, prompt):

        max_attempts = len(key_manager.keys)
        print("Loaded keys:", len(key_manager.keys))
        last_error = None

        for _ in range(max_attempts):

            api_key = key_manager.get_key()

            try:

                genai.configure(api_key=api_key)

                model = genai.GenerativeModel(
                    self.settings.llm_model
                )

                response = model.generate_content(prompt)

                return response

            except Exception as e:

                error_text = str(e)

                if (
                    "429" in error_text
                    or "RESOURCE_EXHAUSTED" in error_text
                    or "rate limit" in error_text.lower()
                    or "403" in error_text
                    or "denied access" in error_text.lower()
                ):
                

                    key_manager.block_key(
                        api_key,
                        seconds=300
                    )

                    last_error = e
                    continue

                raise

        raise Exception(
            f"All Gemini keys exhausted. Last error: {last_error}"
        )