# Video Analysis Server

AI-powered video analysis microservice using GPU-accelerated models.

## Features

- **CLIP Visual Intelligence**: Scene understanding and content analysis
- **Emotion Detection**: Text-based emotion analysis
- **Face Expression Recognition**: Visual emotion detection from faces
- **Engagement Prediction**: Viewer engagement metrics
- **MediaPipe Pose**: Body language and gesture recognition
- **Scene Detection**: Automatic video scene segmentation
- **Video Quality Analysis**: Quality metrics and assessment

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run GPU Tests

Test GPU availability and download models:

```bash
# Quick GPU check
pytest gpu/testing/test_gpu.py -v

# Run all model tests (downloads models on first run)
pytest gpu/testing/ -v

# Run specific test
pytest gpu/testing/test_emotion.py -v
```

## Models

Models are automatically downloaded and cached on first use:
- **Cache Location (Windows)**: `C:\Users\<username>\.cache\huggingface\hub\`
- **CLIP Cache**: `~/.cache/clip/`

## GPU Requirements

- CUDA-compatible GPU (recommended)
- Falls back to CPU if GPU not available
- Check GPU status: `pytest gpu/testing/test_gpu.py`
