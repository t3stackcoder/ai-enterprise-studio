"""
Stockfish vs Leela - Head to Head Performance Test!
"""

import asyncio
import json
import time

import websockets


async def analyze_position(websocket, fen, engine, seconds):
    """Analyze one position with specified engine"""
    request = {"type": "analyze", "fen": fen, "engine": engine, "movetime": seconds * 1000}

    print(f"🔥 {engine.upper()}: Starting {seconds}s analysis...")
    start = time.time()
    await websocket.send(json.dumps(request))
    response = await websocket.recv()
    elapsed = time.time() - start
    result = json.loads(response)

    if result.get("type") == "analysis_result":
        nodes = result["result"].get("nodes", 0)
        depth = result["result"].get("depth", 0)
        best_move = result["result"].get("best_move", "")
        evaluation = result["result"].get("evaluation", "")

        print(f"✅ {engine.upper()}: {nodes:,} nodes in {elapsed:.1f}s")
        print(f"   📊 {int(nodes/elapsed):,} nodes/sec")
        print(f"   📏 Depth: {depth}")
        print(f"   ♟️  Best move: {best_move}")
        print(f"   📈 Eval: {evaluation}")
        print()
    return result, elapsed, result.get("result", {}).get("nodes", 0)


async def head_to_head():
    """Compare Stockfish CPU vs Leela GPU"""

    uri = "ws://localhost:8001"

    print("⚔️  STOCKFISH vs LEELA - HEAD TO HEAD! ⚔️")
    print("=" * 60)
    print("Testing same position with both engines")
    print("60 seconds each engine")
    print("=" * 60)
    print()

    # Complex middlegame position
    test_fen = "r1bqk2r/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R1BQK2R w KQkq - 0 8"

    async with websockets.connect(uri) as websocket:

        # Test Stockfish
        print("🐟 TESTING STOCKFISH (CPU)")
        print("=" * 60)
        sf_result, sf_time, sf_nodes = await analyze_position(websocket, test_fen, "stockfish", 60)

        print("\n" + "=" * 60 + "\n")

        # Test Leela
        print("🧠 TESTING LEELA CHESS ZERO (GPU)")
        print("=" * 60)
        lc0_result, lc0_time, lc0_nodes = await analyze_position(websocket, test_fen, "leela", 60)

        # Results
        print("\n" + "=" * 60)
        print("🏆 FINAL RESULTS")
        print("=" * 60)
        print("🐟 Stockfish (CPU):")
        print(f"   Nodes:     {sf_nodes:,}")
        print(f"   NPS:       {int(sf_nodes/sf_time):,}")
        print()
        print("🧠 Leela (GPU):")
        print(f"   Nodes:     {lc0_nodes:,}")
        print(f"   NPS:       {int(lc0_nodes/lc0_time):,}")
        print()
        print(f"📊 Node Count Winner: {'Stockfish 🐟' if sf_nodes > lc0_nodes else 'Leela 🧠'}")
        print(f"   Stockfish analyzed {sf_nodes/lc0_nodes:.1f}x more nodes")
        print()
        print("💡 Remember: More nodes ≠ Better moves!")
        print("   Stockfish = Brute force search (MANY nodes)")
        print("   Leela = Smart neural network (FEWER nodes, deep understanding)")
        print("=" * 60)


if __name__ == "__main__":
    try:
        print("\n⏰ Starting in 3 seconds...\n")
        import time

        time.sleep(3)
        asyncio.run(head_to_head())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
