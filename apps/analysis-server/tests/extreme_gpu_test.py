"""
EXTREME GPU TORTURE TEST - Push to the LIMIT!
Multiple long analyses in parallel!
"""

import asyncio
import json
import time

import websockets


async def analyze_position(websocket, fen, position_name, seconds):
    """Analyze one position"""
    request = {"type": "analyze", "fen": fen, "engine": "leela", "movetime": seconds * 1000}

    print(f"🔥 {position_name}: Starting {seconds}s analysis...")
    start = time.time()
    await websocket.send(json.dumps(request))
    response = await websocket.recv()
    elapsed = time.time() - start
    result = json.loads(response)

    if result.get("type") == "analysis_result":
        nodes = result["result"].get("nodes", 0)
        print(f"✅ {position_name}: {nodes:,} nodes in {elapsed:.1f}s ({int(nodes/elapsed):,} nps)")
    return result


async def extreme_gpu_torture():
    """Push GPU to absolute maximum with long analysis"""

    uri = "ws://localhost:8001"

    print("🔥🔥🔥 EXTREME GPU TORTURE TEST 🔥🔥🔥")
    print("=" * 60)
    print("⚠️  WARNING: This will run for 60 SECONDS")
    print("⚠️  Your GPU will work HARD")
    print("⚠️  Fans WILL spin up!")
    print("=" * 60)
    print()

    # Super complex positions
    positions = [
        (
            "r1bqk2r/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R1BQK2R w KQkq - 0 8",
            "Complex Middlegame",
        ),
    ]

    async with websockets.connect(uri) as websocket:
        print("🚀 Starting 60 SECOND torture test...")
        print("👂 PUT YOUR EAR NEAR THE COMPUTER!")
        print("🌪️  FANS SHOULD SPIN UP IN 10-15 SECONDS...")
        print()

        start_time = time.time()

        # Single long analysis to really heat it up
        await analyze_position(websocket, positions[0][0], positions[0][1], 60)  # 60 FULL SECONDS!

        total_time = time.time() - start_time

        print()
        print("=" * 60)
        print(f"⏱️  Total time: {total_time:.1f} seconds")
        print("🔥 GPU TEMPERATURE SHOULD HAVE RISEN!")
        print("🌪️  DID YOU HEAR THE FANS?!")
        print("=" * 60)


if __name__ == "__main__":
    try:
        print("\n⏰ Starting in 3 seconds... Get ready to listen!\n")
        import time

        time.sleep(3)
        asyncio.run(extreme_gpu_torture())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
