import sys
import json
import logging
from datetime import datetime
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Session

# Configure minimal stdio-safe logging to stderr (stdout is reserved for JSON-RPC)
logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mcp_server")

# Import database session
try:
    from app.core.database import SessionLocal
    from app.models.models import User, Meeting, Transcript, Task, Notification
except ImportError:
    SessionLocal = None
    logger.error("Database imports failed. MCP running in degraded mode.")


def get_db():
    if SessionLocal:
        return SessionLocal()
    return None


def handle_initialize(req_id: int, params: dict) -> dict:
    """Handles the MCP initialize handshake request."""
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "Meeting2Execution-MCP",
                "version": "1.0.0"
            }
        }
    }


def handle_list_tools(req_id: int) -> dict:
    """Lists the schema contracts for Postgres, FileSystem, Calendar, and Notification tools."""
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "tools": [
                {
                    "name": "postgres_query",
                    "description": "Execute read-only SQL queries against the database schemas.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The SELECT query to run (e.g. 'SELECT count(*) FROM tasks')"
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "filesystem_read_transcript",
                    "description": "Retrieve the transcript details for a given meeting ID.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "meeting_id": {
                                "type": "string",
                                "description": "UUID of the meeting record"
                            }
                        },
                        "required": ["meeting_id"]
                    }
                },
                {
                    "name": "calendar_create_meeting",
                    "description": "Schedules a new meeting item in the system.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Subject of the meeting"
                            },
                            "scheduled_time": {
                                "type": "string",
                                "description": "ISO-8601 format scheduled time (optional)"
                            }
                        },
                        "required": ["title"]
                    }
                },
                {
                    "name": "notifications_send_alert",
                    "description": "Dispatches warning or informative notifications to users.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "email": {
                                "type": "string",
                                "description": "Email address of target user"
                            },
                            "title": {
                                "type": "string",
                                "description": "Subject of alert notification"
                            },
                            "message": {
                                "type": "string",
                                "description": "Details of alert notification"
                            }
                        },
                        "required": ["email", "title", "message"]
                    }
                }
            ]
        }
    }


def execute_tool_call(name: str, args: dict) -> dict:
    """Executes target tool operations using SQLAlchemy database sessions."""
    db = get_db()
    if not db:
        return {"error": "Database session not available"}

    try:
        if name == "postgres_query":
            sql_text = args.get("query")
            # Enforce read-only locks for security
            if not sql_text.strip().lower().startswith("select"):
                return {"isError": True, "content": [{"type": "text", "text": "Unauthorized: Only read-only SELECT queries are permitted via MCP."}]}
            
            result = db.execute(sa.text(sql_text))
            rows = [dict(row._mapping) for row in result.all()]
            # Serialize datetimes to string
            for row in rows:
                for k, v in row.items():
                    if isinstance(v, (datetime, UUID)):
                        row[k] = str(v)
            return {"content": [{"type": "text", "text": json.dumps(rows)}]}

        elif name == "filesystem_read_transcript":
            meeting_uuid = args.get("meeting_id")
            transcript = db.query(Transcript).filter(Transcript.meeting_id == meeting_uuid).first()
            if not transcript:
                return {"isError": True, "content": [{"type": "text", "text": f"No transcript found for meeting: {meeting_uuid}"}]}
            return {"content": [{"type": "text", "text": transcript.raw_text}]}

        elif name == "calendar_create_meeting":
            title = args.get("title")
            sched_str = args.get("scheduled_time")
            sched_time = datetime.fromisoformat(sched_str) if sched_str else datetime.utcnow()
            
            new_meeting = Meeting(title=title, scheduled_time=sched_time, status="Uploaded")
            db.add(new_meeting)
            db.commit()
            db.refresh(new_meeting)
            return {"content": [{"type": "text", "text": f"Successfully created meeting with ID: {new_meeting.id}"}]}

        elif name == "notifications_send_alert":
            email = args.get("email")
            title = args.get("title")
            message = args.get("message")
            
            user = db.query(User).filter(User.email == email).first()
            if not user:
                return {"isError": True, "content": [{"type": "text", "text": f"User with email '{email}' not found."}]}
            
            notify = Notification(user_id=user.id, title=title, content=message, is_read=False)
            db.add(notify)
            db.commit()
            return {"content": [{"type": "text", "text": "Alert notification dispatched successfully."}]}

        else:
            return {"isError": True, "content": [{"type": "text", "text": f"Unknown tool name: {name}"}]}

    except Exception as e:
        logger.error(f"Error executing tool {name}: {str(e)}", exc_info=True)
        return {"isError": True, "content": [{"type": "text", "text": f"Execution failed: {str(e)}"}]}
    finally:
        db.close()


def main():
    logger.info("Initializing MCP Server stdio event loop...")
    
    while True:
        line = sys.stdin.readline()
        if not line:
            break
            
        try:
            req = json.loads(line)
            method = req.get("method")
            req_id = req.get("id")
            
            if method == "initialize":
                res = handle_initialize(req_id, req.get("params", {}))
            elif method == "tools/list":
                res = handle_list_tools(req_id)
            elif method == "tools/call":
                params = req.get("params", {})
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                result = execute_tool_call(tool_name, tool_args)
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": result
                }
            else:
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
                
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
            
        except Exception as e:
            logger.error(f"Error handling JSON-RPC message: {str(e)}")
            res = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal server error: {str(e)}"
                }
            }
            try:
                sys.stdout.write(json.dumps(res) + "\n")
                sys.stdout.flush()
            except Exception:
                pass


if __name__ == "__main__":
    main()
