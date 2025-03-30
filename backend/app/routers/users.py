from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import os
import json
from pathlib import Path

# Create router
router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

# Define path to users data
USERS_DIR = Path("app/data/users")
USERS_DIR.mkdir(parents=True, exist_ok=True)

# Default user data
DEFAULT_USERS = [
    {
        "id": 1,
        "name": "Student",
        "age": 8,
        "grade": "2nd Grade",
        "created_at": datetime.now().isoformat()
    }
]

# Initialize default user if not exist
def initialize_default_users():
    user_file = USERS_DIR / "users.json"
    if not user_file.exists():
        with open(user_file, "w") as f:
            json.dump(DEFAULT_USERS, f, indent=2)
    return True

# Initialize default users
initialize_default_users()

@router.get("")
async def get_users():
    """
    Get all users
    """
    try:
        user_file = USERS_DIR / "users.json"
        if not user_file.exists():
            # Create and return default users if file doesn't exist
            initialize_default_users()
            return DEFAULT_USERS  # Return array directly, not wrapped in object
        
        with open(user_file, "r") as f:
            users = json.load(f)
        
        return users  # Return array directly, not wrapped in object
        
    except Exception as e:
        print(f"Error getting users: {str(e)}")
        # Return default users if there's an error
        return DEFAULT_USERS  # Return array directly, not wrapped in object

@router.get("/{user_id}")
async def get_user(user_id: int):
    """
    Get a specific user by ID
    """
    try:
        user_file = USERS_DIR / "users.json"
        if not user_file.exists():
            # Create default users if file doesn't exist
            initialize_default_users()
            
            # Return default user if ID matches
            for user in DEFAULT_USERS:
                if user["id"] == user_id:
                    return user
            
            raise HTTPException(status_code=404, detail="User not found")
        
        with open(user_file, "r") as f:
            users = json.load(f)
        
        for user in users:
            if user["id"] == user_id:
                return user
        
        raise HTTPException(status_code=404, detail="User not found")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting user {user_id}: {str(e)}")
        # Try to return default user if ID matches
        for user in DEFAULT_USERS:
            if user["id"] == user_id:
                return user
                
        raise HTTPException(status_code=500, detail=f"Failed to get user: {str(e)}")

@router.post("")
async def create_user(user: Dict[str, Any]):
    """
    Create a new user
    """
    try:
        name = user.get("name", "New User")
        age = user.get("age", 8)
        grade = user.get("grade", "Unknown")
        
        user_file = USERS_DIR / "users.json"
        
        if user_file.exists():
            with open(user_file, "r") as f:
                users = json.load(f)
        else:
            users = DEFAULT_USERS.copy()
        
        # Generate a new ID (max ID + 1)
        new_id = max([u["id"] for u in users], default=0) + 1
        
        # Create new user
        new_user = {
            "id": new_id,
            "name": name,
            "age": age,
            "grade": grade,
            "created_at": datetime.now().isoformat()
        }
        
        # Add to users list
        users.append(new_user)
        
        # Save updated users
        with open(user_file, "w") as f:
            json.dump(users, f, indent=2)
        
        return new_user
        
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

@router.put("/{user_id}")
async def update_user(user_id: int, user_data: Dict[str, Any]):
    """
    Update an existing user
    """
    try:
        user_file = USERS_DIR / "users.json"
        
        if not user_file.exists():
            initialize_default_users()
            with open(user_file, "r") as f:
                users = json.load(f)
        else:
            with open(user_file, "r") as f:
                users = json.load(f)
        
        # Find user by ID
        user_found = False
        for i, user in enumerate(users):
            if user["id"] == user_id:
                # Update user fields
                for key, value in user_data.items():
                    if key != "id":  # Don't update the ID field
                        users[i][key] = value
                
                user_found = True
                updated_user = users[i]
                break
        
        if not user_found:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Save updated users
        with open(user_file, "w") as f:
            json.dump(users, f, indent=2)
        
        return updated_user
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")

@router.delete("/{user_id}")
async def delete_user(user_id: int):
    """
    Delete a user by ID
    """
    try:
        user_file = USERS_DIR / "users.json"
        
        if not user_file.exists():
            raise HTTPException(status_code=404, detail="User not found")
        
        with open(user_file, "r") as f:
            users = json.load(f)
        
        # Find user by ID
        user_found = False
        filtered_users = []
        for user in users:
            if user["id"] != user_id:
                filtered_users.append(user)
            else:
                user_found = True
        
        if not user_found:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Save updated users
        with open(user_file, "w") as f:
            json.dump(filtered_users, f, indent=2)
        
        return {"success": True, "message": "User deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}") 