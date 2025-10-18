"""
Fischer's "Game of the Century" - The Queen Sacrifice!
1956, Fischer (age 13) vs Donald Byrne
Will the engines find Be6!! sacrificing the Queen?
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

        # Check if it found Be6 (g4e6)
        if best_move == "g4e6":
            print("   ✨✨✨ FOUND IT! The legendary Be6 Queen sacrifice!")
        else:
            print("   ❓ Different move (expected: g4e6 / Be6!!)")

        print(f"   📈 Evaluation: {evaluation}")
        print(f"   📏 Depth: {depth}")
        print(f"   📊 Nodes: {nodes:,}")
        print(f"   🎮 Principal Variation: {' '.join(pv[:1])}")
        print(f"   ⏱️  Time: {elapsed:.1f}s")
        print()

    return result


async def game_of_the_century_test():
    """Test Fischer's immortal Queen sacrifice"""

    uri = "ws://localhost:8765"

    print("\n" + "=" * 60)
    print("👑 FISCHER'S 'GAME OF THE CENTURY' 👑")
    print("=" * 60)
    print("Fischer (age 13!) vs Donald Byrne, 1956")
    print("Position: Right before the legendary Queen sacrifice")
    print("Solution: Be6!! (sacrificing the Queen)")
    print("Result: Fischer won with a brilliant attack")
    print("=" * 60)

    fen = "r4rk1/pp3pbp/1qp3p1/2B5/2BP2b1/Q1n2N2/P4PPP/3R1K1R b - - 4 17"

    print("\nFEN: " + fen)
    print("Black to move (Fischer)")
    print()

    async with websockets.connect(uri) as websocket:

        # Test Stockfish (180 seconds)
        print("Testing with 180 seconds each...\n")
        sf_result = await test_position(websocket, fen, "stockfish", 180)

        print("\n" + "=" * 60 + "\n")

        # Test Leela (180 seconds)
        lc0_result = await test_position(websocket, fen, "leela", 180)

        # Compare
        print("=" * 60)
        print("🎯 COMPARISON - Did they find Fischer's brilliancy?")
        print("=" * 60)

        sf_move = sf_result.get("result", {}).get("best_move", "")
        lc0_move = lc0_result.get("result", {}).get("best_move", "")

        print(f"🐟 Stockfish: {sf_move}")
        print(f"🧠 Leela:     {lc0_move}")
        print("👑 Fischer:   g4e6 (Be6!!)")
        print()

        if sf_move == "g4e6":
            print("🐟 Stockfish FOUND Fischer's Queen sacrifice!")
        else:
            print(f"🐟 Stockfish prefers: {sf_move}")

        if lc0_move == "g4e6":
            print("🧠 Leela FOUND Fischer's Queen sacrifice!")
        else:
            print(f"🧠 Leela prefers: {lc0_move}")

        print()

        if sf_move == lc0_move == "g4e6":
            print("🏆 Both engines found the immortal move!")
        elif sf_move == lc0_move:
            print("🤝 Both engines agree (but not Fischer's move)")
        else:
            print("⚔️  Engines disagree!")

        print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(game_of_the_century_test())
    except Exception as e:
        print(f"❌ Error: {e}")
