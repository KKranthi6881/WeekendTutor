from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    name: str
    age: int
    grade: str

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Message schemas
class MessageBase(BaseModel):
    role: str
    content: str

class MessageCreate(MessageBase):
    conversation_id: int

class Message(MessageBase):
    id: int
    conversation_id: int
    timestamp: datetime
    
    class Config:
        from_attributes = True

# Conversation schemas
class ConversationBase(BaseModel):
    topic: str
    subject: Optional[str] = "General"  # Options: "Math", "Reading", "Science", "Social Studies", "General"

class ConversationCreate(ConversationBase):
    user_id: int

class Conversation(ConversationBase):
    id: int
    user_id: int
    created_at: datetime
    messages: List[Message] = []
    
    class Config:
        from_attributes = True

# Chat request/response schemas
class ChatRequest(BaseModel):
    message: str
    user_id: int
    conversation_id: Optional[int] = None
    
class ChatResponse(BaseModel):
    text: str
    audio_url: Optional[str] = None
    message: Optional[dict] = None
    
class TranscriptionRequest(BaseModel):
    audio_file_path: str
    
class TranscriptionResponse(BaseModel):
    text: str 