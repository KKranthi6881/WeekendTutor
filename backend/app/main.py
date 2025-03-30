from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import openai
from pathlib import Path

# Get API key from environment variable or use a placeholder that tells the user to replace it
# You must replace this with your actual OpenAI API key to use chat and TTS features
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE")
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# Create FastAPI application
app = FastAPI(
    title="AI Voice Tutor",
    description="A tutoring voice agent for elementary students",
    version="1.0.0"
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create necessary directories
static_dir = Path("app/static")
static_dir.mkdir(parents=True, exist_ok=True)

audio_dir = static_dir / "audio"
audio_dir.mkdir(exist_ok=True)

uploads_dir = static_dir / "uploads"
uploads_dir.mkdir(exist_ok=True)

images_dir = uploads_dir / "images"
images_dir.mkdir(exist_ok=True)

data_dir = Path("app/data")
data_dir.mkdir(parents=True, exist_ok=True)

conversations_dir = data_dir / "conversations"
conversations_dir.mkdir(exist_ok=True)

users_dir = data_dir / "users"
users_dir.mkdir(exist_ok=True)

# Mount static directories
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Create API prefix for all endpoints
api_prefix = "/api"

# Import and include routers
try:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    from backend.app.routers import image, learning, conversations, users, chat, messages
    
    # Include routers with API prefix
    app.include_router(image.router, prefix=api_prefix)
    app.include_router(learning.router, prefix=api_prefix)
    app.include_router(conversations.router, prefix=api_prefix)
    app.include_router(users.router, prefix=api_prefix)
    app.include_router(chat.router, prefix=api_prefix)
    app.include_router(messages.router, prefix=api_prefix)
except Exception as e:
    print(f"Error including routers: {e}")

@app.get("/")
async def root():
    return {"message": "Welcome to the AI Voice Tutor API"}

@app.post("/api/chatgpt")
async def chat_with_gpt(request: Request):
    """
    Endpoint to chat with GPT-3.5-turbo
    """
    try:
        data = await request.json()
        messages = data.get("messages", [])
        
        if not messages:
            return JSONResponse(
                status_code=400,
                content={"error": "No messages provided"}
            )
            
        # Use the new client format
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
        )
        
        response = completion.choices[0].message.content
        
        # Generate audio from the response text
        audio_response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=response
        )
        
        # Save audio to file
        import uuid
        
        audio_filename = f"response-{uuid.uuid4().hex}.mp3"
        audio_path = os.path.join("app/static/audio", audio_filename)
        
        with open(audio_path, "wb") as f:
            f.write(audio_response.content)
            
        # Construct audio URL
        base_url = str(request.base_url).rstrip('/')
        audio_url = f"{base_url}/static/audio/{audio_filename}"
        
        return {"text": response, "audio_url": audio_url}
        
    except Exception as e:
        print(f"Error in chat_with_gpt: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"An error occurred: {str(e)}"}
        )

@app.post("/api/tts")
async def text_to_speech(request: Request):
    """
    Endpoint to convert text to speech
    """
    try:
        data = await request.json()
        text = data.get("text", "")
        voice = data.get("voice", "alloy")  # Default voice is alloy
        
        if not text:
            return JSONResponse(
                status_code=400,
                content={"error": "No text provided"}
            )
            
        # Generate audio from the text using the new client format
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        audio_response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        
        # Save audio to file
        import uuid
        
        audio_filename = f"tts-{uuid.uuid4().hex}.mp3"
        audio_path = os.path.join("app/static/audio", audio_filename)
        
        with open(audio_path, "wb") as f:
            f.write(audio_response.content)
            
        # Construct audio URL
        base_url = str(request.base_url).rstrip('/')
        audio_url = f"{base_url}/static/audio/{audio_filename}"
        
        return {"audio_url": audio_url}
        
    except Exception as e:
        print(f"Error in text_to_speech: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"An error occurred: {str(e)}"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True) 