from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import os
import json
from pathlib import Path

# Create router
router = APIRouter(
    prefix="/messages",
    tags=["messages"],
    responses={404: {"description": "Not found"}},
)

# Define paths
CONVERSATIONS_DIR = Path("app/data/conversations")
CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)

@router.get("")
async def get_messages(conversation_id: Optional[int] = None):
    """
    Get all messages for a conversation
    """
    if conversation_id is None:
        raise HTTPException(status_code=400, detail="conversation_id is required")
    
    try:
        conversation_file = CONVERSATIONS_DIR / f"{conversation_id}.json"
        
        if not conversation_file.exists():
            return []
        
        with open(conversation_file, "r") as f:
            conversation = json.load(f)
        
        # Extract messages from the conversation
        messages = conversation.get("messages", [])
        
        # Return messages array directly
        return messages
    except Exception as e:
        print(f"Error getting messages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")

@router.post("")
async def create_message(message_data: Dict[str, Any] = Body(...)):
    """
    Create a new message in a conversation
    """
    conversation_id = message_data.get("conversation_id")
    content = message_data.get("content")
    role = message_data.get("role", "user")
    
    if not conversation_id:
        raise HTTPException(status_code=400, detail="conversation_id is required")
    
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    
    try:
        conversation_file = CONVERSATIONS_DIR / f"{conversation_id}.json"
        
        if not conversation_file.exists():
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Load conversation
        with open(conversation_file, "r") as f:
            conversation = json.load(f)
        
        # Create new message
        new_message = {
            "id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "content": content,
            "role": role,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add audio_url if provided
        if message_data.get("audio_url"):
            new_message["audio_url"] = message_data.get("audio_url")
        
        # Add to messages list
        if "messages" not in conversation:
            conversation["messages"] = []
        
        conversation["messages"].append(new_message)
        
        # Update timestamp
        conversation["timestamp"] = datetime.now().isoformat()
        
        # Save updated conversation
        with open(conversation_file, "w") as f:
            json.dump(conversation, f, indent=2)
        
        return new_message
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create message: {str(e)}")

@router.get("/{message_id}")
async def get_message(message_id: str, conversation_id: Optional[int] = None):
    """
    Get a specific message by ID
    """
    try:
        # If conversation_id is provided, only search in that conversation
        if conversation_id is not None:
            conversation_file = CONVERSATIONS_DIR / f"{conversation_id}.json"
            
            if not conversation_file.exists():
                raise HTTPException(status_code=404, detail="Conversation not found")
            
            with open(conversation_file, "r") as f:
                conversation = json.load(f)
            
            for message in conversation.get("messages", []):
                if message.get("id") == message_id:
                    return message
            
            raise HTTPException(status_code=404, detail="Message not found")
        
        # If no conversation_id, search in all conversations
        for file in CONVERSATIONS_DIR.glob("*.json"):
            try:
                with open(file, "r") as f:
                    conversation = json.load(f)
                
                for message in conversation.get("messages", []):
                    if message.get("id") == message_id:
                        return message
            except:
                continue
        
        raise HTTPException(status_code=404, detail="Message not found")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting message {message_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get message: {str(e)}")

@router.delete("/{message_id}")
async def delete_message(message_id: str, conversation_id: int):
    """
    Delete a message by ID
    """
    if not conversation_id:
        raise HTTPException(status_code=400, detail="conversation_id is required")
    
    try:
        conversation_file = CONVERSATIONS_DIR / f"{conversation_id}.json"
        
        if not conversation_file.exists():
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Load conversation
        with open(conversation_file, "r") as f:
            conversation = json.load(f)
        
        # Find and remove message
        found = False
        messages = []
        for message in conversation.get("messages", []):
            if message.get("id") != message_id:
                messages.append(message)
            else:
                found = True
        
        if not found:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Update messages list
        conversation["messages"] = messages
        
        # Update timestamp
        conversation["timestamp"] = datetime.now().isoformat()
        
        # Save updated conversation
        with open(conversation_file, "w") as f:
            json.dump(conversation, f, indent=2)
        
        return {"success": True, "message": "Message deleted"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting message {message_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete message: {str(e)}") 