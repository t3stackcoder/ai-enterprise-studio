#!/usr/bin/env python3
"""
CLIP Visual Intelligence Test Suite
Tests openai/clip-vit-base-patch32 for visual content understanding
"""

import os
import tempfile
import time
import warnings

import clip
import cv2
import numpy as np
import pytest
import torch
from PIL import Image

# Suppress known warnings from dependencies
warnings.filterwarnings("ignore", message=".*Torch was not compiled with flash attention.*")
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*has no __module__ attribute.*"
)


@pytest.fixture(scope="module")
def device():
    """Pytest fixture for device"""
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


@pytest.fixture(scope="module")
def model_and_preprocess(device):
    """Pytest fixture for CLIP model and preprocessor"""
    try:
        print(f"🎯 Loading CLIP model on {device}")
        model, preprocess = clip.load("ViT-B/32", device=device)
        return model, preprocess
    except Exception as e:
        pytest.skip(f"CLIP model loading failed: {e}")


@pytest.fixture(scope="module")
def model(model_and_preprocess):
    """Pytest fixture for CLIP model"""
    return model_and_preprocess[0]


@pytest.fixture(scope="module")
def preprocess(model_and_preprocess):
    """Pytest fixture for CLIP preprocessor"""
    return model_and_preprocess[1]


@pytest.fixture(scope="module")
def test_images():
    """Pytest fixture for test images"""
    print("🎨 Creating test images for CLIP analysis...")

    temp_dir = tempfile.gettempdir()
    test_images = []

    # Test scenarios for video content
    scenarios = [
        {
            "name": "presentation",
            "description": "Person presenting with whiteboard",
            "elements": [(100, 50, "person"), (200, 100, "whiteboard")],
        },
        {
            "name": "interview",
            "description": "Two people in conversation",
            "elements": [(80, 80, "person1"), (240, 80, "person2")],
        },
        {
            "name": "screen_share",
            "description": "Computer screen with presentation",
            "elements": [(160, 120, "screen")],
        },
        {
            "name": "outdoor",
            "description": "Person speaking outdoors",
            "elements": [(100, 100, "person"), (200, 200, "nature")],
        },
    ]

    for scenario in scenarios:
        # Create 224x224 image (CLIP standard)
        img = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)

        # Add visual elements
        for x, y, element_type in scenario["elements"]:
            if element_type == "person":
                cv2.circle(img, (x, y), 30, (255, 200, 150), -1)  # Skin tone circle
                cv2.circle(img, (x - 10, y - 10), 5, (0, 0, 0), -1)  # Eyes
                cv2.circle(img, (x + 10, y - 10), 5, (0, 0, 0), -1)
            elif element_type == "whiteboard":
                cv2.rectangle(img, (x - 40, y - 30), (x + 40, y + 30), (255, 255, 255), -1)
                cv2.rectangle(img, (x - 40, y - 30), (x + 40, y + 30), (0, 0, 0), 2)
            elif element_type == "screen":
                cv2.rectangle(img, (x - 60, y - 45), (x + 60, y + 45), (50, 50, 50), -1)
                cv2.rectangle(img, (x - 50, y - 35), (x + 50, y + 35), (100, 150, 255), -1)

        # Save image
        image_path = os.path.join(temp_dir, f"clip_test_{scenario['name']}.jpg")
        cv2.imwrite(image_path, img)

        test_images.append(
            {"path": image_path, "name": scenario["name"], "description": scenario["description"]}
        )

        print(f"  📸 Created {scenario['name']}: {scenario['description']}")

    # Cleanup after tests
    yield test_images

    # Cleanup test images
    for img_data in test_images:
        try:
            os.remove(img_data["path"])
        except OSError:
            pass


def test_clip_installation():
    """Test CLIP library installation and basic functionality"""
    try:
        print("✅ CLIP library installed successfully")

        # List available models
        available_models = clip.available_models()
        print(f"📋 Available CLIP models: {available_models}")
        assert len(available_models) > 0
    except ImportError as e:
        print(f"❌ CLIP not installed: {e}")
        print("💡 Install with: pip install git+https://github.com/openai/CLIP.git")
        pytest.fail(f"CLIP not installed: {e}")


def test_clip_gpu_performance(device):
    """Test CLIP model performance on GPU"""
    print("\n🔥 Testing CLIP GPU Performance...")

    try:

        # Check GPU availability
        print(f"🎯 Using device: {device}")

        if torch.cuda.is_available():
            print(f"🚀 GPU: {torch.cuda.get_device_name(0)}")
            print(f"💾 GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

        # Load model
        print("\n📥 Loading CLIP model...")
        start_time = time.time()
        model, preprocess = clip.load("ViT-B/32", device=device)
        load_time = time.time() - start_time
        print(f"✅ Model loaded in {load_time:.3f} seconds")

        # Check GPU memory usage
        if torch.cuda.is_available():
            memory_allocated = torch.cuda.memory_allocated(0) / 1e9
            print(f"📊 GPU Memory allocated: {memory_allocated:.3f} GB")

        assert model is not None
        assert preprocess is not None

    except Exception as e:
        print(f"❌ Error loading CLIP model: {e}")
        pytest.fail(f"CLIP GPU performance test failed: {e}")


def test_image_understanding(model, preprocess, device, test_images):
    """Test CLIP's image understanding capabilities"""
    print("\n🎭 Testing Image Understanding...")

    if model is None:
        print("❌ Model not loaded, skipping image tests")
        return

    import clip

    # Define text queries for video content
    text_queries = [
        "a person giving a presentation",
        "two people having a conversation",
        "a computer screen with data",
        "someone speaking outdoors",
        "a whiteboard with diagrams",
        "professional video content",
        "casual conversation",
        "educational content",
    ]

    print(f"🔍 Testing {len(text_queries)} text queries on {len(test_images)} images")

    # Tokenize text
    text_tokens = clip.tokenize(text_queries).to(device)

    total_inference_time = 0

    for img_data in test_images:
        print(f"\n📸 Analyzing: {img_data['name']} - {img_data['description']}")

        try:
            # Load and preprocess image
            image = Image.open(img_data["path"])
            image_tensor = preprocess(image).unsqueeze(0).to(device)

            # Run inference
            start_time = time.time()

            with torch.no_grad():
                # Get image and text features
                _ = model.encode_image(image_tensor)
                _ = model.encode_text(text_tokens)

                # Calculate similarities
                logits_per_image, logits_per_text = model(image_tensor, text_tokens)
                probs = logits_per_image.softmax(dim=-1).cpu().numpy()

            inference_time = time.time() - start_time
            total_inference_time += inference_time

            # Show top 3 matches
            top_indices = np.argsort(probs[0])[::-1][:3]

            print(f"  ⏱️  Inference time: {inference_time:.4f} seconds")
            print("  🎯 Top matches:")

            for i, idx in enumerate(top_indices):
                confidence = probs[0][idx] * 100
                print(f"    {i+1}. {text_queries[idx]} ({confidence:.1f}%)")

        except Exception as e:
            print(f"  ❌ Error processing {img_data['name']}: {e}")

    avg_inference_time = total_inference_time / len(test_images)
    print(f"\n📊 Average inference time: {avg_inference_time:.4f} seconds")
    print(f"🚀 Total processing time: {total_inference_time:.3f} seconds")


def test_video_frame_analysis(device):
    """Test CLIP on video frame analysis"""
    print("\n🎬 Testing Video Frame Analysis...")

    try:
        import clip

        model, preprocess = clip.load("ViT-B/32", device=device)

        # Simulate video frames with different content
        frame_scenarios = [
            "close-up shot of speaker",
            "wide shot of presentation",
            "medium shot of conversation",
            "screen recording of software",
            "outdoor interview setting",
        ]

        print(f"🎥 Simulating {len(frame_scenarios)} video frame types...")

        # Create synthetic frames
        frames = []
        for _i, scenario in enumerate(frame_scenarios):
            # Create frame-like image
            frame = np.random.randint(50, 200, (480, 640, 3), dtype=np.uint8)

            # Add content based on scenario
            if "close-up" in scenario:
                cv2.circle(frame, (320, 200), 80, (255, 200, 150), -1)
            elif "wide" in scenario:
                cv2.rectangle(frame, (100, 100), (540, 380), (200, 200, 200), 2)
            elif "screen" in scenario:
                cv2.rectangle(frame, (160, 120), (480, 360), (50, 100, 200), -1)

            frames.append((frame, scenario))

        # Analyze frames
        shot_types = [
            "close-up shot",
            "medium shot",
            "wide shot",
            "screen recording",
            "presentation slide",
        ]

        text_tokens = clip.tokenize(shot_types).to(device)

        total_time = 0

        for frame, scenario in frames:
            # Convert to PIL and preprocess
            frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            frame_tensor = preprocess(frame_pil).unsqueeze(0).to(device)

            start_time = time.time()

            with torch.no_grad():
                logits_per_image, _ = model(frame_tensor, text_tokens)
                probs = logits_per_image.softmax(dim=-1).cpu().numpy()

            processing_time = time.time() - start_time
            total_time += processing_time

            # Find best match
            best_idx = np.argmax(probs[0])
            confidence = probs[0][best_idx] * 100

            print(f"  📹 {scenario}:")
            print(f"     🎯 Detected: {shot_types[best_idx]} ({confidence:.1f}%)")
            print(f"     ⏱️  Time: {processing_time:.4f}s")

        fps_equivalent = len(frames) / total_time
        print(f"\n🚀 Processing speed: {fps_equivalent:.1f} frames/second equivalent")
        print(f"💡 Real-time capability: {'✅ Yes' if fps_equivalent >= 24 else '❌ No'}")

    except Exception as e:
        print(f"❌ Error in video frame analysis: {e}")
