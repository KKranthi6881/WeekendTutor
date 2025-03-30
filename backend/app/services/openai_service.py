import os
import openai
import uuid
from openai import OpenAI
from typing import List, Dict, Any, Optional, Tuple
import requests
import tempfile
from PIL import Image
import io
import base64

# Initialize the OpenAI client inside each method to always use the current environment variable
# This allows for runtime updates to the API key

class OpenAIService:
    @staticmethod
    async def generate_response(messages: List[Dict[str, Any]]) -> str:
        """
        Generate a response from the OpenAI API using formatted messages.
        This handles both text-only and image-containing messages.
        """
        try:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is not set")
            
            client = OpenAI(api_key=api_key)
            
            # Log the number of messages and whether they contain images
            print(f"Generating response with {len(messages)} messages")
            has_images = any(
                isinstance(msg.get('content'), list) and 
                any(isinstance(c, dict) and c.get('type') == 'image_url' for c in msg.get('content', []))
                for msg in messages
            )
            print(f"Messages contain images: {has_images}")
            
            # Ensure proper message formatting
            validated_messages = []
            for msg in messages:
                if isinstance(msg.get('content'), list):
                    # Validate image URLs in content if it's a list
                    content_list = []
                    for item in msg['content']:
                        if isinstance(item, dict) and item.get('type') == 'image_url':
                            # Ensure the image URL is a base64 data URL
                            image_url = item.get('image_url', {}).get('url', '')
                            if not image_url.startswith('data:'):
                                print(f"Warning: Image URL is not in base64 format: {image_url[:30]}...")
                                # Skip this item as it's not valid
                                continue
                        content_list.append(item)
                    
                    if content_list:
                        validated_msg = {
                            'role': msg['role'],
                            'content': content_list
                        }
                        validated_messages.append(validated_msg)
                    else:
                        # If no valid content items, convert to a text-only message
                        validated_messages.append({
                            'role': msg['role'],
                            'content': "I sent an image but it couldn't be processed."
                        })
                else:
                    # Text-only message
                    validated_messages.append(msg)
            
            # Choose appropriate model based on content
            model = "gpt-4o" if has_images else "gpt-4o"
            
            # Call the API with validated messages
            completion = client.chat.completions.create(
                model=model,
                messages=validated_messages,
                temperature=0.7,
                max_tokens=800
            )
            
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Error generating OpenAI response: {e}")
            import traceback
            traceback.print_exc()
            
            # Provide a more helpful error message
            error_message = str(e)
            if "invalid_image_url" in error_message or "invalid_request_error" in error_message:
                return "I'm having trouble processing the images in our conversation history. Let's continue our discussion without referring to previous images. What would you like to talk about next?"
            elif "rate_limit_exceeded" in error_message:
                return "I'm currently experiencing high demand. Please try again in a moment."
            else:
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
            
    @staticmethod
    def image_to_base64(file_path: str) -> Optional[Tuple[str, str]]:
        """
        Convert an image file to a base64 data URI
        Returns (base64_data, content_type) or None if conversion fails
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                return None
            
            # Check if it's a HEIC file
            is_heic = file_path.lower().endswith(('.heic', '.heif'))
            
            if is_heic:
                try:
                    # Try to use pillow_heif for HEIC conversion
                    try:
                        import pillow_heif
                        pillow_heif.register_heif_opener()
                    except ImportError:
                        print("Warning: pillow_heif not installed, trying with PIL directly")
                    
                    # Open and convert to JPEG
                    img = Image.open(file_path)
                    
                    # Convert to base64 using buffer
                    buffer = io.BytesIO()
                    img.save(buffer, format="JPEG")
                    img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    content_type = "image/jpeg"
                    
                    return img_data, content_type
                except Exception as e:
                    print(f"Error converting HEIC: {e}")
                    return None
            else:
                # For regular image formats
                with open(file_path, "rb") as img_file:
                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                
                # Get content type based on file extension
                ext = os.path.splitext(file_path)[1].lower()
                if ext in ['.jpg', '.jpeg']:
                    content_type = 'image/jpeg'
                elif ext == '.png':
                    content_type = 'image/png'
                elif ext == '.gif':
                    content_type = 'image/gif'
                elif ext == '.webp':
                    content_type = 'image/webp'
                else:
                    content_type = 'image/jpeg'  # Default to JPEG
                
                return img_data, content_type
                
        except Exception as e:
            print(f"Error converting image to base64: {e}")
            return None
    
    @staticmethod
    async def analyze_image(image_url: str, prompt: str = "What's in this image?") -> str:
        """
        Analyze an image using OpenAI's GPT-4 Vision API.
        """
        try:
            print(f"Analyzing image at URL: {image_url}")
            base64_image = None
            
            # Extract the file path from the URL
            # If the URL is a local URL on the server, extract the file path
            if "localhost" in image_url or "127.0.0.1" in image_url:
                # Extract the path part after "/static/"
                if "/static/" in image_url:
                    file_path = "app/static/" + image_url.split("/static/", 1)[1]
                    print(f"Local file path: {file_path}")
                    
                    # Convert image to base64
                    result = OpenAIService.image_to_base64(file_path)
                    if result:
                        img_data, content_type = result
                        base64_image = f"data:{content_type};base64,{img_data}"
                        print(f"Successfully converted local image to base64")
                else:
                    file_path = None
            else:
                file_path = None
                
            # If we don't have a base64 image yet, try to download from URL
            if not base64_image:
                try:
                    print(f"Attempting to download image from URL: {image_url}")
                    response = requests.get(image_url, timeout=15)
                    if response.status_code == 200:
                        # Try to process the image data with PIL
                        img = Image.open(io.BytesIO(response.content))
                        
                        # Convert to base64
                        buffer = io.BytesIO()
                        img.save(buffer, format="JPEG")
                        img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                        base64_image = f"data:image/jpeg;base64,{img_data}"
                        print("Downloaded and converted image to base64 JPEG")
                    else:
                        raise ValueError(f"Failed to download image: HTTP {response.status_code}")
                except Exception as e:
                    print(f"Error downloading image: {e}")
                    return f"I couldn't analyze this image properly. There was an issue downloading the image file. Error: {str(e)}"
            
            # Use the new OpenAI client with current API key
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is not set")
            
            client = OpenAI(api_key=api_key)
            
            # Configure the prompt for educational context
            system_prompt = """You are a friendly AI tutor specialized in teaching elementary school students.
            The student has shared an image that might contain educational content like a textbook page, 
            homework problem, or educational material.
            
            Your goals are:
            1. Identify what's in the image (e.g., math problem, reading passage, science diagram)
            2. If the image has multiple problems, ONLY focus on the specific problem number mentioned in the prompt
            3. If no specific problem number is mentioned, focus ONLY on the first problem you see
            4. Provide helpful, age-appropriate guidance
            5. Don't solve problems directly - instead give hints and explanations that help the student learn
            6. Keep explanations simple, using concrete examples and step-by-step guidance
            7. If there are multiple problems in the image, mention this fact and tell the student you'll help with one problem at a time
            
            Use a warm, encouraging tone in your response. Remember to ONLY focus on one problem at a time, even if the image contains multiple problems."""
            
            print(f"Sending image to GPT-4 Vision with prompt: '{prompt}'")
            
            # Prepare content for the message
            if base64_image:
                content = [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": base64_image}}
                ]
            else:
                print("No image data available to analyze")
                return "I couldn't analyze this image. There was an issue processing the image file."
            
            # Call OpenAI API
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            print(f"Image analysis complete. Response length: {len(content)} characters")
            
            return content
            
        except Exception as e:
            print(f"Error analyzing image: {e}")
            import traceback
            traceback.print_exc()
            return f"I couldn't analyze this image properly. The image format might not be supported or there might be an issue with the file. Error: {str(e)}"
    
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
                model="gpt-4o",
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