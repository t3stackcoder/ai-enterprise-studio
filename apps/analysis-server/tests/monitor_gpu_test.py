"""
Monitor GPU while Leela analyzes
"""

import asyncio
import json
import time

import websockets


async def monitor_gpu_during_analysis():
    """Run analysis and monitor GPU at the same time"""

    uri = "ws://localhost:8001"

    print("🔥 GPU MONITORING TEST 🔥\n")

    async with websockets.connect(uri) as websocket:
        complex_fen = "r2q1rk1/ppp2ppp/2n1bn2/2bpp3/4P3/2PP1N2/PPB1NPPP/R1BQ1RK1 w - - 0 10"

        print("Starting 30 SECOND analysis...")
        print("While it runs, open another terminal and run: nvidia-smi\n")

        max_request = {
            "type": "analyze",
            "fen": complex_fen,
            "engine": "leela",
            "movetime": 30000,  # 30 SECONDS!
        }

        start = time.time()
        await websocket.send(json.dumps(max_request))

        print("🔊 GPU IS NOW WORKING FOR 30 SECONDS!")
        print("🏃 Quick! Open PowerShell and run: nvidia-smi")
        print("⏰ You have 30 seconds to check...\n")

        response = await websocket.recv()
        elapsed = time.time() - start
        result = json.loads(response)

        print(f"\n⏱️  Analysis took {elapsed:.1f} seconds")

        if result.get("type") == "analysis_result":
            nodes = result["result"].get("nodes", 0)
            print(f"💪 Analyzed {nodes:,} nodes!")
            print(f"🚀 NPS: {int(nodes/elapsed):,}")


if __name__ == "__main__":
    try:
        asyncio.run(monitor_gpu_during_analysis())
    except Exception as e:
        print(f"❌ Error: {e}")
