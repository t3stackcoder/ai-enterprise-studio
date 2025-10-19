#!/usr/bin/env python3
"""
Engagement Prediction Test Suite
Tests AI models for predicting viewer engagement and content performance
"""

import os
import tempfile
import time

import cv2
import numpy as np


def test_engagement_libs():
    """Test engagement prediction library installations"""
    print("🔥 Testing Engagement Prediction Libraries...")

    libraries_status = {}

    # Test PyTorch
    try:
        import torch

        print(f"✅ PyTorch: {torch.__version__}")
        print(f"🎯 CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"🚀 GPU: {torch.cuda.get_device_name(0)}")
        libraries_status["torch"] = True
    except ImportError:
        print("❌ PyTorch not installed")
        libraries_status["torch"] = False

    # Test transformers for pre-trained models
    try:
        import transformers

        # Verify the import worked by accessing a key component
        _ = transformers.__version__
        print("✅ Transformers for pre-trained models")
        libraries_status["transformers"] = True
    except ImportError:
        print("❌ Transformers not installed: pip install transformers")
        libraries_status["transformers"] = False

    # Test OpenCV
    try:
        import cv2

        print(f"✅ OpenCV: {cv2.__version__}")
        libraries_status["opencv"] = True
    except ImportError:
        print("❌ OpenCV not installed: pip install opencv-python")
        libraries_status["opencv"] = False

    # Test scikit-learn for engagement modeling
    try:
        import sklearn

        # Verify the import worked by accessing a key component
        _ = sklearn.__version__
        print("✅ scikit-learn for engagement modeling")
        libraries_status["sklearn"] = True
    except ImportError:
        print("❌ scikit-learn not installed: pip install scikit-learn")
        libraries_status["sklearn"] = False

    # Assert that all critical libraries are available
    assert libraries_status["torch"], "PyTorch is required for engagement prediction"
    assert libraries_status["transformers"], "Transformers is required for pre-trained models"
    assert libraries_status["opencv"], "OpenCV is required for video processing"
    assert libraries_status["sklearn"], "scikit-learn is required for engagement modeling"

    print("✅ All engagement prediction libraries are properly installed!")


def create_engagement_scenarios():
    """Create test scenarios with different engagement characteristics"""
    print("\n🎯 Creating engagement test scenarios...")

    temp_dir = tempfile.gettempdir()
    scenarios = []

    # Define engagement scenarios based on video content patterns
    engagement_patterns = [
        {
            "name": "high_energy_presentation",
            "description": "High energy presentation with gestures",
            "expected_engagement": 85,
            "features": {
                "speaker_movement": "high",
                "gesture_frequency": "high",
                "facial_expressions": "varied",
                "pace": "dynamic",
                "visual_aids": "present",
            },
        },
        {
            "name": "calm_interview",
            "description": "Calm seated interview",
            "expected_engagement": 65,
            "features": {
                "speaker_movement": "low",
                "gesture_frequency": "medium",
                "facial_expressions": "moderate",
                "pace": "steady",
                "visual_aids": "none",
            },
        },
        {
            "name": "monotone_lecture",
            "description": "Monotone lecture with little variation",
            "expected_engagement": 35,
            "features": {
                "speaker_movement": "minimal",
                "gesture_frequency": "low",
                "facial_expressions": "static",
                "pace": "slow",
                "visual_aids": "slides_only",
            },
        },
        {
            "name": "animated_discussion",
            "description": "Animated discussion between multiple people",
            "expected_engagement": 78,
            "features": {
                "speaker_movement": "medium",
                "gesture_frequency": "high",
                "facial_expressions": "very_varied",
                "pace": "variable",
                "visual_aids": "interactive",
            },
        },
        {
            "name": "technical_demo",
            "description": "Technical demonstration with screen sharing",
            "expected_engagement": 55,
            "features": {
                "speaker_movement": "low",
                "gesture_frequency": "medium",
                "facial_expressions": "focused",
                "pace": "methodical",
                "visual_aids": "screen_share",
            },
        },
    ]

    for pattern in engagement_patterns:
        # Create visual representation
        frame = np.ones((720, 1280, 3), dtype=np.uint8) * 200  # Light background

        # Simulate content based on engagement features
        center_x, center_y = 640, 360

        # Speaker representation based on movement level
        if pattern["features"]["speaker_movement"] == "high":
            # Multiple positions to show movement
            positions = [
                (center_x - 100, center_y),
                (center_x, center_y - 50),
                (center_x + 100, center_y),
            ]
            for pos in positions:
                cv2.circle(frame, pos, 40, (255, 200, 150), 2)  # Outline to show movement
        elif pattern["features"]["speaker_movement"] == "medium":
            cv2.circle(frame, (center_x, center_y), 50, (255, 200, 150), -1)
            cv2.circle(
                frame, (center_x + 30, center_y - 20), 50, (255, 200, 150), 2
            )  # Slight movement
        else:  # low/minimal
            cv2.circle(frame, (center_x, center_y), 50, (255, 200, 150), -1)  # Static position

        # Gesture indicators
        if pattern["features"]["gesture_frequency"] == "high":
            # Multiple arm positions
            cv2.line(
                frame,
                (center_x - 80, center_y),
                (center_x - 120, center_y - 40),
                (150, 120, 100),
                8,
            )
            cv2.line(
                frame,
                (center_x + 80, center_y),
                (center_x + 120, center_y - 40),
                (150, 120, 100),
                8,
            )
        elif pattern["features"]["gesture_frequency"] == "medium":
            cv2.line(
                frame, (center_x - 60, center_y), (center_x - 80, center_y - 20), (150, 120, 100), 6
            )
        # Low gesture frequency = no gesture lines

        # Visual aids representation
        if pattern["features"]["visual_aids"] == "present":
            cv2.rectangle(frame, (100, 100), (400, 300), (255, 255, 255), -1)
            cv2.rectangle(frame, (100, 100), (400, 300), (0, 0, 0), 3)
            cv2.putText(frame, "CHART", (180, 220), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
        elif pattern["features"]["visual_aids"] == "screen_share":
            cv2.rectangle(frame, (50, 50), (600, 400), (50, 50, 50), -1)
            cv2.rectangle(frame, (70, 70), (580, 380), (100, 150, 255), -1)
            cv2.putText(
                frame, "SCREEN", (200, 250), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3
            )
        elif pattern["features"]["visual_aids"] == "slides_only":
            cv2.rectangle(frame, (900, 100), (1200, 400), (240, 240, 240), -1)
            cv2.putText(frame, "SLIDE", (950, 270), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

        # Save frame
        frame_path = os.path.join(temp_dir, f"engagement_{pattern['name']}.jpg")
        cv2.imwrite(frame_path, frame)

        scenarios.append(
            {
                "path": frame_path,
                "name": pattern["name"],
                "description": pattern["description"],
                "expected_engagement": pattern["expected_engagement"],
                "features": pattern["features"],
            }
        )

        print(
            f"  🎯 Created {pattern['name']}: {pattern['description']} (Expected: {pattern['expected_engagement']}%)"
        )

    return scenarios


def extract_engagement_features(frame_path):
    """Extract features that correlate with engagement"""

    frame = cv2.imread(frame_path)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    features = {}

    # 1. Visual Complexity (more complex = potentially more engaging)
    edges = cv2.Canny(gray, 50, 150)
    features["edge_density"] = np.sum(edges > 0) / edges.size

    # 2. Color Variety (more colors = more visually interesting)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    features["color_variance"] = np.var(hsv[:, :, 1])  # Saturation variance

    # 3. Brightness Distribution (good lighting = more engaging)
    features["brightness_mean"] = np.mean(gray)
    features["brightness_std"] = np.std(gray)

    # 4. Content Distribution (balanced composition)
    height, width = gray.shape
    center_region = gray[height // 4 : 3 * height // 4, width // 4 : 3 * width // 4]
    features["center_content"] = np.mean(center_region)

    # 5. Motion Indicators (from static analysis)
    # Look for multiple similar objects (indicating movement/gestures)
    circles = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT, 1, 50, param1=50, param2=30, minRadius=20, maxRadius=100
    )
    features["motion_indicators"] = len(circles[0]) if circles is not None else 0

    # 6. Text/Visual Aid Detection
    # Simple detection of rectangular regions (slides, screens)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    rectangular_areas = 0
    for contour in contours:
        if cv2.contourArea(contour) > 1000:  # Filter small contours
            rect_area = cv2.contourArea(contour)
            rect_perimeter = cv2.arcLength(contour, True)
            if rect_perimeter > 0:
                circularity = 4 * np.pi * rect_area / (rect_perimeter * rect_perimeter)
                if circularity < 0.5:  # Rectangular-ish shapes
                    rectangular_areas += 1

    features["visual_aids_count"] = rectangular_areas

    return features


def predict_engagement(scenarios):
    """Predict engagement scores using extracted features"""
    print("\n🧠 Predicting Engagement Scores...")

    try:
        import numpy as np
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.preprocessing import StandardScaler

        # Extract features for all scenarios
        all_features = []
        all_labels = []

        total_processing_time = 0

        for scenario in scenarios:
            print(f"\n🎯 Analyzing: {scenario['description']}")

            start_time = time.time()
            features = extract_engagement_features(scenario["path"])
            processing_time = time.time() - start_time
            total_processing_time += processing_time

            print(f"  ⏱️  Feature extraction time: {processing_time:.4f} seconds")
            print("  📊 Extracted features:")
            for feature_name, value in features.items():
                print(f"     {feature_name}: {value:.3f}")

            # Convert features to list for model training
            feature_vector = [
                features["edge_density"],
                features["color_variance"],
                features["brightness_mean"],
                features["brightness_std"],
                features["center_content"],
                features["motion_indicators"],
                features["visual_aids_count"],
            ]

            all_features.append(feature_vector)
            all_labels.append(scenario["expected_engagement"])

        # Convert to numpy arrays
        X = np.array(all_features)
        y = np.array(all_labels)

        print("\n🔬 Training engagement prediction model...")
        print(f"  📊 Features shape: {X.shape}")
        print(f"  🎯 Labels shape: {y.shape}")

        # Simple model training (in practice, you'd use a larger dataset)
        # For demo purposes, we'll use the same data for training and testing
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_scaled, y)

        # Make predictions
        predictions = model.predict(X_scaled)

        print("\n📈 Engagement Predictions vs Expected:")
        total_error = 0

        for i, scenario in enumerate(scenarios):
            predicted = predictions[i]
            expected = scenario["expected_engagement"]
            error = abs(predicted - expected)
            total_error += error

            print(f"  🎬 {scenario['name']}:")
            print(f"     🎯 Predicted: {predicted:.1f}%")
            print(f"     ✅ Expected: {expected}%")
            print(f"     📊 Error: {error:.1f}%")

            # Engagement level classification
            if predicted >= 75:
                engagement_level = "High"
            elif predicted >= 50:
                engagement_level = "Medium"
            else:
                engagement_level = "Low"

            print(f"     🏆 Engagement Level: {engagement_level}")

        avg_error = total_error / len(scenarios)
        avg_processing_time = total_processing_time / len(scenarios)

        print("\n📊 Model Performance:")
        print(f"  🎯 Average prediction error: {avg_error:.1f}%")
        print(f"  ⏱️  Average processing time: {avg_processing_time:.4f} seconds")
        print(f"  🚀 Throughput: {1/avg_processing_time:.1f} predictions/second")

        # Feature importance
        feature_names = [
            "edge_density",
            "color_variance",
            "brightness_mean",
            "brightness_std",
            "center_content",
            "motion_indicators",
            "visual_aids_count",
        ]

        importances = model.feature_importances_
        print("\n🔍 Feature Importance for Engagement Prediction:")
        for name, importance in zip(feature_names, importances, strict=False):
            print(f"  📊 {name}: {importance:.3f}")

    except Exception as e:
        print(f"❌ Error in engagement prediction: {e}")


def test_real_time_scoring():
    """Test real-time engagement scoring capability"""
    print("\n⚡ Testing Real-time Engagement Scoring...")

    # Simulate processing multiple frames quickly
    num_frames = 30  # Simulate 30 frames (1 second at 30fps)
    frame_times = []

    print(f"🎬 Processing {num_frames} frames for real-time simulation...")

    for i in range(num_frames):
        # Create random frame
        frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)

        # Add some content
        center_x, center_y = 640 + np.random.randint(-50, 50), 360 + np.random.randint(-50, 50)
        cv2.circle(frame, (center_x, center_y), 50, (255, 200, 150), -1)

        # Save temporary frame
        temp_path = os.path.join(tempfile.gettempdir(), f"realtime_frame_{i}.jpg")
        cv2.imwrite(temp_path, frame)

        # Time feature extraction
        start_time = time.time()
        _ = extract_engagement_features(temp_path)
        processing_time = time.time() - start_time
        frame_times.append(processing_time)

        # Clean up
        try:
            os.remove(temp_path)
        except OSError:
            pass

    avg_frame_time = np.mean(frame_times)
    max_frame_time = np.max(frame_times)
    min_frame_time = np.min(frame_times)
    fps_capability = 1.0 / avg_frame_time

    print("\n📊 Real-time Performance:")
    print(f"  ⏱️  Average frame processing: {avg_frame_time:.4f} seconds")
    print(f"  📈 Max frame processing: {max_frame_time:.4f} seconds")
    print(f"  📉 Min frame processing: {min_frame_time:.4f} seconds")
    print(f"  🚀 FPS capability: {fps_capability:.1f} fps")
    print(f"  💡 Real-time capable (30fps): {'✅ Yes' if fps_capability >= 30 else '❌ No'}")
    print(f"  🎯 Real-time capable (24fps): {'✅ Yes' if fps_capability >= 24 else '❌ No'}")


def main():
    """Main test function"""
    print("🔥 Engagement Prediction Test Suite")
    print("=" * 50)

    # Test 1: Library installations
    libs = test_engagement_libs()
    if not libs["opencv"] or not libs["sklearn"]:
        print("❌ Required libraries missing. Please install them first.")
        return

    # Test 2: Create engagement scenarios
    scenarios = create_engagement_scenarios()

    # Test 3: Predict engagement
    predict_engagement(scenarios)

    # Test 4: Real-time performance
    test_real_time_scoring()

    print("\n" + "=" * 50)
    print("🎉 Engagement Prediction tests completed!")
    print("\n💡 Next steps:")
    print("   - Train model on larger dataset of actual video engagement data")
    print("   - Add engagement prediction to main API (app.py)")
    print("   - Create /api/gpu-engagement-analysis endpoint")
    print("   - Integrate with video timeline for engagement scoring")
    print("   - Combine with other AI models for comprehensive analysis")

    # Cleanup
    for scenario in scenarios:
        try:
            os.remove(scenario["path"])
        except OSError:
            pass


if __name__ == "__main__":
    main()
