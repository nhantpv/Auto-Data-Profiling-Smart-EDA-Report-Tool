import uvicorn
import os

if __name__ == "__main__":
    print("Starting Smart EDA Web UI on http://127.0.0.1:8000 ...")
    uvicorn.run("src.webapp.app:app", host="127.0.0.1", port=8000, reload=True)
