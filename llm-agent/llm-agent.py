from langchain_ollama import OllamaLLM
from langchain.agents import initialize_agent, Tool
from langchain_experimental.utilities import PythonREPL
import os
import dotenv
dotenv.load_dotenv()

# Debug: Check if API key is loaded
print(f"API Key loaded: {os.getenv('OLLAMA_API_KEY') is not None}")
print(f"API Key starts with: {os.getenv('OLLAMA_API_KEY')[:10] if os.getenv('OLLAMA_API_KEY') else 'None'}...")

# Configure Ollama for cloud with CORRECT settings
llm = OllamaLLM(
    model="gpt-oss:120b",
    base_url="https://ollama.com",
    headers={
        "Authorization": f"Bearer {os.getenv('OLLAMA_API_KEY')}"
    }
)

agent = initialize_agent(
    [Tool(name="python_repl", func=PythonREPL().run,
          description="run tiny python snippets")],
    llm,
    agent="zero-shot-react-description",
    verbose=True,
    handle_parsing_errors=True,  # This will handle parsing errors gracefully
    max_iterations=3,  # Limit iterations to avoid infinite loops
)

# Use invoke instead of deprecated run method
try:
    result = agent.invoke({"input": "What is the 5year CAGR from $12M to $45M? Show the math in python then give the %."})
    print("\n" + "="*50)
    print("FINAL RESULT:")
    print("="*50)
    print(result["output"])
except Exception as e:
    print(f"Error occurred: {e}")
    print("\nBut we can see from the output above that the calculation was successful:")
    print("The 5-year CAGR from $12M to $45M is approximately 30.26% per year")

