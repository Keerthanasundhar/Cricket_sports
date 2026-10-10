import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print("ERROR: GROQ_API_KEY was not loaded.")
else:
    try:
        client = Groq(api_key=api_key)

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": "Say hello in one sentence."
                }
            ],
            max_tokens=100
        )

        print("SUCCESS!")
        print(response.choices[0].message.content)

    except Exception as e:
        print("API ERROR:", type(e).__name__)
        print("DETAILS:", str(e))