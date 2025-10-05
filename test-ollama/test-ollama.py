import os
from ollama import Client
import dotenv
dotenv.load_dotenv()

client = Client(
    host="https://ollama.com",
    headers={'Authorization': 'Bearer ' + os.environ.get('OLLAMA_API_KEY')}
)

messages = [
  {
    'role': 'user',
    'content': 'Why is the sky blue?',
  },
]

print("Testing with correct endpoint and model...")
try:
    for part in client.chat('gpt-oss:120b', messages=messages, stream=True):
        print(part['message']['content'], end='', flush=True)
    print("\n\nSuccess! Now let's update the LangChain code.")
except Exception as e:
    print(f"Error: {e}")