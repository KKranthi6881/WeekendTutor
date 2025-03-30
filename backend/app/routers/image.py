from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
import os
from pathlib import Path
import shutil
import uuid
from typing import Optional
import requests
import json
import openai

# Create router
router = APIRouter(
    prefix="/images",
    tags=["images"],
    responses={404: {"description": "Not found"}},
)

# Ensure OpenAI API key is set
if "OPENAI_API_KEY" not in os.environ:
    # Use a default key for development or read from config
    os.environ["OPENAI_API_KEY"] = "your-openai-api-key-here"  # Replace with actual key in production

@router.post("/upload")
async def upload_image(
    request: Request,
    image: UploadFile = File(...),
    conversation_id: int = Form(...)
):
    """Upload an image for analysis"""
    # Validate file type
    if not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Create a unique filename
    filename = f"{uuid.uuid4().hex}{Path(image.filename).suffix}"
    
    # Path to save the image
    upload_dir = Path("app/static/uploads/images")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename
    
    # Save the uploaded file
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
    
    # Generate URL for the saved image
    base_url = str(request.base_url).rstrip('/')
    image_url = f"{base_url}/static/uploads/images/{filename}"
    
    return {
        "success": True,
        "image_url": image_url,
        "message": "Image uploaded successfully"
    }

@router.post("/analyze")
async def analyze_image(request: Request, data: dict):
    """Analyze an uploaded image using OpenAI's Vision model"""
    image_url = data.get("image_url")
    conversation_id = data.get("conversation_id")
    
    if not image_url:
        raise HTTPException(status_code=400, detail="Image URL is required")
    
    if not conversation_id:
        raise HTTPException(status_code=400, detail="Conversation ID is required")
    
    try:
        # Create a context prompt that guides the AI to give educational hints rather than direct answers
        system_prompt = """
        You are an educational AI tutor for children. A student has uploaded an image.
        
        Identify what's in the image and determine if it's educational content like:
        1. A math problem
        2. A science question
        3. A reading/writing task
        4. Other educational content
        
        If it's educational content:
        - DON'T solve the problem directly
        - Provide educational guidance and hints that help the student learn
        - Break down the process into steps they can follow
        - Use age-appropriate language
        - Ask questions to prompt their thinking
        
        If it's not clearly educational content:
        - Just describe what you see and ask if they need help with anything specific
        
        Format your response to be engaging and encouraging.
        """
        
        # Call OpenAI's GPT-4 Vision model
        completion = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]}
            ],
            max_tokens=500
        )
        
        analysis = completion.choices[0].message.content
        
        # Detect if this seems like educational content to set up tutorial mode
        educational_content_patterns = [
            "math problem", "equation", "science question", "experiment",
            "reading", "writing", "homework", "problem to solve", "steps to follow"
        ]
        
        should_enter_tutorial_mode = any(pattern in analysis.lower() for pattern in educational_content_patterns)
        
        # If it's educational content, create learning steps
        learning_steps = []
        if should_enter_tutorial_mode:
            # Call GPT again to generate appropriate learning steps based on the image
            step_completion = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an educational assistant creating step-by-step guidance for a child. Never provide direct answers, only hints and educational guidance."},
                    {"role": "user", "content": f"Based on this analysis of an educational image, create 3-5 interactive learning steps that guide the child to solve it themselves: '{analysis}'"}
                ],
                max_tokens=500
            )
            
            steps_text = step_completion.choices[0].message.content
            
            # Extract steps from the response
            import re
            step_matches = re.findall(r'\d+\.\s+[^\n]+', steps_text)
            
            if step_matches:
                learning_steps = [step.strip() for step in step_matches]
            else:
                # Fallback if regex doesn't find steps
                learning_steps = [line.strip() for line in steps_text.split('\n') 
                                 if line.strip() and not line.strip().startswith("#")][:5]
        
        # Generate audio for the response
        audio_response = openai.Audio.create(
            model="tts-1",
            voice="alloy",
            input=analysis
        )
        
        # Save audio file
        audio_filename = f"response-{uuid.uuid4().hex}.mp3"
        audio_dir = Path("app/static/audio")
        audio_dir.mkdir(parents=True, exist_ok=True)
        
        audio_path = audio_dir / audio_filename
        with open(audio_path, "wb") as f:
            f.write(audio_response.content)
        
        # Generate audio URL
        base_url = str(request.base_url).rstrip('/')
        audio_url = f"{base_url}/static/audio/{audio_filename}"
        
        return {
            "success": True,
            "response": analysis,
            "audio_url": audio_url,
            "should_enter_tutorial_mode": should_enter_tutorial_mode,
            "learning_context": analysis,
            "learning_steps": learning_steps
        }
        
    except Exception as e:
        print(f"Error analyzing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing image: {str(e)}") 