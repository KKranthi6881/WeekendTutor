const { Configuration, OpenAIApi } = require('openai');

// Set up OpenAI configuration
const configuration = new Configuration({
  apiKey: process.env.OPENAI_API_KEY,
});
const openai = new OpenAIApi(configuration);

/**
 * Analyzes a student's response to determine correctness and confusion
 * Returns feedback that focuses on guiding the student rather than giving answers
 */
exports.analyzeStudentResponse = async (req, res) => {
  try {
    const { 
      studentResponse, 
      context, 
      subject, 
      currentStep, 
      totalSteps 
    } = req.body;
    
    if (!studentResponse || !context) {
      return res.status(400).json({
        success: false,
        message: 'Student response and context are required'
      });
    }
    
    // Create a system prompt that focuses on providing hints
    const systemPrompt = `
      You are an AI educational assistant analyzing a student's response.
      
      IMPORTANT: Never provide direct answers to educational problems. Instead, provide hints and guidance.
      
      The student is working on step ${currentStep} of ${totalSteps} in a ${subject} problem.
      
      The context of this step is: "${context}"
      
      Analyze their response based on:
      1. Correctness (is the student on the right track?)
      2. Confusion level (how confused do they seem, on a scale of 0-10?)
      3. Any specific misconceptions
      
      Return your analysis as structured feedback that:
      - Encourages what they did right
      - Offers a HINT (not the answer) for areas of confusion
      - Asks a guiding question to help them reach the next step themselves
      
      Remember: Your goal is to help them learn and think for themselves, not to solve the problem for them.
    `;
    
    // Call GPT for the analysis
    const response = await openai.createChatCompletion({
      model: "gpt-4",
      messages: [
        {
          role: "system",
          content: systemPrompt
        },
        {
          role: "user",
          content: `Student's response: "${studentResponse}"`
        }
      ],
      temperature: 0.7,
      max_tokens: 500,
      function_call: { name: "analyze_student_response" },
      functions: [
        {
          name: "analyze_student_response",
          description: "Analyze a student's response to determine correctness and confusion level",
          parameters: {
            type: "object",
            properties: {
              is_correct: {
                type: "boolean",
                description: "Whether the student's response is mostly correct or on the right track"
              },
              confusion_level: {
                type: "integer",
                description: "The level of confusion detected in the student's response, from 0 (not confused) to 10 (very confused)"
              },
              misconceptions: {
                type: "array",
                items: {
                  type: "string"
                },
                description: "Any misconceptions detected in the student's response"
              },
              feedback: {
                type: "string",
                description: "Educational feedback with hints (not answers) to guide the student"
              }
            },
            required: ["is_correct", "confusion_level", "feedback"]
          }
        }
      ]
    });
    
    let analysisResult;
    
    // Parse the function call response
    if (response.data.choices[0].message.function_call) {
      const functionCallResult = JSON.parse(
        response.data.choices[0].message.function_call.arguments
      );
      analysisResult = functionCallResult;
    } else {
      // Fallback if function calling isn't available
      const analysisText = response.data.choices[0].message.content;
      const isCorrectMatch = analysisText.match(/correct:\s*(true|false)/i);
      const confusionMatch = analysisText.match(/confusion:\s*(\d+)/i);
      
      analysisResult = {
        is_correct: isCorrectMatch ? isCorrectMatch[1].toLowerCase() === 'true' : false,
        confusion_level: confusionMatch ? parseInt(confusionMatch[1]) : 5,
        feedback: analysisText
      };
    }
    
    return res.status(200).json({
      success: true,
      ...analysisResult
    });
    
  } catch (error) {
    console.error('Error analyzing student response:', error);
    return res.status(500).json({
      success: false,
      message: 'Error analyzing student response',
      error: error.message
    });
  }
};

/**
 * Processes a learning response and provides hints rather than answers
 */
exports.processLearningResponse = async (req, res) => {
  try {
    const { 
      message, 
      user_query, 
      subject, 
      current_step, 
      total_steps, 
      context,
      response_type = 'hint'
    } = req.body;
    
    if (!message || !subject) {
      return res.status(400).json({
        success: false,
        message: 'Student message and subject are required'
      });
    }
    
    // Determine if this is the final step
    const isFinalStep = current_step >= total_steps;
    
    // Create a system prompt based on the response type
    let systemPrompt;
    
    switch (response_type) {
      case 'hint':
        systemPrompt = `
          You are an AI tutor helping a student with a ${subject} problem.
          
          The student is on step ${current_step} of ${total_steps}.
          
          Current context: "${context}"
          
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
        `;
        break;
        
      case 'clarification':
        systemPrompt = `
          You are an AI tutor helping a confused student with a ${subject} problem.
          
          The student is on step ${current_step} of ${total_steps} and seems confused.
          
          Current context: "${context}"
          
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
        `;
        break;
        
      case 'encouragement':
        systemPrompt = `
          You are an AI tutor celebrating a student's progress with a ${subject} problem.
          
          The student is on step ${current_step} of ${total_steps} and has provided a good answer.
          
          Current context: "${context}"
          
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
        `;
        break;
        
      default:
        systemPrompt = `
          You are an AI tutor helping a student with a ${subject} problem.
          
          The student is on step ${current_step} of ${total_steps}.
          
          Current context: "${context}"
          
          Provide guidance that helps them learn, but never give direct answers.
        `;
    }
    
    // Add instructions for final step if applicable
    if (isFinalStep) {
      systemPrompt += `
        This is the FINAL STEP in the learning process.
        
        In addition to your regular guidance:
        1. Summarize what they've learned through this process
        2. Celebrate their accomplishment
        3. Suggest how they might apply this knowledge
        4. End with a positive, encouraging note
      `;
    }
    
    // Call GPT for the response
    const response = await openai.createChatCompletion({
      model: "gpt-4",
      messages: [
        {
          role: "system",
          content: systemPrompt
        },
        {
          role: "user",
          content: `Original question: "${user_query}"\n\nStudent's message: "${message}"`
        }
      ],
      temperature: 0.7,
      max_tokens: 500
    });
    
    const responseText = response.data.choices[0].message.content;
    
    // Generate a new learning context that includes this interaction
    const updatedContext = `${context}\n\nStudent: ${message}\n\nTutor: ${responseText}`;
    
    return res.status(200).json({
      success: true,
      next_step: responseText,
      is_final_step: isFinalStep,
      context: updatedContext
    });
    
  } catch (error) {
    console.error('Error processing learning response:', error);
    return res.status(500).json({
      success: false,
      message: 'Error processing learning response',
      error: error.message
    });
  }
};
