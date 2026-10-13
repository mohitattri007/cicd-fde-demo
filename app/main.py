import os
from fastapi import FastAPI

APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
app = FastAPI(title="Support Agent API", version=APP_VERSION)


@app.get("/")
def root():
    return {"service": "support-agent-api", "message": "CI/CD demo is running", "version": APP_VERSION}


@app.get("/health")
def health():
    return {"status": "ok"}

# Just testing it to test CI/CD pipeline

@app.get("/version")
def version():
    return {"version": APP_VERSION}
