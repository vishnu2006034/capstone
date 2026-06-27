import sys
from google.antigravity import LocalAgentConfig

def get_mcp_agent_config() -> LocalAgentConfig:
    """
    Formulates a unified Google ADK LocalAgentConfig connecting agents 
    to the custom PostgreSQL, FileSystem, Notifications, and Calendar MCP server.
    
    Dynamically targets the active python virtual environment's executable.
    """
    return LocalAgentConfig(
        mcp_servers=[
            {
                "name": "meeting2execution-mcp",
                "command": sys.executable,
                "args": ["-m", "app.mcp.server"]
            }
        ]
    )
