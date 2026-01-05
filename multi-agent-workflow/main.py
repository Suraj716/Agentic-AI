"""
FastAPI Backend for Multi-Agent Workflow System
"""
import asyncio
import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn

# Add the parent directory to the Python path
current_dir = Path(__file__).parent.absolute()
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from supervisor_main import MultiAgentSupervisor

app = FastAPI(title="Multi-Agent Workflow API", version="1.0.0")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global supervisor instance
supervisor = None

class QueryRequest(BaseModel):
    query: str
    user_id: str = "default"

class QueryResponse(BaseModel):
    response: str
    agent_used: str
    status: str
    raw_data: Optional[Dict[str, Any]] = None

@app.on_event("startup")
async def startup_event():
    """Initialize the supervisor on startup"""
    global supervisor
    try:
        print("🚀 Starting Multi-Agent Workflow Backend...")
        supervisor = MultiAgentSupervisor()
        await supervisor.initialize()
        print("✅ Multi-Agent Supervisor initialized successfully!")
    except Exception as e:
        print(f"❌ Failed to initialize supervisor: {e}")
        raise

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Multi-Agent Workflow API is running!", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    global supervisor
    if supervisor is None:
        raise HTTPException(status_code=503, detail="Supervisor not initialized")
    
    return {
        "status": "healthy",
        "supervisor_initialized": supervisor is not None,
        "available_agents": ["GeneralChat", "MonitoringMCP", "SystemOps", "HelpDocs"]
    }

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a query through the multi-agent supervisor"""
    global supervisor
    
    if supervisor is None:
        raise HTTPException(status_code=503, detail="Supervisor not initialized")
    
    try:
        print(f"📝 Processing query: {request.query[:100]}...")
        result = await supervisor.process_query(request.query)
        
        return QueryResponse(
            response=result.get("response", "No response received"),
            agent_used=result.get("agent_used", "Unknown"),
            status="success",
            raw_data=result.get("raw_data")
        )
    except Exception as e:
        print(f"❌ Error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

@app.get("/agents")
async def get_available_agents():
    """Get list of available agents"""
    return {
        "agents": [
            {
                "name": "GeneralChat",
                "description": "General conversation and non-specialized queries"
            },
            {
                "name": "MonitoringMCP",
                "description": "System monitoring using MCP tools (Grafana, Prometheus)"
            },
            {
                "name": "SystemOps",
                "description": "System operations and administrative tasks"
            },
            {
                "name": "HelpDocs",
                "description": "Documentation and help-related queries"
            }
        ]
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8080,
        reload=True
    )