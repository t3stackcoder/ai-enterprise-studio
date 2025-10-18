"""
MAXIMUM GPU STRESS TEST - Make it ROAR!
"""

import asyncio
import json
import time

import websockets


async def max_gpu_test():
    """Push Leela to the absolute limit!"""

    uri = "ws://localhost:8001"

    print("🔥🔥🔥 MAXIMUM GPU STRESS TEST 🔥🔥🔥")
    print("Your RTX 3080 is about to WORK!\n")

    async with websockets.connect(uri) as websocket:
        # Super complex position
        complex_fen = "r2q1rk1/ppp2ppp/2n1bn2/2bpp3/4P3/2PP1N2/PPB1NPPP/R1BQ1RK1 w - - 0 10"

        print("📤 Sending MAXIMUM analysis request:")
        print("   - Engine: Leela Chess Zero")
        print("   - Time limit: 10 SECONDS of pure GPU work")
        print("   - Position: Super complex middlegame")
        print("\n⏳ Starting... PUT YOUR EAR NEAR THE CASE! 👂\n")

        max_request = {
            "type": "analyze",
            "fen": complex_fen,
            "engine": "leela",
            "movetime": 10000,  # 10 SECONDS of analysis!
        }

        start = time.time()
        await websocket.send(json.dumps(max_request))

        print("🔊 GPU WORKING HARD...")
        print("🌪️  LISTEN FOR THE FAN...")
        print("🔥 10 SECONDS OF PURE NEURAL NETWORK POWER...\n")

        response = await websocket.recv()
        elapsed = time.time() - start
        result = json.loads(response)

        print(f"\n⏱️  Analysis took {elapsed:.1f} seconds")
        print("\n📥 Result:")
        print(json.dumps(result, indent=2))

        if result.get("type") == "analysis_result":
            nodes = result["result"].get("nodes", 0)
            print(f"\n💪 Analyzed {nodes:,} nodes!")
            print(f"🚀 Nodes per second: {int(nodes/elapsed):,}")
            if nodes > 50000:
                print("🔥🔥🔥 THAT DEFINITELY MADE THE GPU WORK! 🔥🔥🔥")


if __name__ == "__main__":
    try:
        asyncio.run(max_gpu_test())
    except Exception as e:
        print(f"❌ Error: {e}")
