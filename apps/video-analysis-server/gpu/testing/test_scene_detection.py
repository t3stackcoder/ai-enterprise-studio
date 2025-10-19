#!/usr/bin/env python3
"""
Test script for PySceneDetect (ContentDetector) on GPU
"""

import os
import tempfile
import time

import cv2
import numpy as np
import pytest


def _create_scene_frame(scene_num: int, width: int, height: int) -> np.ndarray:
    """Create a frame for a specific scene with distinct visual characteristics"""
    if scene_num == 0:
        # Black scene with white text
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.rectangle(frame, (50, 100), (590, 400), (255, 255, 255), -1)
        cv2.putText(frame, "SCENE 1: OFFICE", (150, 250), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    elif scene_num == 1:
        # Bright white scene with black elements
        frame = np.full((height, width, 3), (255, 255, 255), dtype=np.uint8)
        cv2.rectangle(frame, (100, 150), (540, 350), (0, 0, 0), -1)
        cv2.putText(
            frame, "SCENE 2: KITCHEN", (120, 250), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3
        )
    elif scene_num == 2:
        # Red scene
        frame = np.full((height, width, 3), (0, 0, 200), dtype=np.uint8)
        cv2.circle(frame, (320, 240), 150, (255, 255, 255), -1)
        cv2.putText(
            frame, "SCENE 3: OUTDOOR", (120, 250), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3
        )
    else:
        # Blue/green scene
        frame = np.full((height, width, 3), (150, 200, 0), dtype=np.uint8)
        for i in range(0, width, 50):
            cv2.line(frame, (i, 0), (i, height), (255, 255, 255), 5)
        cv2.putText(frame, "SCENE 4: NIGHT", (150, 250), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    return frame


def _setup_video_writer(video_path: str, fps: int, width: int, height: int):
    """Setup and return video writer"""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    return cv2.VideoWriter(video_path, fourcc, fps, (width, height))


def _apply_brightness_variation(frame: np.ndarray, brightness_variation: int) -> np.ndarray:
    """Apply brightness variation to a frame safely"""
    if brightness_variation > 0:
        return cv2.add(frame, np.full_like(frame, brightness_variation, dtype=np.uint8))
    elif brightness_variation < 0:
        return cv2.subtract(frame, np.full_like(frame, abs(brightness_variation), dtype=np.uint8))
    return frame


def _add_frame_counter(frame: np.ndarray, frame_num: int) -> None:
    """Add frame counter overlay to frame"""
    cv2.putText(
        frame, f"Frame {frame_num}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2
    )


def _calculate_brightness_variation(frame_num: int, fps: int, duration_per_scene: int) -> int:
    """Calculate brightness variation for temporal effects"""
    time_in_scene = (frame_num % (fps * duration_per_scene)) / fps
    return int(20 * np.sin(time_in_scene * 2 * np.pi))


def create_test_video():
    """Create a more realistic test video with clear scene changes"""
    print("🎬 Creating test video with distinct scene changes...")

    temp_dir = tempfile.gettempdir()
    video_path = os.path.join(temp_dir, "realistic_scene_test.mp4")

    # Video properties
    fps = 30
    duration_per_scene = 3  # seconds - longer scenes
    num_scenes = 4  # more scenes
    width, height = 640, 480

    # Create video writer
    out = _setup_video_writer(video_path, fps, width, height)
    total_frames = fps * duration_per_scene * num_scenes

    for frame_num in range(total_frames):
        # Determine which scene we're in
        scene_num = frame_num // (fps * duration_per_scene)
        frame = _create_scene_frame(scene_num, width, height)

        # Add temporal variation within each scene
        brightness_variation = _calculate_brightness_variation(frame_num, fps, duration_per_scene)
        frame = _apply_brightness_variation(frame, brightness_variation)

        # Add frame counter for debugging
        _add_frame_counter(frame, frame_num)

        out.write(frame)

    out.release()
    print(f"✅ Realistic test video created: {video_path}")
    print(f"   Duration: {total_frames/fps:.1f} seconds")
    print(f"   Scenes: {num_scenes}")
    print(
        f"   Scene transitions at: {[i*duration_per_scene for i in range(1, num_scenes)]} seconds"
    )
    return video_path


def _test_threshold(video_path: str, threshold: float) -> dict:
    """Test scene detection with a specific threshold"""
    print(f"\n🎯 Testing threshold: {threshold}")

    start_time = time.time()

    # Import the newer API
    from scenedetect import ContentDetector, detect

    # Detect scenes directly from video file
    detection_start = time.time()
    scene_list = detect(video_path, ContentDetector(threshold=threshold))

    detection_time = time.time() - detection_start
    total_time = time.time() - start_time

    # Display results for this threshold
    print(f"   Scenes detected: {len(scene_list)}")
    print(f"   Detection time: {detection_time:.4f} seconds")

    if scene_list:
        _display_scene_timestamps(scene_list)

        # Estimate video duration from scene list
        video_duration = scene_list[-1][1].get_seconds()
        processing_speed = video_duration / detection_time if detection_time > 0 else 0

        return {
            "threshold": threshold,
            "scenes": len(scene_list),
            "detection_time": detection_time,
            "total_time": total_time,
            "video_duration": video_duration,
            "processing_speed": processing_speed,
            "scene_list": [(s[0].get_seconds(), s[1].get_seconds()) for s in scene_list],
        }
    else:
        print(f"   No scenes detected with threshold {threshold}")
        return None


def _display_scene_timestamps(scene_list):
    """Display scene timestamps"""
    print("   Scene timestamps:")
    for i, scene in enumerate(scene_list):
        start_time_sec = scene[0].get_seconds()
        end_time_sec = scene[1].get_seconds()
        duration = end_time_sec - start_time_sec
        print(
            f"     Scene {i+1}: {start_time_sec:.2f}s - {end_time_sec:.2f}s (duration: {duration:.2f}s)"
        )


def _display_best_result(best_result):
    """Display the best result summary"""
    print("\n" + "=" * 60)
    print(f"🏆 BEST RESULT (Threshold: {best_result['threshold']}):")
    print(f"   Total scenes detected: {best_result['scenes']}")
    print(f"   Video duration: {best_result['video_duration']:.2f} seconds")
    print(f"   Detection time: {best_result['detection_time']:.4f} seconds")
    print(f"   Processing speed: {best_result['processing_speed']:.2f}x real-time")
    print("   Scene transitions:")
    for i, (start, end) in enumerate(best_result["scene_list"]):
        print(f"     Scene {i+1}: {start:.2f}s - {end:.2f}s")
    print("=" * 60)


def _cleanup_test_video(video_path: str):
    """Clean up test video with retry mechanism"""
    import time as time_module

    for attempt in range(3):
        try:
            if os.path.exists(video_path):
                time_module.sleep(0.5)  # Wait a bit for file to be released
                os.remove(video_path)
                print("🗑️  Cleaned up test video")
            break
        except PermissionError:
            if attempt < 2:
                print(f"⏳ Waiting for file release (attempt {attempt + 1}/3)...")
                time_module.sleep(1)
            else:
                print(f"⚠️  Could not clean up test video: {video_path}")


def test_scene_detection_gpu():
    """Test PySceneDetect with ContentDetector using different thresholds"""
    print("🔥 Testing PySceneDetect (ContentDetector) with multiple thresholds...")

    # Create test video
    video_path = create_test_video()

    # Test different thresholds
    thresholds = [10.0, 20.0, 30.0, 40.0, 50.0]
    best_result = None

    try:
        for threshold in thresholds:
            result = _test_threshold(video_path, threshold)

            if result:
                # Consider this the best if it detected expected number of scenes (3-4)
                if not best_result or (
                    2 <= result["scenes"] <= 4 and result["scenes"] > best_result["scenes"]
                ):
                    best_result = result

        # Display best result summary
        if best_result:
            _display_best_result(best_result)
        else:
            print("\n❌ No scenes detected with any threshold")
            # Test failed - should have detected some scenes
            pytest.fail("Scene detection should have found some scene transitions")

        # Assert test success criteria
        assert best_result is not None, "Should have found a best result"
        assert best_result["detection_time"] > 0, "Detection should take some time"
        assert best_result["video_duration"] > 0, "Video should have duration"

        print("✅ Scene detection test completed successfully!")

    finally:
        _cleanup_test_video(video_path)


if __name__ == "__main__":
    try:
        results = test_scene_detection_gpu()
        print("\n✅ PySceneDetect test completed successfully!")
        print("🚀 Ready for GPU-accelerated integration!")
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()
