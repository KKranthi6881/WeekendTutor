const path = require('path');
const fs = require('fs');
const multer = require('multer');
const { Configuration, OpenAIApi } = require('openai');

// Set up OpenAI configuration
const configuration = new Configuration({
  apiKey: process.env.OPENAI_API_KEY,
});
const openai = new OpenAIApi(configuration);

// Configure multer for image uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadDir = path.join(__dirname, '../uploads/images');
    // Create directory if it doesn't exist
    if (!fs.existsSync(uploadDir)) {
      fs.mkdirSync(uploadDir, { recursive: true });
    }
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    cb(null, uniqueSuffix + path.extname(file.originalname));
  }
});

// File filter for images
const fileFilter = (req, file, cb) => {
  if (file.mimetype.startsWith('image/')) {
    cb(null, true);
  } else {
    cb(new Error('Only image files are allowed!'), false);
  }
};

// Initialize upload middleware
const upload = multer({ 
  storage: storage,
  fileFilter: fileFilter,
  limits: {
    fileSize: 5 * 1024 * 1024 // 5MB limit
  }
});

// Helper to get base URL
const getBaseUrl = (req) => {
  return `${req.protocol}://${req.get('host')}`;
};

// Upload image controller
exports.uploadImage = (req, res) => {
  const uploadSingle = upload.single('image');
  
  uploadSingle(req, res, async (err) => {
    if (err) {
      return res.status(400).json({ 
        success: false, 
        message: err.message 
      });
    }
    
    // If no file uploaded
    if (!req.file) {
      return res.status(400).json({ 
        success: false, 
        message: 'Please upload an image file'
      });
    }
    
    // Generate relative URL path
    const relativePath = '/uploads/images/' + req.file.filename;
    const baseUrl = getBaseUrl(req);
    const imageUrl = baseUrl + relativePath;
    
    return res.status(200).json({
      success: true,
      image_url: imageUrl,
      message: 'Image uploaded successfully'
    });
  });
};

// Analyze uploaded image
exports.analyzeImage = async (req, res) => {
  try {
    const { image_url, conversation_id } = req.body;
    
    if (!image_url) {
      return res.status(400).json({ 
        success: false, 
        message: 'Image URL is required' 
      });
    }
    
    // Create a context prompt that guides the AI to give educational hints rather than direct answers
    const contextPrompt = `
      You are an educational AI tutor for children. A student has uploaded an image.
      
      Identify what's in the image and determine if it's educational content like:
      1. A math problem
      2. A science question
      3. A reading/writing task
      4. Other educational content
      
      If it's educational content:
      - DON'T solve the problem directly
      - Provide educational guidance and hints that help the student learn
      - Break down the process into steps they can follow
      - Use age-appropriate language
      - Ask questions to prompt their thinking
      
      If it's not clearly educational content:
      - Just describe what you see and ask if they need help with anything specific
      
      Format your response to be engaging and encouraging.
    `;
    
    // Call OpenAI's GPT-4 Vision model
    const response = await openai.createChatCompletion({
      model: "gpt-4-vision-preview",
      messages: [
        {
          role: "system",
          content: contextPrompt
        },
        {
          role: "user",
          content: [
            { type: "text", text: "What's in this image?" },
            { type: "image_url", image_url: { url: image_url } }
          ]
        }
      ],
      max_tokens: 500
    });
    
    const analysis = response.data.choices[0].message.content;
    
    // Detect if this seems like educational content to set up tutorial mode
    const educationalContentPatterns = [
      /math problem/i, 
      /equation/i, 
      /science question/i, 
      /experiment/i,
      /read(ing)?/i, 
      /writ(ing|e)/i,
      /homework/i,
      /problem to solve/i,
      /steps to follow/i
    ];
    
    const shouldEnterTutorialMode = educationalContentPatterns.some(pattern => 
      pattern.test(analysis)
    );
    
    // If it's educational content, create learning steps
    let learningSteps = [];
    if (shouldEnterTutorialMode) {
      // Call GPT again to generate appropriate learning steps based on the image
      const stepsResponse = await openai.createChatCompletion({
        model: "gpt-4",
        messages: [
          {
            role: "system",
            content: "You are an educational assistant creating step-by-step guidance for a child. Never provide direct answers, only hints and educational guidance."
          },
          {
            role: "user",
            content: `Based on this analysis of an educational image, create 3-5 interactive learning steps that guide the child to solve it themselves: "${analysis}"`
          }
        ],
        max_tokens: 500
      });
      
      const stepsText = stepsResponse.data.choices[0].message.content;
      
      // Extract steps from response
      const stepMatches = stepsText.match(/\d+\.\s+[^\n]+/g);
      if (stepMatches) {
        learningSteps = stepMatches.map(step => step.trim());
      } else {
        // Fallback if regex doesn't find steps
        learningSteps = stepsText.split('\n')
          .filter(line => line.trim().length > 0)
          .slice(0, 5);
      }
    }
    
    // Generate audio for the response
    const audioResponse = await openai.createAudio({
      model: "tts-1",
      voice: "alloy",
      input: analysis
    });
    
    // Save audio file
    const audioFileName = `response-${Date.now()}.mp3`;
    const audioDir = path.join(__dirname, '../uploads/audio');
    
    // Create directory if it doesn't exist
    if (!fs.existsSync(audioDir)) {
      fs.mkdirSync(audioDir, { recursive: true });
    }
    
    const audioPath = path.join(audioDir, audioFileName);
    fs.writeFileSync(audioPath, audioResponse.data);
    
    // Generate audio URL
    const audioUrl = `${getBaseUrl(req)}/uploads/audio/${audioFileName}`;
    
    return res.status(200).json({
      success: true,
      response: analysis,
      audio_url: audioUrl,
      should_enter_tutorial_mode: shouldEnterTutorialMode,
      learning_context: analysis,
      learning_steps: learningSteps
    });
    
  } catch (error) {
    console.error('Error analyzing image:', error);
    return res.status(500).json({
      success: false,
      message: 'Error analyzing image',
      error: error.message
    });
  }
};
