# LLM Agent (`llm-agent.py`)

## Purpose
Main AI agent that can perform mathematical calculations and execute Python code using Ollama Cloud's `gpt-oss:120b` model through LangChain.

## What it does
1. **Connects to Ollama Cloud** using API key authentication
2. **Creates a ReAct agent** that can reason and take actions
3. **Provides Python execution capability** through PythonREPL tool
4. **Handles complex calculations** by writing and executing Python code
5. **Returns formatted results** with error handling

## Key Components

### LLM Configuration
- **Model**: `gpt-oss:120b` (Ollama Cloud's large language model)
- **Authentication**: Bearer token via headers
- **Endpoint**: `https://ollama.com`

### Agent Setup
- **Type**: Zero-shot ReAct (Reasoning + Acting)
- **Tools**: Python REPL for code execution
- **Error Handling**: Graceful parsing error recovery
- **Iteration Limit**: Maximum 3 iterations to prevent loops

### Example Usage
```python
# The agent can solve problems like:
result = agent.invoke({
    "input": "What is the 5year CAGR from $12M to $45M? Show the math in python then give the %."
})

# Output: Shows calculation steps and result (30.26% CAGR)
```

## Features
- ✅ Mathematical calculations
- ✅ Python code execution
- ✅ Step-by-step reasoning
- ✅ Error handling
- ✅ Verbose output for debugging
- ✅ Cloud-based LLM inference

## Dependencies
- `langchain-ollama`: Ollama integration
- `langchain`: Agent framework
- `langchain-experimental`: Python REPL tool
- `python-dotenv`: Environment variable loading