# Test Ollama (`test-ollama.py`)

## Purpose
Simple test script to verify Ollama Cloud connection, authentication, and model access before using the main agent.

## What it does
1. **Tests API connectivity** to Ollama Cloud
2. **Verifies authentication** using Bearer token
3. **Confirms model access** to `gpt-oss:120b`
4. **Demonstrates streaming responses** from the model
5. **Validates environment setup** before running the main agent

## Key Components

### Connection Test
- **Endpoint**: `https://ollama.com`
- **Authentication**: Bearer token from environment variable
- **Model**: `gpt-oss:120b`

### Test Flow
1. Load API key from `.env` file
2. Create Ollama client with authentication headers
3. Send simple test message: "Why is the sky blue?"
4. Stream response to verify everything works
5. Display success/error messages

### Example Output
```
Testing with correct endpoint and model...
The short answer is: **Rayleigh scattering** makes the sky appear blue.
[...detailed explanation...]
Success! Now let's update the LangChain code.
```

## Use Cases
- ✅ **Pre-flight check** before running main agent
- ✅ **Debug authentication** issues
- ✅ **Verify API key** is working
- ✅ **Test model availability** 
- ✅ **Troubleshoot connection** problems

## Quick Test
```bash
python test-ollama.py
```

If this works, your setup is ready for the main agent!

## Dependencies
- `ollama`: Official Ollama client
- `python-dotenv`: Environment variable loading