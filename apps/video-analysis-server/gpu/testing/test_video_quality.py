#!/usr/bin/env python3
"""
Video Quality Assessment Test Suite
Tests video quality scoring, shot classification, and production analysis
"""

import os
import tempfile
import time

import cv2
import numpy as np


def test_video_quality_libs():
    """Test video quality assessment library installations"""
    print("🔥 Testing Video Quality Assessment Libraries...")

    libraries_status = {}

    # Test OpenCV
    try:
        import cv2

        print(f"✅ OpenCV: {cv2.__version__}")
        libraries_status["opencv"] = True
    except ImportError:
        print("❌ OpenCV not installed: pip install opencv-python")
        libraries_status["opencv"] = False

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

    # Test scikit-image for quality metrics
    try:
        import skimage

        # Verify the import worked by accessing a key component
        _ = skimage.__version__
        print("✅ scikit-image for quality metrics")
        libraries_status["skimage"] = True
    except ImportError:
        print("❌ scikit-image not installed: pip install scikit-image")
        libraries_status["skimage"] = False

    # Test LPIPS for perceptual quality (optional)
    try:
        import lpips

        # Verify the import worked by accessing a key component
        _ = lpips.__version__
        print("✅ LPIPS for perceptual quality")
        libraries_status["lpips"] = True
    except ImportError:
        print("⚠️  LPIPS not installed (optional): pip install lpips")
        libraries_status["lpips"] = False

    # Assert that critical libraries are available
    assert libraries_status["opencv"], "OpenCV is required for video processing"
    assert libraries_status["torch"], "PyTorch is required for deep learning models"
    assert libraries_status["skimage"], "scikit-image is required for quality metrics"

    print("✅ All critical video quality libraries are properly installed!")


def _get_quality_scenarios():
    """Return list of quality scenarios for testing"""
    return [
        {
            "name": "high_quality",
            "description": "High quality professional video",
            "noise_level": 0,
            "blur_level": 0,
            "lighting": "bright",
        },
        {
            "name": "medium_quality",
            "description": "Average webcam quality",
            "noise_level": 10,
            "blur_level": 1,
            "lighting": "normal",
        },
        {
            "name": "low_quality",
            "description": "Poor quality with noise and blur",
            "noise_level": 30,
            "blur_level": 3,
            "lighting": "dark",
        },
        {
            "name": "overexposed",
            "description": "Overexposed video",
            "noise_level": 5,
            "blur_level": 0,
            "lighting": "overexposed",
        },
        {
            "name": "underexposed",
            "description": "Underexposed/dark video",
            "noise_level": 15,
            "blur_level": 1,
            "lighting": "underexposed",
        },
    ]


def _get_background_color(lighting):
    """Get background color based on lighting scenario"""
    colors = {
        "bright": (240, 240, 245),
        "normal": (180, 185, 190),
        "dark": (60, 65, 70),
        "overexposed": (250, 250, 255),
        "underexposed": (30, 35, 40),
    }
    return colors.get(lighting, (180, 185, 190))


def _add_person_to_frame(frame, center_x, center_y, lighting):
    """Add a simple person representation to the frame"""
    person_brightness = 200 if lighting != "underexposed" else 100
    if lighting == "overexposed":
        person_brightness = 255

    # Head
    cv2.circle(
        frame,
        (center_x, center_y - 100),
        60,
        (person_brightness, person_brightness - 20, person_brightness - 10),
        -1,
    )

    # Body
    cv2.rectangle(
        frame,
        (center_x - 80, center_y - 40),
        (center_x + 80, center_y + 200),
        (person_brightness - 50, person_brightness - 30, person_brightness - 40),
        -1,
    )


def _add_face_details(frame, center_x, center_y, noise_level):
    """Add facial details for higher quality frames"""
    if noise_level == 0:
        # Eyes for high quality
        cv2.circle(frame, (center_x - 20, center_y - 110), 8, (50, 50, 50), -1)
        cv2.circle(frame, (center_x + 20, center_y - 110), 8, (50, 50, 50), -1)
        # Mouth
        cv2.ellipse(frame, (center_x, center_y - 80), (15, 8), 0, 0, 180, (80, 60, 60), -1)


def _apply_quality_degradations(frame, scenario):
    """Apply noise and blur degradations to frame"""
    # Apply noise
    if scenario["noise_level"] > 0:
        noise = np.random.normal(0, scenario["noise_level"], frame.shape).astype(np.int16)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Apply blur
    if scenario["blur_level"] > 0:
        kernel_size = scenario["blur_level"] * 2 + 1
        frame = cv2.GaussianBlur(frame, (kernel_size, kernel_size), 0)

    return frame


def _create_single_test_frame(scenario, temp_dir):
    """Create a single test frame for a quality scenario"""
    # Create base frame (720p)
    height, width = 720, 1280
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    center_x, center_y = width // 2, height // 2

    # Set background
    bg_color = _get_background_color(scenario["lighting"])
    frame[:] = bg_color

    # Add person representation
    _add_person_to_frame(frame, center_x, center_y, scenario["lighting"])

    # Add facial details for high quality
    _add_face_details(frame, center_x, center_y, scenario["noise_level"])

    # Apply quality degradations
    frame = _apply_quality_degradations(frame, scenario)

    # Save frame
    frame_path = os.path.join(temp_dir, f"quality_test_{scenario['name']}.jpg")
    cv2.imwrite(frame_path, frame)

    return {
        "path": frame_path,
        "name": scenario["name"],
        "description": scenario["description"],
        "expected_quality": (
            "high"
            if scenario["noise_level"] == 0 and scenario["blur_level"] == 0
            else "medium" if scenario["noise_level"] < 20 else "low"
        ),
    }


def create_test_videos():
    """Create test video frames with different quality characteristics"""
    print("\n🎬 Creating test video frames...")

    temp_dir = tempfile.gettempdir()
    test_frames = []
    quality_scenarios = _get_quality_scenarios()

    for scenario in quality_scenarios:
        frame_info = _create_single_test_frame(scenario, temp_dir)
        test_frames.append(frame_info)
        print(f"  🎥 Created {scenario['name']}: {scenario['description']}")

    return test_frames


def _calculate_quality_metrics(gray):
    """Calculate all quality metrics for a grayscale frame"""
    from skimage import filters
    from skimage.measure import shannon_entropy

    # 1. Sharpness/Blur Detection (Laplacian variance)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

    # 2. Noise Estimation (using high-frequency content)
    high_freq = filters.gaussian(gray.astype(float), sigma=1) - filters.gaussian(
        gray.astype(float), sigma=2
    )
    noise_estimate = np.std(high_freq)

    # 3. Contrast Analysis
    contrast = gray.std()

    # 4. Brightness Analysis
    brightness = gray.mean()

    # 5. Information Content (Shannon Entropy)
    entropy = shannon_entropy(gray)

    # 6. Edge Density (feature richness)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / edges.size

    return {
        "laplacian_var": laplacian_var,
        "noise_estimate": noise_estimate,
        "contrast": contrast,
        "brightness": brightness,
        "entropy": entropy,
        "edge_density": edge_density,
    }


def _calculate_quality_scores(metrics):
    """Calculate quality scores from raw metrics"""
    # Quality scoring (0-100 scale) - improved normalization
    sharpness_score = min(100, max(0, metrics["laplacian_var"] / 3))
    noise_score = max(0, 100 - metrics["noise_estimate"] * 5)
    contrast_score = min(100, max(0, metrics["contrast"] / 1.5))

    # Brightness score - penalize over/under exposure more
    brightness = metrics["brightness"]
    if brightness < 50:  # Underexposed
        brightness_score = brightness * 1.5
    elif brightness > 200:  # Overexposed
        brightness_score = max(0, 100 - (brightness - 200) * 2)
    else:  # Good exposure range
        brightness_score = min(100, 70 + (100 - abs(brightness - 125) / 1.25))

    detail_score = min(100, metrics["entropy"] * 15)

    # Weighted overall quality (emphasize sharpness and contrast for video)
    overall_quality = (
        sharpness_score * 0.3
        + noise_score * 0.2
        + contrast_score * 0.25
        + brightness_score * 0.15
        + detail_score * 0.1
    )

    return {
        "sharpness_score": sharpness_score,
        "noise_score": noise_score,
        "contrast_score": contrast_score,
        "brightness_score": brightness_score,
        "detail_score": detail_score,
        "overall_quality": overall_quality,
    }


def _get_quality_classification(overall_quality):
    """Get quality classification from overall score"""
    if overall_quality >= 70:
        return "High Quality"
    elif overall_quality >= 50:
        return "Medium Quality"
    else:
        return "Low Quality"


def _get_recommendations(scores):
    """Get production recommendations based on scores"""
    recommendations = []
    if scores["sharpness_score"] < 30:
        recommendations.append("Improve focus/reduce blur")
    if scores["noise_score"] < 60:
        recommendations.append("Reduce noise (better lighting/camera)")
    if scores["contrast_score"] < 40:
        recommendations.append("Improve contrast")
    if scores["brightness_score"] < 60:
        recommendations.append("Adjust exposure/lighting")
    return recommendations


def _print_quality_results(frame_data, metrics, scores, analysis_time):
    """Print quality analysis results for a frame"""
    print(f"  ⏱️  Analysis time: {analysis_time:.4f} seconds")
    print("  📊 Quality Metrics:")
    print(
        f"     🔍 Sharpness: {scores['sharpness_score']:.1f}/100 (Laplacian: {metrics['laplacian_var']:.1f})"
    )
    print(
        f"     🌟 Noise Level: {scores['noise_score']:.1f}/100 (Estimate: {metrics['noise_estimate']:.2f})"
    )
    print(f"     📈 Contrast: {scores['contrast_score']:.1f}/100 (Std: {metrics['contrast']:.1f})")
    print(
        f"     💡 Brightness: {scores['brightness_score']:.1f}/100 (Mean: {metrics['brightness']:.1f})"
    )
    print(
        f"     🎯 Detail Level: {scores['detail_score']:.1f}/100 (Entropy: {metrics['entropy']:.2f})"
    )
    print(f"     ⭐ Overall Quality: {scores['overall_quality']:.1f}/100")

    quality_class = _get_quality_classification(scores["overall_quality"])
    print(f"     🏆 Classification: {quality_class}")
    print(f"     ✅ Expected: {frame_data['expected_quality'].title()} Quality")

    recommendations = _get_recommendations(scores)
    if recommendations:
        print(f"     💡 Recommendations: {', '.join(recommendations)}")
    else:
        print("     ✨ No improvements needed - excellent quality!")


def analyze_video_quality(test_frames):
    """Analyze video quality using multiple metrics"""
    print("\n📊 Analyzing Video Quality...")

    try:
        import cv2

        total_analysis_time = 0

        for frame_data in test_frames:
            print(f"\n🎬 Analyzing: {frame_data['name']} - {frame_data['description']}")

            try:
                # Load image
                frame = cv2.imread(frame_data["path"])
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                start_time = time.time()

                # Calculate metrics and scores
                metrics = _calculate_quality_metrics(gray)
                scores = _calculate_quality_scores(metrics)

                analysis_time = time.time() - start_time
                total_analysis_time += analysis_time

                # Print results
                _print_quality_results(frame_data, metrics, scores, analysis_time)

            except Exception as e:
                print(f"  ❌ Error analyzing {frame_data['name']}: {e}")

        # Performance summary
        avg_analysis_time = total_analysis_time / len(test_frames)
        fps_equivalent = 1.0 / avg_analysis_time

        print("\n📊 Performance Summary:")
        print(f"  ⏱️  Average analysis time: {avg_analysis_time:.4f} seconds/frame")
        print(f"  🚀 Processing speed: {fps_equivalent:.1f} fps equivalent")
        print(f"  💡 Real-time capable: {'✅ Yes' if fps_equivalent >= 24 else '❌ No'}")

    except Exception as e:
        print(f"❌ Error in quality analysis: {e}")


def _get_shot_types():
    """Return list of shot type definitions"""
    return [
        {"name": "close_up", "description": "Close-up shot", "person_size": 150},
        {"name": "medium_shot", "description": "Medium shot", "person_size": 100},
        {"name": "wide_shot", "description": "Wide shot", "person_size": 60},
        {"name": "extreme_close_up", "description": "Extreme close-up", "person_size": 200},
        {"name": "establishing_shot", "description": "Establishing/wide shot", "person_size": 30},
    ]


def _draw_extreme_close_up(frame, center_x, center_y, person_size):
    """Draw extreme close-up shot content"""
    cv2.circle(frame, (center_x, center_y), person_size, (255, 200, 150), -1)
    cv2.circle(frame, (center_x - 30, center_y - 20), 15, (50, 50, 50), -1)  # Eyes
    cv2.circle(frame, (center_x + 30, center_y - 20), 15, (50, 50, 50), -1)


def _draw_close_up(frame, center_x, center_y, person_size):
    """Draw close-up shot content"""
    cv2.circle(frame, (center_x, center_y - 50), person_size // 2, (255, 200, 150), -1)
    cv2.rectangle(
        frame,
        (center_x - person_size // 2, center_y),
        (center_x + person_size // 2, center_y + person_size),
        (100, 150, 200),
        -1,
    )


def _draw_medium_shot(frame, center_x, center_y, person_size):
    """Draw medium shot content"""
    cv2.circle(frame, (center_x, center_y - person_size), person_size // 3, (255, 200, 150), -1)
    cv2.rectangle(
        frame,
        (center_x - person_size // 2, center_y - person_size // 2),
        (center_x + person_size // 2, center_y + person_size),
        (100, 150, 200),
        -1,
    )


def _draw_wide_shot(frame, center_x, center_y, person_size):
    """Draw wide shot content"""
    cv2.circle(frame, (center_x, center_y - person_size), person_size // 4, (255, 200, 150), -1)
    cv2.rectangle(
        frame,
        (center_x - person_size // 3, center_y - person_size // 2),
        (center_x + person_size // 3, center_y + person_size),
        (100, 150, 200),
        -1,
    )
    # Add environment
    cv2.rectangle(frame, (50, 50), (1230, 670), (120, 140, 160), 3)  # Room outline


def _draw_establishing_shot(frame, center_x, center_y, person_size):
    """Draw establishing shot content"""
    cv2.circle(frame, (center_x, center_y), person_size // 4, (255, 200, 150), -1)
    cv2.rectangle(
        frame,
        (center_x - person_size // 4, center_y),
        (center_x + person_size // 4, center_y + person_size // 2),
        (100, 150, 200),
        -1,
    )
    # Large environment
    cv2.rectangle(frame, (20, 20), (1260, 700), (100, 120, 140), 5)
    cv2.rectangle(frame, (100, 100), (1180, 620), (140, 160, 180), 3)


def _draw_shot_content(frame, shot, center_x, center_y, person_size):
    """Draw content for specific shot type"""
    if shot["name"] == "extreme_close_up":
        _draw_extreme_close_up(frame, center_x, center_y, person_size)
    elif shot["name"] == "close_up":
        _draw_close_up(frame, center_x, center_y, person_size)
    elif shot["name"] == "medium_shot":
        _draw_medium_shot(frame, center_x, center_y, person_size)
    elif shot["name"] == "wide_shot":
        _draw_wide_shot(frame, center_x, center_y, person_size)
    elif shot["name"] == "establishing_shot":
        _draw_establishing_shot(frame, center_x, center_y, person_size)


def _classify_shot_by_ratio(person_ratio):
    """Classify shot type based on person area ratio"""
    if person_ratio > 0.15:  # Large person in frame
        return "Extreme Close-up"
    elif person_ratio > 0.08:  # Medium-large person
        return "Close-up"
    elif person_ratio > 0.04:  # Medium person
        return "Medium Shot"
    elif person_ratio > 0.015:  # Small person
        return "Wide Shot"
    else:  # Very small person
        return "Establishing Shot"


def _analyze_single_shot(frame_data):
    """Analyze a single shot frame"""
    print(f"\n📹 Analyzing: {frame_data['description']}")

    try:
        frame = cv2.imread(frame_data["path"])
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        start_time = time.time()

        # Improved shot classification based on content analysis
        height, width = gray.shape

        # Use edge detection to find the person outline more accurately
        edges = cv2.Canny(gray, 50, 150)

        # Find contours from edges
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            # Find the largest contour that's likely the person
            valid_contours = [c for c in contours if cv2.contourArea(c) > 100]  # Filter small noise

            if valid_contours:
                largest_contour = max(valid_contours, key=cv2.contourArea)
                person_area = cv2.contourArea(largest_contour)
                frame_area = height * width
                person_ratio = person_area / frame_area

                predicted_shot = _classify_shot_by_ratio(person_ratio)
            else:
                predicted_shot = "Unknown"
                person_ratio = 0
        else:
            predicted_shot = "Unknown"
            person_ratio = 0

        analysis_time = time.time() - start_time

        print(f"  ⏱️  Analysis time: {analysis_time:.4f} seconds")
        print(f"  📊 Person area ratio: {person_ratio:.3f}")
        print(f"  🎯 Predicted shot type: {predicted_shot}")
        print(f"  ✅ Actual shot type: {frame_data['description']}")

        # Check if prediction matches
        actual_normalized = frame_data["name"].replace("_", " ").title()
        match = predicted_shot.lower().replace("-", " ") in actual_normalized.lower()
        print(f"  {'✅' if match else '❌'} Prediction {'correct' if match else 'incorrect'}")

    except Exception as e:
        print(f"  ❌ Error analyzing shot: {e}")


def test_shot_classification():
    """Test shot type classification (close-up, medium, wide)"""
    print("\n🎯 Testing Shot Classification...")

    shot_types = _get_shot_types()
    temp_dir = tempfile.gettempdir()
    shot_frames = []

    # Create frames for each shot type
    for shot in shot_types:
        # Create frame
        frame = np.ones((720, 1280, 3), dtype=np.uint8) * 180  # Gray background
        center_x, center_y = 640, 360
        person_size = shot["person_size"]

        # Draw shot content
        _draw_shot_content(frame, shot, center_x, center_y, person_size)

        # Save frame
        frame_path = os.path.join(temp_dir, f"shot_{shot['name']}.jpg")
        cv2.imwrite(frame_path, frame)
        shot_frames.append(
            {"path": frame_path, "name": shot["name"], "description": shot["description"]}
        )

        print(f"  🎥 Created {shot['description']}")

    # Analyze shot types
    print("\n🎬 Analyzing Shot Types...")

    for frame_data in shot_frames:
        _analyze_single_shot(frame_data)

    # Cleanup
    for frame_data in shot_frames:
        try:
            os.remove(frame_data["path"])
        except OSError:
            pass


def main():
    """Main test function"""
    print("🔥 Video Quality Assessment Test Suite")
    print("=" * 50)

    # Test 1: Library installations
    libs = test_video_quality_libs()
    if not libs["opencv"] or not libs["skimage"]:
        print("❌ Required libraries missing. Please install them first.")
        return

    # Test 2: Create test frames
    test_frames = create_test_videos()

    # Test 3: Quality analysis
    analyze_video_quality(test_frames)

    # Test 4: Shot classification
    test_shot_classification()

    print("\n" + "=" * 50)
    print("🎉 Video Quality Assessment tests completed!")
    print("\n💡 Next steps:")
    print("   - Add quality assessment to main API (app.py)")
    print("   - Create /api/gpu-video-quality endpoint")
    print("   - Integrate with video processing pipeline")
    print("   - Combine with CLIP for semantic shot classification")

    # Cleanup
    for frame_data in test_frames:
        try:
            os.remove(frame_data["path"])
        except OSError:
            pass


if __name__ == "__main__":
    main()
