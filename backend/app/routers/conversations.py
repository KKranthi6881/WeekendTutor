from fastapi import APIRouter, HTTPException, Depends, Request, Body
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import os
import json
from pathlib import Path

# Create router
router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
    responses={404: {"description": "Not found"}},
)

# Define paths
CONVERSATIONS_DIR = Path("app/data/conversations")
CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)

@router.get("")
async def get_conversations(user_id: Optional[int] = None):
    """
    Get a list of all conversations, optionally filtered by user_id
    """
    conversations = []
    
    for file in CONVERSATIONS_DIR.glob("*.json"):
        try:
            with open(file, "r") as f:
                conv_data = json.load(f)
                # Add the filename as the id
                conv_data["id"] = int(file.stem) if file.stem.isdigit() else file.stem
                
                # Only include conversations for the specified user if user_id is provided
                if user_id is None or conv_data.get("user_id") == user_id:
                    conversations.append(conv_data)
        except Exception as e:
            print(f"Error reading conversation file {file}: {str(e)}")
    
    # Sort by date descending
    conversations.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    # Return the conversations array directly, not wrapped in an object
    return conversations

@router.post("")
async def create_conversation(data: Dict[str, Any] = Body(...)):
    """
    Create a new conversation
    """
    try:
        topic = data.get("topic", "New Conversation")
        user_id = data.get("user_id")
        subject = data.get("subject", "General")
        initial_message = data.get("initial_message", "")
        
        if user_id is None:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        # Generate a unique ID
        conversation_id = len(list(CONVERSATIONS_DIR.glob("*.json"))) + 1
        
        # Create conversation data
        conversation_data = {
            "topic": topic,
            "user_id": user_id,
            "subject": subject,
            "created_at": datetime.now().isoformat(),
            "timestamp": datetime.now().isoformat(),
            "messages": []
        }
        
        # Add initial message if provided
        if initial_message:
            conversation_data["messages"].append({
                "role": "user",
                "content": initial_message,
                "timestamp": datetime.now().isoformat()
            })
        
        # Save to file
        conversation_file = CONVERSATIONS_DIR / f"{conversation_id}.json"
        with open(conversation_file, "w") as f:
            json.dump(conversation_data, f, indent=2)
        
        # Return the data along with the ID
        return {
            "id": conversation_id,
            **conversation_data
        }
        
    except Exception as e:
        print(f"Error creating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")

@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    Get a specific conversation by ID
    """
    try:
        conversation_file = CONVERSATIONS_DIR / f"{conversation_id}.json"
        
        if not conversation_file.exists():
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        with open(conversation_file, "r") as f:
            data = json.load(f)
            
        # Add the ID to the response
        data["id"] = int(conversation_id) if conversation_id.isdigit() else conversation_id
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting conversation {conversation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")

@router.post("/{conversation_id}/messages")
async def add_message(
    conversation_id: str,
    data: Dict[str, Any] = Body(...)
):
    """
    Add a new message to a conversation
    """
    try:
        conversation_file = CONVERSATIONS_DIR / f"{conversation_id}.json"
        
        if not conversation_file.exists():
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Load existing conversation
        with open(conversation_file, "r") as f:
            conversation = json.load(f)
        
        # Validate message data
        role = data.get("role")
        content = data.get("content")
        
        if not role or not content:
            raise HTTPException(status_code=400, detail="Role and content are required")
        
        if role not in ["user", "assistant"]:
            raise HTTPException(status_code=400, detail="Role must be 'user' or 'assistant'")
        
        # Create new message
        new_message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add audio_url if provided
        if data.get("audio_url"):
            new_message["audio_url"] = data.get("audio_url")
        
        # Add to messages list
        if "messages" not in conversation:
            conversation["messages"] = []
            
        conversation["messages"].append(new_message)
        
        # Update timestamp
        conversation["timestamp"] = datetime.now().isoformat()
        
        # Save updated conversation
        with open(conversation_file, "w") as f:
            json.dump(conversation, f, indent=2)
        
        # Return the updated conversation
        conversation["id"] = int(conversation_id) if conversation_id.isdigit() else conversation_id
        return conversation
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error adding message to conversation {conversation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add message: {str(e)}")

@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation by ID
    """
    try:
        conversation_file = CONVERSATIONS_DIR / f"{conversation_id}.json"
        
        if not conversation_file.exists():
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Delete the file
        conversation_file.unlink()
        
        return {"success": True, "message": "Conversation deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting conversation {conversation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}") 