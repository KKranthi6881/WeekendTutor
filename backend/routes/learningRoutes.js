const express = require('express');
const router = express.Router();
const analyzeController = require('../controllers/analyzeController');

// Route to analyze student responses
router.post('/analyze', analyzeController.analyzeStudentResponse);

// Route to process learning responses with hints
router.post('/process', analyzeController.processLearningResponse);

module.exports = router;
