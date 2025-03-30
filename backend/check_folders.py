#!/usr/bin/env python
import os

def create_required_folders():
    """Create all the required folders for the application."""
    folders = [
        "app/static",
        "app/static/audio",
        "app/static/uploads",
        "app/static/uploads/images",
        "app/data",
        "app/data/conversations",
        "app/data/users",
    ]
    
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        print(f"Ensured folder exists: {folder}")

if __name__ == "__main__":
    create_required_folders()
    print("All required folders have been created.") 