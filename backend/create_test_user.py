from sqlalchemy.orm import Session
import os
import sys
import datetime

# Add the parent directory to sys.path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import SessionLocal, engine, Base
from app.models.models import User, Conversation, Message

def create_test_data():
    db = SessionLocal()
    try:
        # Create test user
        user = User(
            name="Test User",
            age=10,
            grade="5th Grade",
            created_at=datetime.datetime.now()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Created user: {user.name} (ID: {user.id})")
        
        # Create test conversation
        conversation = Conversation(
            user_id=user.id, 
            topic="Test Conversation", 
            subject="Math",
            created_at=datetime.datetime.now()
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        print(f"Created conversation: {conversation.topic} (ID: {conversation.id})")
        
        # Add a test message
        user_message = Message(
            conversation_id=conversation.id,
            content="Hello, I need help with math.",
            role="user",
            timestamp=datetime.datetime.now()
        )
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
        print(f"Added message: {user_message.content}")
        
        # Add a response message
        assistant_message = Message(
            conversation_id=conversation.id,
            content="Hi there! I'd be happy to help you with math. What specific topic or problem are you working on?",
            role="assistant",
            timestamp=datetime.datetime.now()
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)
        print(f"Added response: {assistant_message.content}")
        
    finally:
        db.close()

if __name__ == "__main__":
    # Create all tables first
    Base.metadata.create_all(bind=engine)
    create_test_data()
    print("Test data created successfully!") 