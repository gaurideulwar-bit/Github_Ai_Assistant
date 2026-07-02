"""
Simple script to talk to Google's Gemini API directly using the `requests` library.
No SDK needed — just plain HTTP request/response.

Setup:
    pip install requests
    Set your API key below or as an environment variable GEMINI_API_KEY.

Get a free API key from: https://aistudio.google.com/apikey
"""

import os
import requests

# ---- CONFIG ----
API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6IH_ItHEEBJAI7ZhsknPUWrqqJ_xC4UnarZRlmy7AUlkw")

# Free-tier friendly models (as of mid-2026). Change this if needed.
MODEL = "gemini-2.5-flash"   # other options: "gemini-2.5-flash-lite", "gemini-2.0-flash"

BASE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"


def ask_gemini(prompt: str, api_key: str = API_KEY, model: str = MODEL) -> str:
    """Send a prompt to Gemini and return the text response."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload)

    # Raise an error if the request failed (bad key, rate limit, etc.)
    response.raise_for_status()

    data = response.json()

    # Extract the text from the response structure
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return f"Unexpected response format: {data}"


def chat_loop():
    """Simple interactive loop in the terminal."""
    print(f"Gemini chat ({MODEL}) — type 'exit' to quit.\n")

    if API_KEY == "PASTE_YOUR_API_KEY_HERE":
        print("⚠️  Please set your API key (edit the script or set GEMINI_API_KEY env var).\n")
        return

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue

        try:
            reply = ask_gemini(user_input)
            print(f"Gemini: {reply}\n")
        except requests.exceptions.HTTPError as e:
            print(f"Error: {e}\nResponse body: {e.response.text}\n")


if __name__ == "__main__":
    # Example single-shot call:
    # print(ask_gemini("What is the capital of France?"))

    chat_loop()