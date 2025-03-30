# AI Voice Tutor

A voice-powered AI tutoring application for elementary school students, featuring natural conversations, text-to-speech, and speech-to-text capabilities.

## Features

- User profiles for elementary students
- Voice interaction with AI tutor using OpenAI
- Audio responses with text-to-speech
- Conversation history
- Custom teaching approach for elementary students

## Technology Stack

- **Frontend**: React with TypeScript
- **Backend**: FastAPI (Python)
- **Database**: SQLite
- **AI Services**: OpenAI GPT-4, Whisper API for speech-to-text, TTS API for text-to-speech

## Getting Started

### Prerequisites

- Node.js and npm
- Python 3.8+ with pip
- OpenAI API key

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/AIVoiceAgent.git
   cd AIVoiceAgent
   ```

2. Set up the backend:
   ```
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   export OPENAI_API_KEY="your-api-key-here"  # On Windows: set OPENAI_API_KEY=your-api-key-here
   ```

3. Set up the frontend:
   ```
   cd ../frontend
   npm install
   ```

### Running the Application

1. Start the backend server:
   ```
   cd backend
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   python run.py
   ```
   The API will be available at http://localhost:8000

2. Start the frontend development server:
   ```
   cd frontend
   npm start
   ```
   The application will be available at http://localhost:3000

## Usage

1. Create a user profile or select an existing one
2. Start a new conversation
3. Type or speak your questions or topics
4. The AI tutor will respond with voice and text 