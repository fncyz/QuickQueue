import os
from google import genai

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def ask_gemini(message):
    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=message
        )

        return response.text

    except Exception as e:
        print(f"Gemini Error: {e}")
        return None