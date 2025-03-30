from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import os
import uuid
import aiofiles

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
        
        # Save user message to database
        user_message = await ConversationService.add_message(
            db,
            schemas.MessageCreate(
                conversation_id=conversation_id,
                role="user",
                content=chat_request.message
            )
        )
        
        # Get conversation history
        messages = await ConversationService.get_messages(db, conversation_id)
        
        # Format messages for OpenAI
        openai_messages = await ConversationService.format_messages_for_openai(messages)
        
        # Generate AI response
        ai_response = await OpenAIService.generate_response(openai_messages)
        
        # Save assistant message to database
        assistant_message = await ConversationService.add_message(
            db,
            schemas.MessageCreate(
                conversation_id=conversation_id,
                role="assistant",
                content=ai_response
            )
        )
        
        # Generate speech from AI response
        tts_response = await OpenAIService.text_to_speech(ai_response)
        
        # Return response
        return schemas.ChatResponse(
            text=ai_response,
            audio_url=tts_response.get("audio_url"),
            message={
                "id": assistant_message.id,
                "role": assistant_message.role,
                "content": assistant_message.content,
                "conversation_id": assistant_message.conversation_id,
                "timestamp": assistant_message.timestamp.isoformat()
            }
        ) 