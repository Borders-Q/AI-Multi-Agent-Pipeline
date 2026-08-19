import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI(title="天韬（SkyT） Cloud Skill Registry")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

REGISTRY_DIR = os.path.join(os.path.dirname(__file__), "cloud_registry")

# Serve the raw python files and json static files
app.mount("/", StaticFiles(directory=REGISTRY_DIR), name="static")

if __name__ == "__main__":
    print(f"Cloud Registry Server starting on http://127.0.0.1:8001")
    print(f"Serving files from {REGISTRY_DIR}")
    uvicorn.run(app, host="127.0.0.1", port=8001)
