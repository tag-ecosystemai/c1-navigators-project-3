from openai import OpenAI, RateLimitError
import os

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

try:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello, test message"}]
    )
    print(resp.choices[0].message.content)
except RateLimitError as e:
    print("✅ Connection successful, but no credits left:", e)
