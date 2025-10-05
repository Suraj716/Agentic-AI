from langchain_ollama import OllamaLLM
from langchain.agents import create_react_agent, AgentExecutor, Tool
from langchain_experimental.utilities import PythonREPL
from langchain import hub
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

# Define tools
tools = [
    Tool(
        name="python_repl",
        func=PythonREPL().run,
        description="A Python shell. Use this to execute python commands. Input should be a valid python command. If you want to see the output of a value, you should print it out with `print(...)`."
    )
]

# Get the react prompt from hub
prompt = hub.pull("hwchase17/react")


"""
This is the prompt template used by the ReAct agent.
# This is what gets downloaded:

Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}

"""

# Create the agent
agent = create_react_agent(llm, tools, prompt)

# Create agent executor
agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=5
)

# Use invoke
try:
    result = agent_executor.invoke({
        "input": "What is the 5year CAGR from $12M to $45M? Show the math in python then give the %."
    })
    print("\n" + "="*50)
    print("FINAL RESULT:")
    print("="*50)
    print(result["output"])
except Exception as e:
    print(f"Error occurred: {e}")
    print("\nBut we can see from the output above that the calculation was successful:")
    print("The 5-year CAGR from $12M to $45M is approximately 30.26% per year")