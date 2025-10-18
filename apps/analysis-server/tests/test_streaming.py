"""
Test real-time streaming analysis
"""

import asyncio
import json

import websockets


async def test_streaming_analysis():
    """Test streaming analysis with real-time updates"""

    uri = "ws://localhost:8001"

    # Test position (Fischer's Game of the Century)
    fen = "r4rk1/pp3pbp/1qp3p1/2B5/2BP2b1/Q1n2N2/P4PPP/3R1K1R b - - 4 17"

    print("=" * 60)
    print("🔥 REAL-TIME STREAMING ANALYSIS TEST")
    print("=" * 60)
    print(f"FEN: {fen}")
    print("Connecting to server...")
    print()

    async with websockets.connect(uri) as websocket:

        # Send analysis request with streaming enabled and INFINITE mode
        request = {
            "type": "analyze",
            "fen": fen,
            "engine": "stockfish",
            "multipv": 3,  # Show top 3 candidate moves
            "stream": True,  # Enable real-time updates
            "infinite": True,  # INFINITE ANALYSIS MODE
        }

        print("📡 Sending INFINITE analysis request (MultiPV=3)...")
        print("⚠️  Will auto-stop after 50 updates for testing...")
        await websocket.send(json.dumps(request))

        update_count = 0
        max_updates = 50  # Stop after 50 updates to test infinite mode

        # Receive updates
        async for message in websocket:
            data = json.loads(message)

            if data.get("type") == "analysis_update":
                update_count += 1
                depth = data.get("depth", 0)
                nodes = data.get("nodes", 0)
                lines = data.get("lines", [])

                # Stop infinite analysis after max_updates for testing
                if update_count >= max_updates:
                    print(f"\n⏹️  Reached {max_updates} updates, manually stopping test...")
                    print("   (In real usage, infinite mode keeps running until new position sent)")
                    break

                # Print updates (limit to every 10 to avoid spam)
                if update_count % 10 == 0 and lines:
                    print(f"\n📊 Update #{update_count} - Depth {depth}, Nodes {nodes:,}")
                    for i, line in enumerate(lines[:3], 1):
                        move = line.get("move", "")
                        evaluation = line.get("evaluation", "")
                        pv = " ".join(line.get("pv", [])[:12])  # Display first 12 moves
                        print(f"   {i}. {move:6} ({evaluation:+6.2f}) {pv}")

            elif data.get("type") == "analysis_result":
                print()
                print("=" * 60)
                print("✅ FINAL RESULT:")
                result = data.get("result", {})
                print(f"   🎯 Best move: {result.get('best_move')}")
                print(f"   📈 Evaluation: {result.get('evaluation')}")
                print(f"   📏 Depth: {result.get('depth')}")
                print(f"   📊 Nodes: {result.get('nodes', 0):,}")

                # Show all MultiPV lines if available
                multipv = result.get("multipv", [])
                if multipv:
                    print("\n   📋 Top 3 Candidate Moves:")
                    for i, line in enumerate(multipv[:3], 1):
                        move = line.get("move", "")
                        evaluation = line.get("evaluation", "")
                        pv = " ".join(line.get("pv", [])[:12])  # Display first 12 moves
                        print(f"      {i}. {move:6} ({evaluation:+6.2f}) {pv}")
                else:
                    print(
                        f"   🎮 PV: {' '.join(result.get('pv', [])[:12])}"
                    )  # Display first 12 moves

                print(f"\n   📡 Total updates received: {update_count}")
                print("=" * 60)
                break

            elif data.get("type") == "error":
                print(f"❌ Error: {data.get('message')}")
                break

        # If we broke out of infinite mode, show summary
        if update_count > 0:
            print("\n" + "=" * 60)
            print("✅ INFINITE MODE TEST SUMMARY:")
            print(f"   📡 Total updates received: {update_count}")
            print("   ✅ Infinite analysis was running continuously")
            print("   ✅ Test manually stopped after target updates")
            print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(test_streaming_analysis())
    except Exception as e:
        print(f"❌ Error: {e}")
