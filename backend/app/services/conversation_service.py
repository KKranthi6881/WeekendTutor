from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import os
import uuid
import aiofiles
import re

from app.models.models import User, Conversation, Message
from app.schemas import schemas
from app.services.openai_service import OpenAIService

class ConversationService:
    @staticmethod
    async def create_conversation(db: Session, conversation: schemas.ConversationCreate) -> Conversation:
        db_conversation = Conversation(**conversation.model_dump())
        db.add(db_conversation)
        db.commit()
        db.refresh(db_conversation)
        return db_conversation
    
    @staticmethod
    async def get_conversation(db: Session, conversation_id: int) -> Optional[Conversation]:
        return db.query(Conversation).filter(Conversation.id == conversation_id).first()
    
    @staticmethod
    async def get_messages(db: Session, conversation_id: int) -> List[Message]:
        return db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.timestamp).all()
    
    @staticmethod
    async def add_message(db: Session, message: schemas.MessageCreate) -> Message:
        db_message = Message(**message.model_dump())
        db.add(db_message)
        db.commit()
        db.refresh(db_message)
        return db_message
    
    @staticmethod
    async def format_messages_for_openai(messages: List[Message]) -> List[Dict[str, str]]:
        # Get the conversation to determine the subject
        conversation = messages[0].conversation if messages else None
        subject = conversation.subject if conversation else "General"
        
        # Base system prompt
        system_content = """You are a friendly AI tutor specialized in teaching elementary school students. Follow these teaching principles:

1. AGE-APPROPRIATE LANGUAGE: Use simple words and short sentences. Avoid complex terminology unless explaining it carefully.

2. STRUCTURED TEACHING APPROACH:
   - Start with a brief, friendly introduction to the topic
   - Break down concepts into very small steps
   - Use concrete examples relevant to children's experiences
   - Connect new ideas to things students already know
   - Provide clear, step-by-step instructions for any activities

3. POSITIVE REINFORCEMENT:
   - Praise specific efforts ("Great job working through that problem!")
   - Use encouraging language when students struggle
   - Celebrate small wins and progress
   - Never be judgmental or impatient

4. TEACHING STRATEGIES:
   - Use analogies with familiar things (e.g., "Fractions are like sharing a pizza")
   - Incorporate storytelling to explain concepts
   - Ask guiding questions instead of giving immediate answers
   - Use visual descriptions when explaining (e.g., "Imagine a number line...")
   - Repeat important points in different ways

5. SUBJECT-SPECIFIC APPROACHES:
   - MATH: Focus on conceptual understanding before procedures. Use objects and visual models.
   - READING/WRITING: Emphasize phonics, sight words, and simple grammar rules.
   - SCIENCE: Encourage observation and simple experiments with household items.
   - SOCIAL STUDIES: Connect to the child's community and personal experiences.

6. ACCOMMODATE DIFFERENT LEARNING STYLES:
   - Offer multiple explanations (visual, verbal, sequential)
   - Be patient with repetition if needed
   - Check for understanding before moving on

7. ENGAGEMENT:
   - Keep responses concise (3-5 sentences maximum per point)
   - Ask questions to maintain conversation
   - Express enthusiasm for the subject matter
   - Use playful language and occasional appropriate humor

8. HANDLING IMAGES:
   - When a student shares an image of a textbook, homework, or educational material, analyze it
   - Give hints and guidance rather than direct answers
   - Relate the image content to previous learning when possible
   - Encourage the student to think through the problem step by step

Always respond in a warm, encouraging tone. If unsure of the student's exact grade level, tailor the explanation to a slightly simpler level and adjust based on their responses."""

        # Add subject-specific instructions based on the conversation subject
        if subject == "Math":
            subject_content = """
You are a MATH tutor for elementary students. Focus on:
- Building number sense and understanding of place value
- Visual representations of math concepts (counting blocks, number lines)
- Real-world applications of math (measuring ingredients, counting money)
- Step-by-step problem solving with clear explanations
- Multiple ways to solve the same problem
- Making math fun through games and relatable examples

Use simple language, avoid complex math terms without explanation, and always check for understanding before moving on."""
        elif subject == "Reading":
            subject_content = """
You are a READING tutor for elementary students. Focus on:
- Phonics and letter-sound relationships for younger students
- Reading comprehension strategies (predicting, questioning, summarizing)
- Vocabulary development through context clues and word families
- Story elements (characters, setting, plot) for fiction
- Finding main ideas and supporting details for non-fiction
- Encouraging reading fluency and expression

Use encouraging language, suggest age-appropriate books, and make reading enjoyable."""
        elif subject == "Science":
            subject_content = """
You are a SCIENCE tutor for elementary students. Focus on:
- Encouraging curiosity and observation skills
- Explaining natural phenomena in simple terms
- Suggesting simple, safe experiments with household items
- Connecting science concepts to everyday experiences
- Introducing basic scientific method steps (question, predict, test, observe)
- Environmental awareness and appreciation for nature

Make science exciting, use analogies children can understand, and encourage hands-on exploration."""
        elif subject == "Social Studies":
            subject_content = """
You are a SOCIAL STUDIES tutor for elementary students. Focus on:
- Understanding communities and helping others
- Basic geography concepts using familiar landmarks
- Cultural awareness and appreciation for diversity
- Historical events told as engaging stories
- Civic responsibility and community roles
- Making connections between past and present

Use simple maps, timelines, and relatable examples for abstract concepts. Connect social studies to the student's own community experiences."""
        else:  # General
            subject_content = """
You are a general knowledge tutor for elementary students. Be prepared to address any subject with age-appropriate explanations. 
- Adapt your teaching approach based on the specific topic
- Connect different subjects when applicable (like measuring in both math and science)
- Encourage curiosity across all areas of learning
- Help students see connections between school subjects and real life

Be flexible in your teaching approach while maintaining kid-friendly language and explanations."""

        # Combine the base system content with subject-specific content
        system_message = {
            "role": "system", 
            "content": system_content + subject_content
        }
        
        formatted_messages = [system_message]
        for message in messages:
            if message.image_url:
                # For messages with images, include both the text and image URL
                try:
                    # Get the file path from the image URL
                    file_path = None
                    if "/static/" in message.image_url:
                        file_path = "app/static/" + message.image_url.split("/static/", 1)[1]
                    
                    # Convert image to base64 if it's a local file
                    base64_image = None
                    if file_path and os.path.exists(file_path):
                        print(f"Converting image to base64: {file_path}")
                        result = OpenAIService.image_to_base64(file_path)
                        if result:
                            img_data, content_type = result
                            base64_image = f"data:{content_type};base64,{img_data}"
                    
                    if base64_image:
                        # Use base64 data URL
                        formatted_messages.append({
                            "role": message.role,
                            "content": [
                                {"type": "text", "text": message.content},
                                {"type": "image_url", "image_url": {"url": base64_image}}
                            ]
                        })
                        print(f"Added message with base64 image")
                    else:
                        # Fall back to text-only if we can't convert the image
                        formatted_messages.append({"role": message.role, "content": message.content})
                        print(f"Could not convert image to base64, using text-only message")
                except Exception as e:
                    print(f"Error formatting message with image: {e}, falling back to text-only")
                    # Fall back to text-only if there's an issue with the image
                    formatted_messages.append({"role": message.role, "content": message.content})
            else:
                # For text-only messages
                formatted_messages.append({"role": message.role, "content": message.content})
        
        return formatted_messages
    
    @staticmethod
    async def save_audio_file(audio_content: bytes) -> str:
        """Save audio content to a file and return the file path"""
        os.makedirs("app/static/audio", exist_ok=True)
        file_name = f"{uuid.uuid4()}.mp3"
        file_path = f"app/static/audio/{file_name}"
        
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(audio_content)
        
        return file_path
    
    @staticmethod
    async def process_chat(
        db: Session, 
        chat_request: schemas.ChatRequest
    ) -> schemas.ChatResponse:
        try:
            print(f"Processing chat request: {chat_request}")
            
            # Create a new conversation if needed
            conversation_id = chat_request.conversation_id
            if not conversation_id:
                # Create a new conversation
                conversation = await ConversationService.create_conversation(
                    db,
                    schemas.ConversationCreate(
                        user_id=chat_request.user_id,
                        topic="General Chat"
                    )
                )
                conversation_id = conversation.id
                print(f"Created new conversation with ID: {conversation_id}")
            
            # Save user message to database
            user_message = await ConversationService.add_message(
                db,
                schemas.MessageCreate(
                    conversation_id=conversation_id,
                    role="user",
                    content=chat_request.message,
                    image_url=chat_request.image_url
                )
            )
            print(f"Saved user message with ID: {user_message.id}")
            
            # Get conversation history - limit to 15 most recent messages to avoid overwhelming the API
            all_messages = await ConversationService.get_messages(db, conversation_id)
            # Always include the system message and the last 10 messages
            messages = all_messages[-10:] if len(all_messages) > 10 else all_messages
            print(f"Retrieved {len(messages)} recent messages from conversation (total: {len(all_messages)})")
            
            # Check if this is a request to move to the next problem
            is_next_problem_request = False
            message_lower = chat_request.message.lower()
            if any(phrase in message_lower for phrase in ["next problem", "next question", "another problem", "problem 2", "question 2"]):
                is_next_problem_request = True
                print("Detected request for next problem")
            
            # Format messages for OpenAI
            openai_messages = await ConversationService.format_messages_for_openai(messages)
            
            # Try first with full history including images
            ai_response = ""
            try:
                if is_next_problem_request and chat_request.image_url is None:
                    # For next problem requests without a new image, use the most recent image
                    image_messages = [msg for msg in all_messages if msg.image_url]
                    if image_messages:
                        # Get the most recent image message
                        recent_image_message = image_messages[-1]
                        print(f"Using previous image for next problem: {recent_image_message.image_url}")
                        
                        # Analyze the image focusing on the next problem
                        prompt = f"The student has asked for the next problem in this image. Please find the next unsolved problem and provide guidance for that specific problem."
                        
                        image_analysis = await OpenAIService.analyze_image(
                            image_url=recent_image_message.image_url,
                            prompt=prompt
                        )
                        
                        # Use the image analysis as the response
                        ai_response = image_analysis
                    else:
                        # No previous images, just respond to the text
                        ai_response = await OpenAIService.generate_response(openai_messages)
                        ai_response = "I don't see any previous problems to continue with. Can you upload an image with the problems you'd like help with?"
                elif chat_request.image_url:
                    print(f"Image URL detected in request: {chat_request.image_url}")
                    # If this message includes an image, analyze it using GPT-4 Vision
                    try:
                        # Check if the user is asking about a specific problem number
                        problem_number = None
                        
                        # Look for phrases like "problem 1", "question 2", etc.
                        problem_patterns = [
                            r"problem\s+(\d+)",
                            r"question\s+(\d+)",
                            r"exercise\s+(\d+)",
                            r"#\s*(\d+)",
                            r"number\s+(\d+)",
                            r"(\d+)[:\.]"  # Matches "1:", "2.", etc.
                        ]
                        
                        for pattern in problem_patterns:
                            match = re.search(pattern, message_lower)
                            if match:
                                problem_number = int(match.group(1))
                                print(f"Detected request for problem #{problem_number}")
                                break
                        
                        # Construct the prompt based on whether a specific problem was requested
                        if problem_number:
                            prompt = f"This student sent an image with homework problems and is asking about problem #{problem_number}. Please focus ONLY on problem #{problem_number}, identify it in the image, and provide helpful, educational guidance for that specific problem."
                        else:
                            # Check if the message indicates they want help with all problems
                            if any(phrase in message_lower for phrase in ["all problems", "all questions", "everything"]):
                                prompt = f"This student sent an image with homework problems and wants help with all of them. Please identify each problem one by one, and focus ONLY on the FIRST problem for now. Mention that you'll help with one problem at a time, and they can ask about the next problem after understanding this one."
                            else:
                                # Default case - focus on first problem only
                                prompt = f"This student sent an image with the message: '{chat_request.message}'. If this contains multiple problems or questions, please identify the first problem only and provide helpful, educational guidance for just that first problem. Let them know you can help with the other problems one at a time."
                        
                        image_analysis = await OpenAIService.analyze_image(
                            image_url=chat_request.image_url,
                            prompt=prompt
                        )
                        
                        # Add image analysis to the response
                        ai_response = image_analysis
                        print(f"Image analysis successful, response length: {len(ai_response)}")
                    except Exception as e:
                        print(f"Error analyzing image: {e}")
                        import traceback
                        traceback.print_exc()
                        
                        # Fall back to regular chat if image analysis fails
                        ai_response = await OpenAIService.generate_response(openai_messages)
                        ai_response = "I had trouble analyzing your image, but I'll try to help with your question: " + ai_response
                else:
                    # Generate AI response for text-only messages
                    ai_response = await OpenAIService.generate_response(openai_messages)
            except Exception as e:
                print(f"Error with full history: {e}")
                
                # If failed with full history, try with text-only recent messages
                try:
                    print("Falling back to text-only conversation")
                    # Filter out messages with images
                    text_only_messages = [
                        {"role": msg["role"], "content": msg["content"]} 
                        for msg in openai_messages 
                        if not (isinstance(msg.get("content"), list) and 
                              any(isinstance(c, dict) and c.get("type") == "image_url" for c in msg.get("content", [])))
                    ]
                    
                    # Generate response with text-only messages
                    ai_response = await OpenAIService.generate_response(text_only_messages)
                    ai_response = "I had some trouble with our previous image-based conversation, but I can still help with your question: " + ai_response
                except Exception as e2:
                    print(f"Error with text-only fallback: {e2}")
                    ai_response = "I'm having trouble generating a response right now. Could you please try again with your question?"
            
            # Save assistant message to database
            assistant_message = await ConversationService.add_message(
                db,
                schemas.MessageCreate(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=ai_response
                )
            )
            print(f"Saved assistant message with ID: {assistant_message.id}")
            
            # Generate speech from AI response
            try:
                tts_response = await OpenAIService.text_to_speech(ai_response)
                audio_url = tts_response.get("audio_url")
                print(f"Generated speech with URL: {audio_url}")
            except Exception as e:
                print(f"Error generating speech: {e}")
                audio_url = None
            
            # Return response
            return schemas.ChatResponse(
                text=ai_response,
                audio_url=audio_url,
                message={
                    "id": assistant_message.id,
                    "role": assistant_message.role,
                    "content": assistant_message.content,
                    "conversation_id": assistant_message.conversation_id,
                    "timestamp": assistant_message.timestamp.isoformat(),
                    "image_url": user_message.image_url
                }
            )
        except Exception as e:
            print(f"Error in process_chat: {e}")
            import traceback
            traceback.print_exc()
            raise e 