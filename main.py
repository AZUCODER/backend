"""
Application entry point.

This is the main entry point for the FastAPI backend application.
"""

from app.main import app

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
