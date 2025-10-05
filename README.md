# AI Agent with Ollama Cloud

This repository contains a Python-based AI agent that uses Ollama Cloud's `gpt-oss:120b` model to perform calculations and execute Python code through LangChain.

## Features

- **LangChain Integration**: Uses LangChain's agent framework to create a ReAct (Reasoning + Acting) agent
- **Ollama Cloud**: Connects to Ollama Cloud's powerful `gpt-oss:120b` model
- **Python Code Execution**: Agent can execute Python code to perform calculations
- **Error Handling**: Includes parsing error handling and iteration limits

## Files

- `llm-agent.py` - Main AI agent that can perform calculations and execute Python code
- `test-ollama.py` - Test script to verify Ollama Cloud connection and authentication
- `requirements.txt` - Python dependencies
- `.env` - Environment variables (API key)

## Setup

1. **Install dependencies:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   Create a `.env` file with your Ollama Cloud API key:
   ```
   OLLAMA_API_KEY=your_ollama_cloud_api_key_here
   ```

3. **Test connection:**
   ```bash
   python test-ollama.py
   ```

4. **Run the agent:**
   ```bash
   python llm-agent.py
   ```

## Usage Example

The agent can solve mathematical problems by executing Python code:

```
Input: "What is the 5year CAGR from $12M to $45M? Show the math in python then give the %."
Output: Calculates and shows that the CAGR is approximately 30.26% per year
```

## Requirements

- Python 3.8+
- Ollama Cloud API key
- Internet connection

## Architecture

The agent uses:
- **LangChain**: For agent orchestration and tool management
- **Ollama Cloud**: For large language model inference
- **Python REPL**: As a tool for code execution
- **ReAct Pattern**: For reasoning and action cycles