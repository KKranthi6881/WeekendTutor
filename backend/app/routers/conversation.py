from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.schemas import schemas
from app.services.conversation_service import ConversationService
from app.database.database import get_db

router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=schemas.Conversation)
async def create_conversation(conversation: schemas.ConversationCreate, db: Session = Depends(get_db)):
    return await ConversationService.create_conversation(db=db, conversation=conversation)

@router.get("/{conversation_id}", response_model=schemas.Conversation)
async def read_conversation(conversation_id: int, db: Session = Depends(get_db)):
    db_conversation = await ConversationService.get_conversation(db, conversation_id=conversation_id)
    if db_conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return db_conversation

@router.get("/{conversation_id}/messages", response_model=List[schemas.Message])
async def read_conversation_messages(conversation_id: int, db: Session = Depends(get_db)):
    db_conversation = await ConversationService.get_conversation(db, conversation_id=conversation_id)
    if db_conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return await ConversationService.get_messages(db, conversation_id=conversation_id)

@router.post("/messages", response_model=schemas.Message)
async def create_message(message: schemas.MessageCreate, db: Session = Depends(get_db)):
    return await ConversationService.add_message(db=db, message=message) 