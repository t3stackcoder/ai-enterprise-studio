#!/usr/bin/env python3
"""
Test script for local emotion detection model
Tests the j-hartmann/emotion-english-distilroberta-base model on GPU
"""

import time

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline


def test_emotion_model():
    print("🔥 Testing j-hartmann/emotion-english-distilroberta-base model...")

    # Check GPU availability
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "No GPU"

    print(f"📱 Device: {device}")
    print(f"🎮 GPU: {gpu_name}")

    # Load model
    model_name = "j-hartmann/emotion-english-distilroberta-base"
    print(f"⬇️  Loading model: {model_name}")

    start_time = time.time()

    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)

    # Move model to GPU
    model = model.to(device)

    # Create pipeline
    classifier = pipeline(
        "text-classification",
        model=model,
        tokenizer=tokenizer,
        device=0 if torch.cuda.is_available() else -1,
        top_k=None,  # Return all scores (replaces deprecated return_all_scores=True)
    )

    load_time = time.time() - start_time
    print(f"✅ Model loaded in {load_time:.4f} seconds")

    # Test texts with different emotions
    test_texts = [
        "I am so happy and excited about this amazing project!",
        "This is really frustrating and makes me angry.",
        "I'm worried about what might happen next.",
        "That's a really sad story, I feel terrible.",
        "Wow, that was completely unexpected!",
        "This is disgusting and awful.",
        "The weather is nice today.",
    ]

    print("\n🧪 Testing emotion classification:")
    print("=" * 60)

    total_inference_time = 0

    for i, text in enumerate(test_texts, 1):
        print(f'\n{i}. Text: "{text}"')

        # Measure inference time
        start_time = time.time()
        results = classifier(text)
        inference_time = time.time() - start_time
        total_inference_time += inference_time

        # Get top emotion
        emotions = results[0]  # Pipeline returns list of lists
        emotions.sort(key=lambda x: x["score"], reverse=True)

        top_emotion = emotions[0]
        print(f"   🎯 Top emotion: {top_emotion['label']} ({top_emotion['score']:.4f})")
        print(f"   ⏱️  Inference time: {inference_time:.4f} seconds")

        # Show all emotions if score > 0.1
        print("   📊 All emotions:")
        for emotion in emotions:
            if emotion["score"] > 0.1:
                print(f"      - {emotion['label']}: {emotion['score']:.4f}")

    avg_inference_time = total_inference_time / len(test_texts)
    print("\n📈 Performance Summary:")
    print(f"   • Model load time: {load_time:.4f} seconds")
    print(f"   • Average inference time: {avg_inference_time:.4f} seconds")
    print(f"   • Total inference time: {total_inference_time:.4f} seconds")
    print(f"   • Texts processed: {len(test_texts)}")

    # Memory usage (if CUDA)
    if torch.cuda.is_available():
        memory_allocated = torch.cuda.memory_allocated(0) / 1024**3  # GB
        memory_reserved = torch.cuda.memory_reserved(0) / 1024**3  # GB
        print(f"   • GPU memory allocated: {memory_allocated:.2f} GB")
        print(f"   • GPU memory reserved: {memory_reserved:.2f} GB")

    print("\n✅ Emotion model test completed successfully!")


if __name__ == "__main__":
    test_emotion_model()
