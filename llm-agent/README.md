# LLM Agent v2 (`llm-agent.py`)

## Purpose
Enhanced AI agent using modern LangChain architecture that can perform mathematical calculations and execute Python code using Ollama Cloud's `gpt-oss:120b` model through the ReAct pattern.

## What it does
1. **Connects to Ollama Cloud** using API key authentication with Bearer token
2. **Creates a modern ReAct agent** using `create_react_agent` and `AgentExecutor`
3. **Uses community-tested prompts** from LangChain Hub for optimal performance
4. **Provides Python execution capability** through PythonREPL tool
5. **Handles complex calculations** by writing and executing Python code step-by-step
6. **Returns formatted results** with robust error handling and graceful recovery

## Key Components

### LLM Configuration
- **Model**: `gpt-oss:120b` (Ollama Cloud's 120B parameter large language model)
- **Authentication**: Bearer token via headers
- **Endpoint**: `https://ollama.com` (corrected from previous versions)

### Agent Setup (v2 Architecture)
- **Type**: ReAct (Reasoning + Acting) using modern LangChain approach
- **Creation Method**: `create_react_agent()` + `AgentExecutor()` (replaces deprecated `initialize_agent`)
- **Prompt Source**: LangChain Hub community prompt (`hwchase17/react`)
- **Tools**: Python REPL for code execution
- **Error Handling**: Graceful parsing error recovery with `handle_parsing_errors=True`
- **Iteration Limit**: Maximum 5 iterations to prevent infinite loops
- **Verbose Mode**: Detailed step-by-step reasoning display

### ReAct Pattern Flow
```
Question: [User's input question]
Thought: [Agent reasoning about approach]
Action: [Tool selection - python_repl]
Action Input: [Python code to execute]
Observation: [Execution results]
... (repeat Thought/Action/Observation cycle as needed)
Thought: I now know the final answer
Final Answer: [Comprehensive response with results]
```

### Example Usage
```python
# The agent follows structured ReAct pattern:
result = agent_executor.invoke({
    "input": "What is the 5year CAGR from $12M to $45M? Show the math in python then give the %."
})

# Process:
# 1. Analyzes CAGR formula requirement
# 2. Executes Python calculation: (45M/12M)^(1/5) - 1
# 3. Shows step-by-step math
# 4. Provides final answer: 30.26% CAGR
```

## New Features in v2
- ✅ **Modern Architecture**: Uses `create_react_agent` instead of deprecated methods
- ✅ **LangChain Hub Integration**: Community-tested ReAct prompts
- ✅ **Enhanced Error Recovery**: Handles LLM parsing errors gracefully
- ✅ **Iteration Control**: Prevents runaway agent loops
- ✅ **Better Debugging**: Comprehensive error messages and fallback responses
- ✅ **Robust Execution**: `AgentExecutor` with advanced error handling

## Features
- ✅ Mathematical calculations with step-by-step reasoning
- ✅ Python code execution in secure REPL environment
- ✅ Structured ReAct reasoning pattern
- ✅ Graceful error handling and recovery
- ✅ Verbose output for debugging and transparency
- ✅ Cloud-based LLM inference with 120B parameters
- ✅ Community-tested prompt templates
- ✅ Modern LangChain agent architecture

## Dependencies
- `langchain-ollama`: Ollama integration for LLM
- `langchain`: Core agent framework and utilities
- `langchain-experimental`: Python REPL tool for code execution
- `langchainhub`: Access to community prompt templates
- `python-dotenv`: Environment variable loading
- `ollama`: Official Ollama client library

## Code Structure
```python
# Modern v2 approach:
llm = OllamaLLM(model="gpt-oss:120b", base_url="https://ollama.com", headers={...})
tools = [Tool(name="python_repl", func=PythonREPL().run, description="...")]
prompt = hub.pull("hwchase17/react")  # Community-tested prompt
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, 
                              handle_parsing_errors=True, max_iterations=5)
```

## Error Handling
- **Parsing Errors**: Automatic recovery when LLM output doesn't match expected format
- **Iteration Limits**: Prevents infinite reasoning loops
- **API Failures**: Graceful degradation with informative error messages
- **Tool Failures**: Continues execution even if Python code has errors
- **Fallback Responses**: Provides manual calculation results when agent fails