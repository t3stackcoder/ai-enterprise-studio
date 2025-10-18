"""
Heavy GPU test - Push Leela harder to hear that fan!
"""

import asyncio
import json

import websockets


async def heavy_gpu_test():
    """Run intensive Leela analysis to spin up GPU fans"""

    uri = "ws://localhost:8001"

    print("🔥 HEAVY GPU TEST - Let's make that RTX 3080 WORK! 🔥\n")

    async with websockets.connect(uri) as websocket:
        # Complex middle game position
        complex_fen = "r1bq1rk1/pp2bppp/2n1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 0 10"

        print("📤 Sending HEAVY analysis request:")
        print("   - Engine: Leela Chess Zero")
        print("   - Depth: 25 (more nodes!)")
        print("   - Position: Complex middlegame")
        print("\n⏳ Starting analysis... LISTEN FOR THE FAN! 🌪️\n")

        heavy_request = {
            "type": "analyze",
            "fen": complex_fen,
            "engine": "leela",
            "depth": 25,  # Much deeper = more GPU work!
        }

        await websocket.send(json.dumps(heavy_request))

        print("🔊 GPU is working...")
        response = await websocket.recv()
        result = json.loads(response)

        print("\n📥 Result:")
        print(json.dumps(result, indent=2))

        if result.get("type") == "analysis_result":
            nodes = result["result"].get("nodes", 0)
            print(f"\n💪 Analyzed {nodes:,} nodes!")
            if nodes > 10000:
                print("🔥 That should have made the GPU work!")


if __name__ == "__main__":
    try:
        asyncio.run(heavy_gpu_test())
    except Exception as e:
        print(f"❌ Error: {e}")
