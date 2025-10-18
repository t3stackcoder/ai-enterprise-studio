"""
The Anand-Svidler Position Test
Complex positional puzzle - Will they find Bb2?
"""

import asyncio
import json
import time

import websockets


async def test_position(websocket, fen, engine, seconds):
    """Test a position with an engine"""
    request = {"type": "analyze", "fen": fen, "engine": engine, "movetime": seconds * 1000}

    print(f"{'='*60}")
    print(f"🔥 {engine.upper()}: Analyzing for {seconds} seconds...")
    print(f"{'='*60}")

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

        print(f"\n✅ {engine.upper()} RESULT:")
        print(f"   🎯 Best move: {best_move}")

        # Check if it found Bb2 (d3b2)
        if best_move == "d3b2":
            print("   ✨ FOUND IT! The quiet Bb2!")
        else:
            print("   ❓ Different move (expected: d3b2 / Bb2)")

        print(f"   📈 Evaluation: {evaluation}")
        print(f"   📏 Depth: {depth}")
        print(f"   📊 Nodes: {nodes:,}")
        print(f"   🎮 Principal Variation: {' '.join(pv[:5])}")
        print(f"   ⏱️  Time: {elapsed:.1f}s")
        print()

    return result


async def anand_svidler_test():
    """Test the famous Anand-Svidler position"""

    uri = "ws://localhost:8001"

    print("\n" + "=" * 60)
    print("🏆 THE ANAND-SVIDLER POSITION TEST (2005)")
    print("=" * 60)
    print("Position: Complex middlegame requiring positional finesse")
    print("Solution: Bb2 (quiet, improving move)")
    print("Challenge: Not the most forcing move")
    print("=" * 60)

    fen = "2brk2r/pp2bppp/2n1pn2/2p5/2P5/1P1BPN2/P1Q2PPP/RNB2RK1 w K - 0 12"

    print("\nFEN: " + fen)
    print()

    async with websockets.connect(uri) as websocket:

        # Test Stockfish first (120 seconds)
        sf_result = await test_position(websocket, fen, "stockfish", 120)

        print("\n" + "=" * 60 + "\n")

        # Test Leela (120 seconds)
        lc0_result = await test_position(websocket, fen, "leela", 120)

        # Compare
        print("=" * 60)
        print("🎯 COMPARISON")
        print("=" * 60)

        sf_move = sf_result.get("result", {}).get("best_move", "")
        lc0_move = lc0_result.get("result", {}).get("best_move", "")

        print(f"🐟 Stockfish: {sf_move}")
        print(f"🧠 Leela:     {lc0_move}")
        print("✅ Expected:  d3b2 (Bb2)")
        print()

        if sf_move == "d3b2":
            print("🐟 Stockfish FOUND the quiet move!")
        else:
            print(f"🐟 Stockfish prefers: {sf_move}")

        if lc0_move == "d3b2":
            print("🧠 Leela FOUND the quiet move!")
        else:
            print(f"🧠 Leela prefers: {lc0_move}")

        print()

        if sf_move == lc0_move:
            print("🤝 Both engines agree!")
        else:
            print("⚔️  Engines disagree - interesting position!")

        print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(anand_svidler_test())
    except Exception as e:
        print(f"❌ Error: {e}")
