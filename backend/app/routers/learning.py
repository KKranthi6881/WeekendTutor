from fastapi import APIRouter, HTTPException, Request
from typing import Optional, List, Dict, Any
import os
import openai
import json

# Create router
router = APIRouter(
    prefix="/learning",
    tags=["learning"],
    responses={404: {"description": "Not found"}},
)

# Ensure OpenAI API key is set
if "OPENAI_API_KEY" not in os.environ:
    # Use a default key for development or read from config
    os.environ["OPENAI_API_KEY"] = "your-openai-api-key-here"  # Replace with actual key in production

@router.post("/analyze")
async def analyze_student_response(data: Dict[str, Any]):
    """
    Analyze a student's response to determine correctness and confusion
    Returns feedback that focuses on providing hints rather than direct answers
    """
    try:
        student_response = data.get("studentResponse")
        context = data.get("context")
        subject = data.get("subject", "General")
        current_step = data.get("currentStep", 1)
        total_steps = data.get("totalSteps", 1)
        
        if not student_response or not context:
            raise HTTPException(status_code=400, detail="Student response and context are required")
        
        # Create a system prompt that focuses on providing hints
        system_prompt = f"""
        You are an AI educational assistant analyzing a student's response.
        
        IMPORTANT: Never provide direct answers to educational problems. Instead, provide hints and guidance.
        
        The student is working on step {current_step} of {total_steps} in a {subject} problem.
        
        The context of this step is: "{context}"
        
        Analyze their response based on:
        1. Correctness (is the student on the right track?)
        2. Confusion level (how confused do they seem, on a scale of 0-10?)
        3. Any specific misconceptions
        
        Return your analysis as JSON with the following structure:
        {{
            "is_correct": true/false,
            "confusion_level": number 0-10,
            "misconceptions": ["misconception 1", "misconception 2"],
            "feedback": "Educational feedback with hints (not answers)"
        }}
        
        Remember: Your goal is to help them learn and think for themselves, not to solve the problem for them.
        """
        
        # Call OpenAI for the analysis
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Student's response: \"{student_response}\""}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        # Parse the response
        response_text = completion.choices[0].message.content
        
        # Try to extract JSON from the response
        try:
            # First try to parse directly if it's valid JSON
            analysis_result = json.loads(response_text)
        except json.JSONDecodeError:
            # If not valid JSON, try to extract JSON part from text
            import re
            json_match = re.search(r'({.*})', response_text.replace('\n', ' '), re.DOTALL)
            if json_match:
                try:
                    analysis_result = json.loads(json_match.group(1))
                except:
                    # Fallback to manual parsing
                    analysis_result = {
                        "is_correct": "true" in response_text.lower() and "is_correct" in response_text.lower(),
                        "confusion_level": 5,  # Default mid-level confusion
                        "feedback": response_text
                    }
            else:
                # Could not extract JSON, create basic structure
                analysis_result = {
                    "is_correct": "true" in response_text.lower() and "is_correct" in response_text.lower(),
                    "confusion_level": 5,
                    "feedback": response_text
                }
        
        # Ensure all keys exist
        if "is_correct" not in analysis_result:
            analysis_result["is_correct"] = False
        if "confusion_level" not in analysis_result:
            analysis_result["confusion_level"] = 5
        if "feedback" not in analysis_result:
            analysis_result["feedback"] = response_text
        
        return analysis_result
        
    except Exception as e:
        print(f"Error analyzing student response: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing response: {str(e)}")

@router.post("/process")
async def process_learning_response(request: Request, data: Dict[str, Any]):
    """
    Process a learning response and provide hints rather than direct answers
    """
    try:
        message = data.get("message")
        user_query = data.get("user_query")
        subject = data.get("subject", "General")
        current_step = data.get("current_step", 1)
        total_steps = data.get("total_steps", 1)
        context = data.get("context", "")
        response_type = data.get("response_type", "hint")
        
        if not message:
            raise HTTPException(status_code=400, detail="Student message is required")
        
        # Determine if this is the final step
        is_final_step = current_step >= total_steps
        
        # Create a system prompt based on the response type
        if response_type == "hint":
            system_prompt = f"""
            You are an AI tutor helping a student with a {subject} problem.
            
            The student is on step {current_step} of {total_steps}.
            
            Current context: "{context}"
            
            The student has responded and needs a HINT to move forward. Do NOT give them the answer!
            
            Your response should:
            1. Acknowledge their answer with specific encouragement
            2. Provide a gentle hint that guides them in the right direction
            3. Ask a thought-provoking question that helps them discover the next step themselves
            4. Use age-appropriate language and examples
            
            Important guidelines:
            - NEVER solve the problem for them
            - Focus on process and thinking skills
            - Build confidence through guided discovery
            - Keep your response friendly, encouraging, and concise
            """
        elif response_type == "clarification":
            system_prompt = f"""
            You are an AI tutor helping a confused student with a {subject} problem.
            
            The student is on step {current_step} of {total_steps} and seems confused.
            
            Current context: "{context}"
            
            Your response should:
            1. Reassure them that confusion is part of learning
            2. Clarify the concept they're struggling with using simple examples
            3. Break down the step into smaller, more manageable parts
            4. Provide a structured approach to help them get unstuck
            
            Important guidelines:
            - Use very clear, simple language
            - Explain concepts in multiple ways
            - Use metaphors or visual examples when possible
            - Keep your response patient, kind, and supportive
            """
        elif response_type == "encouragement":
            system_prompt = f"""
            You are an AI tutor celebrating a student's progress with a {subject} problem.
            
            The student is on step {current_step} of {total_steps} and has provided a good answer.
            
            Current context: "{context}"
            
            Your response should:
            1. Provide specific praise for what they did well
            2. Reinforce the concept they just demonstrated
            3. Connect this knowledge to the bigger picture
            4. Present the next challenge with enthusiasm
            
            Important guidelines:
            - Be genuinely excited about their progress
            - Highlight specific aspects of their thinking that were effective
            - Build momentum and curiosity for the next step
            - Keep your response upbeat and motivating
            """
        else:
            system_prompt = f"""
            You are an AI tutor helping a student with a {subject} problem.
            
            The student is on step {current_step} of {total_steps}.
            
            Current context: "{context}"
            
            Provide guidance that helps them learn, but never give direct answers.
            """
        
        # Add instructions for final step if applicable
        if is_final_step:
            system_prompt += """
            This is the FINAL STEP in the learning process.
            
            In addition to your regular guidance:
            1. Summarize what they've learned through this process
            2. Celebrate their accomplishment
            3. Suggest how they might apply this knowledge
            4. End with a positive, encouraging note
            """
        
        # Call OpenAI for the response
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Original question: \"{user_query}\"\n\nStudent's message: \"{message}\""}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        response_text = completion.choices[0].message.content
        
        # Generate audio for the response
        audio_response = openai.Audio.create(
            model="tts-1",
            voice="alloy",
            input=response_text
        )
        
        # Save audio file
        import uuid
        from pathlib import Path
        
        audio_filename = f"response-{uuid.uuid4().hex}.mp3"
        audio_dir = Path("app/static/audio")
        audio_dir.mkdir(parents=True, exist_ok=True)
        
        audio_path = audio_dir / audio_filename
        with open(audio_path, "wb") as f:
            f.write(audio_response.content)
        
        # Generate audio URL
        base_url = str(request.base_url).rstrip('/')
        audio_url = f"{base_url}/static/audio/{audio_filename}"
        
        # Generate a new learning context that includes this interaction
        updated_context = f"{context}\n\nStudent: {message}\n\nTutor: {response_text}"
        
        return {
            "success": True,
            "next_step": response_text,
            "is_final_step": is_final_step,
            "context": updated_context,
            "audio_url": audio_url
        }
        
    except Exception as e:
        print(f"Error processing learning response: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing response: {str(e)}")

@router.post("/start")
async def start_interactive_learning(data: Dict[str, Any]):
    """
    Start an interactive learning session based on a query and subject
    """
    try:
        query = data.get("query")
        subject = data.get("subject", "General")
        grade_level = data.get("grade_level", 3)
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Create a system prompt to generate an interactive learning plan
        system_prompt = f"""
        You are an educational AI tutor designing an interactive learning experience for a {grade_level}th grade student.
        
        The student wants to learn about: "{query}" in the subject of {subject}.
        
        Create an interactive learning plan with 3-5 steps.
        For each step, focus on having the student actively engage with the concepts.
        
        IMPORTANT: Never provide direct answers to problems. Instead, guide the student through discovery.
        
        Format your response as a single paragraph with a brief explanation of the first learning step.
        This should give the student enough information to start working on the task, but not complete answers.
        
        Keep your language child-friendly, engaging, and encouraging.
        """
        
        # Call OpenAI to create the learning plan
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Help me learn about: {query}"}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        first_step = completion.choices[0].message.content
        
        # Create a separate completion to determine number of total steps
        steps_completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You only respond with a number representing how many steps would be appropriate for this learning task, between 3 and 5."},
                {"role": "user", "content": f"How many interactive learning steps would be appropriate for a {grade_level}th grade student to learn about '{query}' in the subject of {subject}?"}
            ],
            temperature=0.3,
            max_tokens=10
        )
        
        total_steps_text = steps_completion.choices[0].message.content
        import re
        steps_match = re.search(r'\d+', total_steps_text)
        total_steps = int(steps_match.group()) if steps_match else 3
        
        # Generate audio for the first step
        audio_response = openai.Audio.create(
            model="tts-1",
            voice="alloy",
            input=first_step
        )
        
        # Save audio file
        import uuid
        from pathlib import Path
        
        audio_filename = f"start-learning-{uuid.uuid4().hex}.mp3"
        audio_dir = Path("app/static/audio")
        audio_dir.mkdir(parents=True, exist_ok=True)
        
        audio_path = audio_dir / audio_filename
        with open(audio_path, "wb") as f:
            f.write(audio_response.content)
        
        # Generate audio URL
        base_url = str(request.url_for("root")).rstrip('/')
        audio_url = f"{base_url}/static/audio/{audio_filename}"
        
        return {
            "success": True,
            "first_step": first_step,
            "total_steps": total_steps,
            "audio_url": audio_url
        }
        
    except Exception as e:
        print(f"Error starting interactive learning: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error starting learning: {str(e)}") 