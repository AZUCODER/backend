"""
Application entry point.

This is the main entry point for the FastAPI backend application.
"""

from app.main import app

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
