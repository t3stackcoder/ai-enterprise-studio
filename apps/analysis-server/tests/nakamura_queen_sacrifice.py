"""
Nakamura's Brilliant Queen Sacrifice!
2007, Krasenkow vs Nakamura - Casino de Barcelona
Will the engines find Qxf2+!! leading to a king hunt?
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

        # Check if it found Qxf2+ (the queen sacrifice)
        if best_move == "b6f2":
            print("   ✨✨✨ FOUND IT! Nakamura's brilliant Qxf2+!! queen sacrifice!")
        else:
            print("   ❓ Different move (expected: Qxf2+!!)")

        print(f"   📈 Evaluation: {evaluation}")
        print(f"   📏 Depth: {depth}")
        print(f"   📊 Nodes: {nodes:,}")
        print(f"   🎮 Principal Variation: {' '.join(pv[:10])}")
        print(f"   ⏱️  Time: {elapsed:.1f}s")
        print()

    return result


async def nakamura_sacrifice_test():
    """Test Nakamura's brilliant queen sacrifice"""

    uri = "ws://localhost:8765"

    print("\n" + "=" * 60)
    print("👑 NAKAMURA'S QUEEN SACRIFICE - KING HUNT 👑")
    print("=" * 60)
    print("Krasenkow vs Nakamura, Casino de Barcelona, 2007")
    print("Position: Move 21, before Nakamura's queen sacrifice")
    print("Solution: Qxf2+!! (the brilliant queen sacrifice)")
    print("Result: One of Nakamura's finest games")
    print("=" * 60)

    fen = "4r1k1/3nbppp/bqr2B2/p7/2p5/6P1/P2N1PBP/1R1QR1K1 b - - 0 21"

    print("\nFEN: " + fen)
    print("Black to move (Nakamura)")
    print()

    async with websockets.connect(uri) as websocket:

        # Test Stockfish (30 seconds)
        print("Testing with 30 seconds each...\n")
        sf_result = await test_position(websocket, fen, "stockfish", 30)

        print("\n" + "=" * 60 + "\n")

        # Test Leela (30 seconds)
        lc0_result = await test_position(websocket, fen, "leela", 30)

        # Compare
        print("=" * 60)
        print("🎯 COMPARISON - Did they find Nakamura's brilliancy?")
        print("=" * 60)

        sf_move = sf_result.get("result", {}).get("best_move", "")
        lc0_move = lc0_result.get("result", {}).get("best_move", "")

        print(f"🐟 Stockfish: {sf_move}")
        print(f"🧠 Leela:     {lc0_move}")
        print("👑 Nakamura:  b6f2 (Qxf2+!!)")
        print()

        sf_found = sf_move == "b6f2"
        lc0_found = lc0_move == "b6f2"

        if sf_found:
            print("🐟 Stockfish FOUND Nakamura's Queen sacrifice!")
        else:
            print(f"🐟 Stockfish prefers: {sf_move}")

        if lc0_found:
            print("🧠 Leela FOUND Nakamura's Queen sacrifice!")
        else:
            print(f"🧠 Leela prefers: {lc0_move}")

        print()

        if sf_found and lc0_found:
            print("🏆 Both engines found the brilliant queen sacrifice!")
        elif sf_move == lc0_move:
            print("🤝 Both engines agree (but not Nakamura's move)")
        else:
            print("⚔️  Engines disagree!")

        print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(nakamura_sacrifice_test())
    except Exception as e:
        print(f"❌ Error: {e}")
