#!/usr/bin/env python3
"""
Test script for trpakov/vit-face-expression model on GPU
Vision Transformer for facial expression recognition
"""

import os
import tempfile
import time

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification, pipeline


def create_test_faces():
    """Create test face images with different expressions"""
    print("🎭 Creating test face images...")

    temp_dir = tempfile.gettempdir()
    test_images = []

    # Create simple synthetic face-like images for testing
    # In a real scenario, you'd use actual face photos
    face_expressions = [
        ("happy", (0, 255, 0)),  # Green tint for happy
        ("sad", (255, 0, 0)),  # Blue tint for sad
        ("angry", (0, 0, 255)),  # Red tint for angry
        ("neutral", (128, 128, 128)),  # Gray for neutral
    ]

    for _i, (expression, color) in enumerate(face_expressions):
        # Create a 224x224 image (standard ViT input size)
        img = np.zeros((224, 224, 3), dtype=np.uint8)

        # Create a face-like shape (circle)
        center = (112, 112)
        radius = 80
        cv2.circle(img, center, radius, color, -1)

        # Add eyes
        cv2.circle(img, (90, 90), 15, (255, 255, 255), -1)  # Left eye
        cv2.circle(img, (134, 90), 15, (255, 255, 255), -1)  # Right eye
        cv2.circle(img, (90, 90), 8, (0, 0, 0), -1)  # Left pupil
        cv2.circle(img, (134, 90), 8, (0, 0, 0), -1)  # Right pupil

        # Add mouth based on expression
        if expression == "happy":
            # Smile
            cv2.ellipse(img, (112, 140), (25, 15), 0, 0, 180, (0, 0, 0), 3)
        elif expression == "sad":
            # Frown
            cv2.ellipse(img, (112, 150), (25, 15), 0, 180, 360, (0, 0, 0), 3)
        elif expression == "angry":
            # Straight line
            cv2.line(img, (87, 140), (137, 140), (0, 0, 0), 3)
            # Angry eyebrows
            cv2.line(img, (75, 75), (105, 85), (0, 0, 0), 3)
            cv2.line(img, (119, 85), (149, 75), (0, 0, 0), 3)
        else:  # neutral
            # Small mouth
            cv2.ellipse(img, (112, 140), (15, 8), 0, 0, 180, (0, 0, 0), 2)

        # Add some texture/noise to make it more realistic
        noise = np.random.randint(0, 30, img.shape, dtype=np.uint8)
        img = cv2.add(img, noise)

        # Save as temporary file
        filename = f"test_face_{expression}.jpg"
        filepath = os.path.join(temp_dir, filename)
        cv2.imwrite(filepath, img)

        test_images.append({"path": filepath, "expression": expression, "image": img})

        print(f"   Created {expression} face: {filename}")

    return test_images


def test_face_expression_gpu():
    """Test trpakov/vit-face-expression model on GPU"""
    print("🔥 Testing trpakov/vit-face-expression model on GPU...")

    # Check GPU availability
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "No GPU"

    print(f"📱 Device: {device}")
    print(f"🎮 GPU: {gpu_name}")

    test_images = create_test_faces()

    try:
        # Load model and processor
        model_name = "trpakov/vit-face-expression"
        print(f"⬇️  Loading model: {model_name}")

        start_time = time.time()

        # Load processor and model
        processor = AutoImageProcessor.from_pretrained(model_name)
        model = AutoModelForImageClassification.from_pretrained(model_name)

        # Move model to GPU
        model = model.to(device)

        # Create pipeline
        classifier = pipeline(
            "image-classification",
            model=model,
            image_processor=processor,
            device=0 if torch.cuda.is_available() else -1,
            top_k=None,  # Return all scores
        )

        load_time = time.time() - start_time
        print(f"✅ Model loaded in {load_time:.4f} seconds")

        # Test emotion classification on each face
        print("\n🎭 Testing facial expression recognition:")
        print("=" * 60)

        total_inference_time = 0
        results = []

        for i, test_image in enumerate(test_images, 1):
            print(f"\n{i}. Expected: {test_image['expression']}")

            # Load image
            pil_image = Image.open(test_image["path"]).convert("RGB")

            # Measure inference time
            start_time = time.time()
            predictions = classifier(pil_image)
            inference_time = time.time() - start_time
            total_inference_time += inference_time

            # Get top prediction
            top_prediction = predictions[0]

            print(f"   🎯 Predicted: {top_prediction['label']} ({top_prediction['score']:.4f})")
            print(f"   ⏱️  Inference time: {inference_time:.4f} seconds")

            # Show all predictions with significant confidence
            print("   📊 All expressions:")
            for pred in predictions[:3]:  # Top 3
                print(f"      - {pred['label']}: {pred['score']:.4f}")

            results.append(
                {
                    "expected": test_image["expression"],
                    "predicted": top_prediction["label"],
                    "confidence": top_prediction["score"],
                    "inference_time": inference_time,
                    "all_predictions": predictions,
                }
            )

        avg_inference_time = total_inference_time / len(test_images)

        print("\n📈 Performance Summary:")
        print(f"   • Model load time: {load_time:.4f} seconds")
        print(f"   • Average inference time: {avg_inference_time:.4f} seconds")
        print(f"   • Total inference time: {total_inference_time:.4f} seconds")
        print(f"   • Images processed: {len(test_images)}")

        # Memory usage (if CUDA)
        if torch.cuda.is_available():
            memory_allocated = torch.cuda.memory_allocated(0) / 1024**3  # GB
            memory_reserved = torch.cuda.memory_reserved(0) / 1024**3  # GB
            print(f"   • GPU memory allocated: {memory_allocated:.2f} GB")
            print(f"   • GPU memory reserved: {memory_reserved:.2f} GB")

        # Accuracy analysis
        print("\n🎯 Model Analysis:")
        emotion_labels = set()
        for result in results:
            for pred in result["all_predictions"]:
                emotion_labels.add(pred["label"])

        print(f"   • Detected emotion labels: {sorted(emotion_labels)}")
        print(f"   • Average confidence: {np.mean([r['confidence'] for r in results]):.4f}")

        # Assert that the test completed successfully
        assert len(results) > 0, "No face expression predictions were made"
        assert all(
            r["confidence"] > 0.1 for r in results
        ), "All predictions should have reasonable confidence"
        assert load_time < 30, "Model loading should be reasonably fast"
        assert avg_inference_time < 5, "Inference should be reasonably fast"

        print("✅ Face expression recognition test completed successfully!")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()
        raise  # Re-raise the exception for pytest

    finally:
        # Clean up test images
        for test_image in test_images:
            try:
                if os.path.exists(test_image["path"]):
                    os.remove(test_image["path"])
            except OSError:
                pass
        print("🗑️  Cleaned up test images")


if __name__ == "__main__":
    try:
        results = test_face_expression_gpu()
        if results:
            print("\n✅ Face expression recognition test completed successfully!")
            print("🚀 Ready for GPU-accelerated facial emotion detection!")
        else:
            print("\n❌ Test failed - check model availability")
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback

        traceback.print_exc()
