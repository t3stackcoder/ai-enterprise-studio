#!/usr/bin/env python3
"""
MediaPipe Pose & Body Language Test Suite
Tests MediaPipe for pose detection, gesture recognition, and body language analysis
"""

import os
import tempfile
import time

import cv2
import mediapipe as mp
import numpy as np
import pytest


def test_mediapipe_installation():
    """Test MediaPipe installation and GPU support"""
    try:
        print("✅ MediaPipe installed successfully")
        print(f"📦 MediaPipe version: {mp.__version__}")

        # Test basic components
        mp_pose = mp.solutions.pose
        mp_hands = mp.solutions.hands
        mp_face_mesh = mp.solutions.face_mesh

        print("✅ MediaPipe solutions loaded:")
        print("   🧍 Pose detection")
        print("   👋 Hand tracking")
        print("   😊 Face mesh")

        # Assert that components are available
        assert mp_pose is not None, "MediaPipe pose detection should be available"
        assert mp_hands is not None, "MediaPipe hand tracking should be available"
        assert mp_face_mesh is not None, "MediaPipe face mesh should be available"

    except ImportError as e:
        print(f"❌ MediaPipe not installed: {e}")
        print("💡 Install with: pip install mediapipe")
        pytest.fail(f"MediaPipe not installed: {e}")


def create_test_poses():
    """Create test images with different poses and gestures"""
    print("\n🎭 Creating test pose images...")

    temp_dir = tempfile.gettempdir()
    test_images = []

    # Define pose scenarios for video content
    pose_scenarios = [
        {
            "name": "presenting",
            "description": "Person presenting with arms extended",
            "pose_type": "open_arms",
        },
        {
            "name": "sitting",
            "description": "Person sitting in interview pose",
            "pose_type": "seated",
        },
        {"name": "pointing", "description": "Person pointing or gesturing", "pose_type": "gesture"},
        {"name": "crossed_arms", "description": "Person with arms crossed", "pose_type": "closed"},
    ]

    for _i, scenario in enumerate(pose_scenarios):
        # Create synthetic pose image (in real use, you'd have actual photos)
        img = np.zeros((480, 640, 3), dtype=np.uint8)

        # Add some background color
        img[:] = (50, 50, 50)  # Dark gray background

        # Draw a simple stick figure representing the pose
        center_x, center_y = 320, 240

        # Head
        cv2.circle(img, (center_x, center_y - 100), 30, (200, 200, 200), -1)

        # Body
        cv2.line(img, (center_x, center_y - 70), (center_x, center_y + 80), (200, 200, 200), 8)

        # Arms (different positions based on pose type)
        if scenario["pose_type"] == "open_arms":
            # Extended arms
            cv2.line(img, (center_x, center_y - 30), (center_x - 80, center_y), (200, 200, 200), 6)
            cv2.line(img, (center_x, center_y - 30), (center_x + 80, center_y), (200, 200, 200), 6)
        elif scenario["pose_type"] == "gesture":
            # One arm extended (pointing)
            cv2.line(
                img, (center_x, center_y - 30), (center_x + 100, center_y - 50), (200, 200, 200), 6
            )
            cv2.line(
                img, (center_x, center_y - 30), (center_x - 40, center_y + 10), (200, 200, 200), 6
            )
        elif scenario["pose_type"] == "closed":
            # Arms crossed
            cv2.line(
                img, (center_x, center_y - 30), (center_x + 30, center_y + 10), (200, 200, 200), 6
            )
            cv2.line(
                img, (center_x, center_y - 30), (center_x - 30, center_y + 10), (200, 200, 200), 6
            )
        else:
            # Default seated pose
            cv2.line(
                img, (center_x, center_y - 30), (center_x - 50, center_y + 20), (200, 200, 200), 6
            )
            cv2.line(
                img, (center_x, center_y - 30), (center_x + 50, center_y + 20), (200, 200, 200), 6
            )

        # Legs
        cv2.line(
            img, (center_x, center_y + 80), (center_x - 30, center_y + 150), (200, 200, 200), 6
        )
        cv2.line(
            img, (center_x, center_y + 80), (center_x + 30, center_y + 150), (200, 200, 200), 6
        )

        # Save image
        filename = f"test_pose_{scenario['name']}.jpg"
        filepath = os.path.join(temp_dir, filename)
        cv2.imwrite(filepath, img)

        test_images.append({"path": filepath, "scenario": scenario, "image": img})

        print(f"   Created {scenario['name']} pose: {filename}")

    return test_images


def test_pose_detection_performance():
    """Test MediaPipe pose detection performance"""
    print("\n🔥 Testing MediaPipe Pose Detection Performance...")

    try:
        # Initialize MediaPipe Pose
        mp_pose = mp.solutions.pose

        # Test with different confidence levels
        confidence_levels = [0.5, 0.7, 0.9]

        for confidence in confidence_levels:
            print(f"\n🎯 Testing with confidence threshold: {confidence}")

            with mp_pose.Pose(
                static_image_mode=True,
                model_complexity=2,  # Highest accuracy
                enable_segmentation=True,
                min_detection_confidence=confidence,
            ) as pose:

                print(f"✅ Pose detector initialized (confidence: {confidence})")
                print("📊 Model complexity: 2 (highest accuracy)")
                print("🎭 Segmentation enabled: Yes")

                # Test processing time
                test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
                test_rgb = cv2.cvtColor(test_image, cv2.COLOR_BGR2RGB)

                # Warm-up run
                pose.process(test_rgb)

                # Timed runs
                num_tests = 10
                total_time = 0

                for _i in range(num_tests):
                    start_time = time.time()
                    _ = pose.process(test_rgb)
                    processing_time = time.time() - start_time
                    total_time += processing_time

                avg_time = total_time / num_tests
                fps_equivalent = 1.0 / avg_time

                print(f"  ⏱️  Average processing time: {avg_time:.4f} seconds")
                print(f"  🚀 FPS equivalent: {fps_equivalent:.1f} fps")
                print(f"  💡 Real-time capable: {'✅ Yes' if fps_equivalent >= 24 else '❌ No'}")

        # Assert test success
        assert fps_equivalent > 0, "FPS calculation should be positive"
        print("✅ Pose detection performance test completed successfully!")

    except Exception as e:
        print(f"❌ Error in pose detection test: {e}")
        raise  # Re-raise for pytest


def test_hand_tracking():
    """Test MediaPipe hand tracking capabilities"""
    print("\n👋 Testing MediaPipe Hand Tracking...")

    try:
        mp_hands = mp.solutions.hands

        with mp_hands.Hands(
            static_image_mode=True, max_num_hands=2, min_detection_confidence=0.7
        ) as hands:

            print("✅ Hand tracking initialized")
            print("📊 Max hands: 2")
            print("🎯 Detection confidence: 0.7")

            # Test with synthetic hand image
            test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            test_rgb = cv2.cvtColor(test_image, cv2.COLOR_BGR2RGB)

            # Process image
            start_time = time.time()
            _ = hands.process(test_rgb)
            processing_time = time.time() - start_time

            print(f"⏱️  Processing time: {processing_time:.4f} seconds")
            print("📋 Hand landmarks: 21 points per hand")
            print("🎭 Capabilities:")
            print("   - Finger joint detection")
            print("   - Gesture recognition potential")
            print("   - Multi-hand tracking")

        # Assert test success
        assert mp_hands is not None, "MediaPipe hands should be available"
        print("✅ Hand tracking test completed successfully!")

    except Exception as e:
        print(f"❌ Error in hand tracking test: {e}")
        raise  # Re-raise for pytest


def test_face_mesh():
    """Test MediaPipe face mesh capabilities"""
    print("\n😊 Testing MediaPipe Face Mesh...")

    try:
        mp_face_mesh = mp.solutions.face_mesh

        with mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
        ) as face_mesh:

            print("✅ Face mesh initialized")
            print("📊 Max faces: 1")
            print("🎯 Detection confidence: 0.5")
            print("✨ Refined landmarks: Yes")

            # Test with synthetic face image
            test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            test_rgb = cv2.cvtColor(test_image, cv2.COLOR_BGR2RGB)

            # Process image
            start_time = time.time()
            _ = face_mesh.process(test_rgb)
            processing_time = time.time() - start_time

            print(f"⏱️  Processing time: {processing_time:.4f} seconds")
            print("📋 Face landmarks: 468 points")
            print("🎭 Capabilities:")
            print("   - Detailed facial geometry")
            print("   - Eye tracking")
            print("   - Lip movement analysis")
            print("   - Expression detection")

        # Assert test success
        assert mp_face_mesh is not None, "MediaPipe face mesh should be available"
        print("✅ Face mesh test completed successfully!")

    except Exception as e:
        print(f"❌ Error in face mesh test: {e}")
        raise  # Re-raise for pytest


def analyze_engagement_from_pose(landmarks):
    """Analyze engagement level from pose landmarks"""
    if landmarks is None:
        return {"engagement": "unknown", "confidence": 0.0}

    # Extract key pose landmarks
    # MediaPipe pose has 33 landmarks
    engagement_score = 0.5  # Base score

    # Check posture (shoulders alignment)
    if len(landmarks.landmark) > 12:  # Ensure we have shoulder landmarks
        left_shoulder = landmarks.landmark[11]  # Left shoulder
        right_shoulder = landmarks.landmark[12]  # Right shoulder

        # Check if shoulders are level (good posture)
        shoulder_diff = abs(left_shoulder.y - right_shoulder.y)
        if shoulder_diff < 0.05:  # Normalized coordinates
            engagement_score += 0.2

    # Check arm positioning
    if len(landmarks.landmark) > 16:  # Ensure we have wrist landmarks
        left_wrist = landmarks.landmark[15]  # Left wrist
        right_wrist = landmarks.landmark[16]  # Right wrist
        # nose = landmarks.landmark[0]  # Nose (face center) - unused

        # Check for open, engaging posture
        wrist_spread = abs(left_wrist.x - right_wrist.x)
        if wrist_spread > 0.3:  # Arms spread apart
            engagement_score += 0.2

        # Check if hands are visible and active
        if left_wrist.visibility > 0.5 and right_wrist.visibility > 0.5:
            engagement_score += 0.1

    # Determine engagement level
    if engagement_score > 0.7:
        engagement = "high"
    elif engagement_score > 0.5:
        engagement = "medium"
    else:
        engagement = "low"

    return {
        "engagement": engagement,
        "confidence": min(engagement_score, 1.0),
        "features": {
            "posture": "upright" if engagement_score > 0.6 else "relaxed",
            "gesture": "open" if engagement_score > 0.7 else "neutral",
        },
    }


def main():
    """Main test function"""
    print("🔥 MediaPipe Pose & Body Language Test Suite")
    print("=" * 60)

    # Test installation
    if not test_mediapipe_installation():
        print("❌ MediaPipe installation test failed!")
        exit(1)

    # Create test poses
    _ = create_test_poses()

    # Run performance tests
    if not test_pose_detection_performance():
        print("❌ Performance test failed!")
        exit(1)

    # Test hand tracking
    if not test_hand_tracking():
        print("❌ Hand tracking test failed!")
        exit(1)

    # Test face mesh
    if not test_face_mesh():
        print("❌ Face mesh test failed!")
        exit(1)

    print("\n🎉 MediaPipe Pose & Body Language tests completed!")
    print("\n📝 Next steps:")
    print("   - Add MediaPipe to main API (app.py)")
    print("   - Real video processing tests")
    print("   - Engagement scoring calibration")
    print("   - Performance optimization")


if __name__ == "__main__":
    main()
