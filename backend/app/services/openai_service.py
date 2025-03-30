import os
import openai
import uuid
from openai import OpenAI
from typing import List, Dict, Any

# Initialize the OpenAI client inside each method to always use the current environment variable
# This allows for runtime updates to the API key

class OpenAIService:
    @staticmethod
    async def generate_response(messages: List[Dict[str, str]], model: str = "gpt-3.5-turbo") -> str:
        """
        Generate a response from OpenAI's API.
        """
        try:
            # Use the new OpenAI client with current API key
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            completion = client.chat.completions.create(
                model=model,
                messages=messages
            )
            
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Error generating OpenAI response: {e}")
            raise Exception(f"Error generating OpenAI response: {e}")
    
    @staticmethod
    async def text_to_speech(text: str, voice: str = "alloy") -> Dict[str, Any]:
        """
        Convert text to speech using OpenAI's API.
        """
        try:
            # Use the new OpenAI client with current API key
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            # Generate audio from the text
            response = client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            
            # Save the audio file
            os.makedirs("app/static/audio", exist_ok=True)
            file_name = f"{uuid.uuid4()}.mp3"
            file_path = f"app/static/audio/{file_name}"
            
            with open(file_path, "wb") as f:
                f.write(response.content)
            
            # Return response with audio URL
            return {
                "text": text,
                "audio_url": f"/static/audio/{file_name}",
                "message": "Audio generated successfully"
            }
        except Exception as e:
            print(f"Error generating speech: {e}")
            raise Exception(f"Error generating speech: {e}")
    
    @staticmethod
    async def transcribe_audio(file_path: str) -> str:
        """
        Transcribe audio to text using OpenAI's API.
        """
        try:
            # Use the new OpenAI client with current API key
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            with open(file_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            
            return transcript.text
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            raise Exception(f"Error transcribing audio: {e}")
            
    # Fallback method for compatibility with older code
    @staticmethod
    async def chat_completion(messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Generate a chat completion using OpenAI's API
        Returns the full response object for compatibility
        """
        try:
            # Use the new OpenAI client with current API key
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            # Return a dict that mimics the older API response format
            return {
                "choices": [
                    {
                        "message": {
                            "content": response.choices[0].message.content
                        }
                    }
                ]
            }
        except Exception as e:
            print(f"Error in chat completion: {e}")
            return {
                "choices": [
                    {
                        "message": {
                            "content": "I'm sorry, I encountered an error. Please try again."
                        }
                    }
                ]
            } 