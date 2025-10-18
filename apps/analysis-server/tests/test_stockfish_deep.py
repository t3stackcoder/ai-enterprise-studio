"""
Test just Stockfish on Anand-Svidler
"""

import asyncio
import json
import time

import websockets


async def test_stockfish_deep():
    uri = "ws://localhost:8001"

    print("🐟 STOCKFISH - Deep Analysis (2 minutes)")
    print("=" * 60)

    fen = "2brk2r/pp2bppp/2n1pn2/2p5/2P5/1P1BPN2/P1Q2PPP/RNB2RK1 w K - 0 12"

    async with websockets.connect(uri) as websocket:
        request = {"type": "analyze", "fen": fen, "engine": "stockfish", "movetime": 120000}

        print("Starting analysis...")
        start = time.time()
        await websocket.send(json.dumps(request))
        response = await websocket.recv()
        elapsed = time.time() - start
        result = json.loads(response)

        if result.get("type") == "analysis_result":
            best_move = result["result"].get("best_move", "")
            evaluation = result["result"].get("evaluation", "")
            nodes = result["result"].get("nodes", 0)
            depth = result["result"].get("depth", 0)
            pv = result["result"].get("pv", [])

            print("\n✅ RESULT:")
            print(f"   Best move: {best_move}")
            print(f"   Evaluation: {evaluation}")
            print(f"   Depth: {depth}")
            print(f"   Nodes: {nodes:,}")
            print(f"   NPS: {int(nodes/elapsed):,}")
            print(f"   PV: {' '.join(pv[:8])}")
            print(f"   Time: {elapsed:.1f}s")

            if best_move == "d3b2":
                print("\n   ✨ FOUND Bb2!")
            else:
                print("\n   Different from Bb2 (d3b2)")


if __name__ == "__main__":
    try:
        asyncio.run(test_stockfish_deep())
    except Exception as e:
        print(f"❌ Error: {e}")
