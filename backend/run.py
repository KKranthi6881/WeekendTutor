import uvicorn
import os
from check_folders import create_required_folders

# Set a default API key for development
if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "your-openai-api-key-here"  # Replace with actual key in production

# Ensure all required folders exist
create_required_folders()

# Run the application
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 