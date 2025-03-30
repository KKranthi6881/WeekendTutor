from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Body, Query, Path, Form
from sqlalchemy.orm import Session
import os
import uuid
from typing import Optional, Dict, Any
import openai
import json
import re
import tempfile

from app.schemas import schemas
from app.services.conversation_service import ConversationService
from app.services.openai_service import OpenAIService
from app.database.database import get_db
from datetime import datetime

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=schemas.ChatResponse)
async def process_chat(
    chat_request: schemas.ChatRequest, 
    db: Session = Depends(get_db)
):
    """
    Process a chat message from the user and return AI response
    """
    try:
        return await ConversationService.process_chat(db=db, chat_request=chat_request)
    except Exception as e:
        # Provide a fallback response if there's an API key error
        if "invalid_api_key" in str(e) or "Incorrect API key" in str(e):
            error_message = "Error: OpenAI API key is invalid or not set. Please configure a valid API key."
            print(f"OpenAI API key error: {str(e)}")
            
            # Return a fallback response - use attribute access for Pydantic model
            return {
                "text": error_message,
                "audio_url": None,
                "message": {
                    "id": "fallback",
                    "role": "assistant",
                    "content": error_message,
                    "conversation_id": getattr(chat_request, "conversation_id", 0)
                }
            }
        else:
            # For other errors, raise an HTTP exception
            raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@router.post("/text-to-speech", response_model=schemas.ChatResponse)
async def text_to_speech(data: Dict[str, Any]):
    """
    Convert text to speech
    """
    try:
        text = data.get("text", "")
        voice = data.get("voice", "alloy")
        
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")
        
        tts_response = await OpenAIService.text_to_speech(text, voice)
        return tts_response
    except Exception as e:
        # Provide a fallback response if there's an API key error
        if "invalid_api_key" in str(e) or "Incorrect API key" in str(e):
            error_message = "Error: OpenAI API key is invalid or not set. Please configure a valid API key."
            print(f"OpenAI API key error in TTS: {str(e)}")
            
            # Return a fallback response without audio
            return {
                "text": text,
                "audio_url": None,
                "message": f"Error: {error_message}"
            }
        else:
            # For other errors, raise an HTTP exception
            raise HTTPException(status_code=500, detail=f"Error generating speech: {str(e)}")

@router.post("/transcribe", response_model=schemas.TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Transcribe user's audio message
    """
    # Create uploads directory if it doesn't exist
    os.makedirs("app/static/uploads", exist_ok=True)
    
    # Save uploaded file
    file_path = f"app/static/uploads/{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    # Transcribe audio file
    text = await OpenAIService.transcribe_audio(file_path)
    
    # Clean up file after transcription (optional)
    os.remove(file_path)
    
    return schemas.TranscriptionResponse(text=text)

@router.post("/generate-explanation", response_model=Dict[str, Any])
async def generate_explanation(
    query: str = Body(..., embed=True),
    subject: str = Body("Math", embed=True)
):
    """
    Generate a step-by-step explanation for a query in a specific subject.
    This is mainly used for creating structured explanations that can be displayed
    in the explanation panel.
    """
    try:
        # Define prompts based on subject for kid-friendly explanations (2nd grade level)
        prompts = {
            "Math": "You are explaining a math problem to a 2nd grader. Break it down into simple, fun steps that a young child would understand. Use simple words and examples from everyday life. Format your response as JSON with numbered steps, each having a title and detailed content. For example: {\"steps\": [{\"title\": \"First we count\", \"content\": \"Let's count the apples one by one: 1, 2, 3!\"}, {\"title\": \"Then we add\", \"content\": \"Now we put all the apples together and count them all.\"}]}",
            
            "Reading": "You are explaining a reading passage to a 2nd grader. Break it down into fun, simple steps with clear explanations a young child would understand. Use simple words and relate to things they know. Format your response as JSON with numbered steps, each having a title and detailed content. For example: {\"steps\": [{\"title\": \"Who is in the story\", \"content\": \"The story is about a friendly dog named Spot who loves to play.\"}, {\"title\": \"What happened\", \"content\": \"Spot lost his favorite toy and went on an adventure to find it.\"}]}",
            
            "Science": "You are explaining a science concept to a 2nd grader. Break it down into exciting, simple steps with clear explanations that would make a young child curious and help them understand. Use simple words and everyday examples. Format your response as JSON with numbered steps, each having a title and detailed content. For example: {\"steps\": [{\"title\": \"Water is wet\", \"content\": \"When you touch water, your fingers get wet because water sticks to things!\"}, {\"title\": \"Ice is frozen water\", \"content\": \"When it gets very cold, water turns hard like a rock. That's ice!\"}]}",
            
            "Social Studies": "You are explaining a social studies topic to a 2nd grader. Break it down into friendly, simple steps with explanations that a young child would understand. Use simple words and examples from their world. Format your response as JSON with numbered steps, each having a title and detailed content. For example: {\"steps\": [{\"title\": \"Communities are where we live\", \"content\": \"A community is like a big neighborhood where people live, work and play together.\"}, {\"title\": \"People in communities help each other\", \"content\": \"In a community, we have helpers like teachers, doctors, and firefighters who keep everyone safe and happy.\"}]}"
        }
        
        # Get the appropriate prompt or use a default one
        prompt = prompts.get(subject, "You are explaining a concept to a 2nd grader. Break it down into friendly, simple steps with clear explanations a young child would understand. Use simple words and relatable examples. Format your response as JSON with numbered steps, each having a title and detailed content.")
        
        # Call OpenAI API with the appropriate prompt
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.7,
            max_tokens=800
        )
        
        # Extract the response content
        explanation_text = response.choices[0].message.content
        
        # Try to parse the response as JSON
        try:
            # First, try to extract JSON if it's embedded in markdown code blocks
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', explanation_text)
            if json_match:
                explanation_text = json_match.group(1)
            
            explanation_data = json.loads(explanation_text)
            
            # Ensure the explanation data has the expected structure
            if not explanation_data.get("steps"):
                explanation_data = {
                    "steps": [
                        {
                            "title": "Let's Learn!",
                            "content": explanation_text
                        }
                    ]
                }
        except (json.JSONDecodeError, TypeError):
            # If parsing fails, create a structured format manually
            # Split by sentences or paragraphs to create steps
            paragraphs = explanation_text.split('\n\n')
            if len(paragraphs) > 1:
                steps = []
                for i, para in enumerate(paragraphs):
                    if para.strip():
                        title = f"Step {i+1}"
                        if ':' in para.split('\n')[0]:
                            parts = para.split(':', 1)
                            title = parts[0].strip()
                            content = parts[1].strip()
                        else:
                            sentences = para.split('. ')
                            if len(sentences) > 1:
                                title = sentences[0]
                                content = '. '.join(sentences[1:])
                            else:
                                content = para
                        steps.append({"title": title, "content": content})
                explanation_data = {"steps": steps}
            else:
                explanation_data = {
                    "steps": [
                        {
                            "title": "Let's Learn!",
                            "content": explanation_text
                        }
                    ]
                }
        
        return {
            "subject": subject,
            "query": query,
            "explanation": explanation_data
        }
    
    except Exception as e:
        print(f"Error generating explanation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate explanation: {str(e)}"
        )

@router.post("/interactive-learning", response_model=Dict[str, Any])
async def start_interactive_learning(
    query: str = Body(..., embed=True),
    subject: str = Body("General", embed=True),
    grade_level: int = Body(2, embed=True)
):
    """
    Start an interactive learning session about a topic.
    Breaks down the concept into sequential steps for guided learning.
    """
    try:
        # Define the prompt for interactive learning
        prompt = f"""You are a friendly, encouraging tutor for a {grade_level}nd grade student. 
The student wants to learn about: "{query}"

Break down this concept into 3-5 sequential learning steps. Each step should:
1. Present a small piece of information
2. Ask a simple question to check understanding
3. Be engaging and child-friendly

Format your response as a conversation step. Your response will be shown directly to the student, 
so speak to them directly with warm, engaging language. Ask just ONE question at a time.

For example, if teaching about butterflies, your first step might be:
"Let's learn about butterflies! Did you know that butterflies start out as tiny eggs? 
Then they become caterpillars that love to munch on leaves. What's your favorite insect?"

Keep your response under 4 sentences and end with a clear question that's appropriate for a {grade_level}nd grader."""

        # Call OpenAI API with the prompt
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        # Extract the response content
        learning_step = response.choices[0].message.content
        
        # Return the learning step along with metadata
        return {
            "subject": subject,
            "query": query,
            "first_step": learning_step,
            "step_number": 1,
            "total_steps": 4  # This is approximate, will be refined during interaction
        }
    
    except Exception as e:
        print(f"Error starting interactive learning: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start interactive learning: {str(e)}"
        )

@router.post("/process-learning-response", response_model=Dict[str, Any])
async def process_learning_response(
    user_response: str = Body(..., embed=True),
    subject: str = Body("General", embed=True),
    query: str = Body(..., embed=True),
    current_step: int = Body(..., embed=True),
    total_steps: int = Body(4, embed=True),
    previous_context: str = Body("", embed=True)
):
    """
    Process the user's response in an interactive learning session and provide the next step.
    """
    try:
        # Determine if this is the final step
        is_final_step = current_step >= total_steps
        
        # Define the prompt based on whether this is the final step
        if is_final_step:
            prompt = f"""You are a friendly, encouraging tutor for a young student.
The student has been learning about: "{query}"

They just responded to your previous question with: "{user_response}"

This is the FINAL step in the learning sequence. Provide a summary of what they've learned
and congratulate them on completing the lesson. Keep your tone warm and encouraging.

Previous context from this conversation:
{previous_context}

Your response should be 3-4 sentences, simple enough for a young child to understand,
and should make the student feel accomplished."""
        else:
            prompt = f"""You are a friendly, encouraging tutor for a young student.
The student is learning about: "{query}"

They just responded to your previous question with: "{user_response}"

This is step {current_step} of {total_steps} in the learning sequence.

Previous context from this conversation:
{previous_context}

Provide the next piece of information and ask ONE new question to check understanding.
Your response should be 3-4 sentences, simple enough for a young child to understand.
Always respond with enthusiasm to keep the student engaged."""

        # Call OpenAI API with the prompt
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_response}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        # Extract the response content
        next_step = response.choices[0].message.content
        
        # Update the context for future interactions
        updated_context = f"{previous_context}\nTutor: [Previous guidance]\nStudent: {user_response}\nTutor: {next_step}"
        
        # Return the next step along with updated metadata
        return {
            "subject": subject,
            "query": query,
            "next_step": next_step,
            "step_number": current_step + 1,
            "total_steps": total_steps,
            "is_final_step": is_final_step,
            "context": updated_context
        }
    
    except Exception as e:
        print(f"Error processing learning response: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process learning response: {str(e)}"
        )

@router.post("/with-image", response_model=schemas.ChatResponse)
async def chat_with_image(
    file: UploadFile = File(...),
    message: str = Form(...),
    user_id: int = Form(...),
    conversation_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Process a chat message that includes an uploaded image
    """
    file_path = ""
    try:
        print(f"Received image upload request - file: {file.filename}, message: {message}, user_id: {user_id}, conversation_id: {conversation_id}")
        
        # Create uploads directory if it doesn't exist
        os.makedirs("app/static/uploads/images", exist_ok=True)
        
        # Generate a unique filename with original extension
        file_extension = os.path.splitext(file.filename)[1].lower() if file.filename else ".jpg"
        filename = f"{uuid.uuid4()}{file_extension}"
        file_path = f"app/static/uploads/images/{filename}"
        
        # Save the uploaded file
        file_content = await file.read()
        if not file_content:
            raise ValueError("Empty file content received")
            
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
            
        print(f"Saved image to {file_path}")
            
        # Create the full URL path to the image
        base_url = "http://localhost:8000"  # This should be configurable or derived from request
        image_url = f"{base_url}/static/uploads/images/{filename}"
        
        print(f"Image URL: {image_url}")
        
        # Validate user_id
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            user_id_int = 1  # Default to user 1 if parsing fails
            print(f"Invalid user_id format: {user_id}, using default: 1")
        
        # Create a temporary copy of the message without image_url
        # This is to make it backward compatible if the database migration failed
        try:
            # First try with image_url
            chat_request = schemas.ChatRequest(
                message=message,
                user_id=user_id_int,
                conversation_id=int(conversation_id) if conversation_id else None,
                image_url=image_url
            )
            
            print(f"Processing chat request with image: {chat_request}")
            
            # Use the existing chat processing flow with the image URL
            return await ConversationService.process_chat(db=db, chat_request=chat_request)
        except Exception as db_error:
            if "no column named image_url" in str(db_error):
                print("Warning: Database schema missing image_url column. Falling back to text-only message.")
                # Fall back to a message without image_url
                chat_request = schemas.ChatRequest(
                    message=f"{message} (Image uploaded but not stored in database)",
                    user_id=user_id_int,
                    conversation_id=int(conversation_id) if conversation_id else None
                )
                
                # Process and analyze the image directly with OpenAI Vision
                try:
                    image_analysis = await OpenAIService.analyze_image(
                        image_url=image_url,
                        prompt=f"This student sent an image with the message: '{message}'. Please analyze the image and provide helpful, educational guidance."
                    )
                    
                    # Process the regular chat without storing the image
                    chat_response = await ConversationService.process_chat(db=db, chat_request=chat_request)
                    
                    # Override the text with the image analysis result
                    chat_response.text = image_analysis
                    
                    # If there's a message, update its content as well
                    if chat_response.message and 'content' in chat_response.message:
                        chat_response.message['content'] = image_analysis
                    
                    return chat_response
                except Exception as vision_error:
                    print(f"Error analyzing image with Vision API: {vision_error}")
                    raise
            else:
                raise db_error
        
    except Exception as e:
        print(f"Error in chat_with_image: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Handle errors
        if file_path and os.path.exists(file_path):
            os.remove(file_path)  # Clean up file on error
            print(f"Cleaned up file: {file_path}")
            
        if "invalid_api_key" in str(e) or "Incorrect API key" in str(e):
            error_message = "Error: OpenAI API key is invalid or not set. Please configure a valid API key."
            print(f"OpenAI API key error: {str(e)}")
            
            # Return a fallback response
            return {
                "text": error_message,
                "audio_url": None,
                "message": {
                    "id": "fallback",
                    "role": "assistant",
                    "content": error_message,
                    "conversation_id": conversation_id or 0
                }
            }
        else:
            # For other errors, raise an HTTP exception
            raise HTTPException(status_code=500, detail=f"Error processing chat with image: {str(e)}") 