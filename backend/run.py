import uvicorn
import os
import sys

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

port = int(os.environ.get("PORT", "8001"))

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=False)
