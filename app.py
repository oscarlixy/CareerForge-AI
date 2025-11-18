import os
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# --- Configuration ---
# Get the API key from Hugging Face Secrets
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

# --- FastAPI App Initialization ---
app = FastAPI()

# Create a reusable HTTP client
client = httpx.AsyncClient()

# --- Absolute Path Configuration ---
# Get the absolute path of the directory where this file is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Define the path to the static directory
STATIC_DIR = os.path.join(BASE_DIR, "static")


# --- API Endpoint ---
@app.post("/call-deepseek")
async def proxy_deepseek(request: Request):
    """
    This endpoint receives the request from our frontend (index.html),
    adds the secret API key, and forwards it to the DeepSeek API.
    """
    # Check if the API key is configured in HF Secrets
    print(f"[DEBUG] DEEPSEEK_API_KEY exists: {bool(DEEPSEEK_API_KEY)}")
    if DEEPSEEK_API_KEY:
        print(f"[DEBUG] API Key starts with: {DEEPSEEK_API_KEY[:10]}...")
    
    if not DEEPSEEK_API_KEY:
        print("[ERROR] DEEPSEEK_API_KEY is not set!")
        raise HTTPException(
            status_code=500, 
            detail="DEEPSEEK_API_KEY is not set on the server."
        )
        
    try:
        # Get the original JSON body from the frontend
        body = await request.json()

        # Prepare the authorization headers for DeepSeek
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        
        # Make the asynchronous request to DeepSeek
        response = await client.post(
            DEEPSEEK_ENDPOINT,
            json=body,      # Forward the body from the frontend
            headers=headers,
            timeout=300.0    # Set a 300-second timeout (5 minutes)
        )
        
        # Check if DeepSeek returned an error
        response.raise_for_status()
        
        # Return DeepSeek's successful response directly to the frontend
        return response.json()

    except httpx.HTTPStatusError as e:
        # Handle errors from the DeepSeek API
        error_msg = f"DeepSeek API Error: {e.response.status_code} - {e.response.text}"
        print(f"[ERROR] {error_msg}")
        raise HTTPException(
            status_code=e.response.status_code, 
            detail=error_msg
        )
    except Exception as e:
        # Handle any other unexpected errors
        error_msg = f"Internal server error: {type(e).__name__} - {str(e)}"
        print(f"[ERROR] {error_msg}")
        import traceback
        print(f"[TRACEBACK] {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail=error_msg
        )


# --- Static File Serving ---
# Mount the 'static' directory to serve index.html and other assets
# Use the absolute path to be safe
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def read_root():
    """
    Serves the main index.html file from the 'static' directory.
    """
    try:
        # Use the absolute path to be safe
        with open(os.path.join(STATIC_DIR, "index.html")) as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Error: index.html not found</h1><p>Ensure index.html is in a 'static' folder.</p>", 
            status_code=404
        )
