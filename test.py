from app.core.config import settings
import os
os.environ["AGENTSPHERE_ENV"] = "development"

from app.llm.qwen_client import QwenClient

client = QwenClient()

print("Generating response...")
response = client.generate("Hello, how are you?")
print("Response:", response)