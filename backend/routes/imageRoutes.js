const express = require('express');
const router = express.Router();
const imageController = require('../controllers/imageController');

// Image upload route
router.post('/upload', imageController.uploadImage);

// Image analysis route
router.post('/analyze', imageController.analyzeImage);

module.exports = router;
