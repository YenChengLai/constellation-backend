from fastapi import FastAPI
from .config import settings

# Initialize the FastAPI app
# We add a title for documentation purposes
app = FastAPI(title=settings.APP_NAME)

@app.get("/health", tags=["System"])
def health_check():
    """
    Health check endpoint to confirm the service is running.
    """
    return {"status": "OK", "service": settings.APP_NAME}