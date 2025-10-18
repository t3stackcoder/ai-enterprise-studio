"""
Test client for Chess Analysis Service
Tests both Stockfish and Leela Chess Zero
"""

import asyncio
import json

import websockets


async def test_analysis():
    """Connect to server and test both engines"""

    uri = "ws://localhost:8001"

    print("🔌 Connecting to Chess Analysis Service...")

    async with websockets.connect(uri) as websocket:
        print("✅ Connected!\n")

        # Starting position
        starting_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

        # Test 1: Stockfish Analysis
        print("=" * 60)
        print("🐟 TESTING STOCKFISH")
        print("=" * 60)

        stockfish_request = {
            "type": "analyze",
            "fen": starting_fen,
            "engine": "stockfish",
            "depth": 20,
        }

        print(f"📤 Sending request: {json.dumps(stockfish_request, indent=2)}")
        await websocket.send(json.dumps(stockfish_request))

        print("⏳ Waiting for Stockfish analysis...")
        response = await websocket.recv()
        result = json.loads(response)

        print("\n📥 Stockfish Result:")
        print(json.dumps(result, indent=2))
        print()

        # Test 2: Leela Analysis (this will spin up your GPU!)
        print("=" * 60)
        print("🧠 TESTING LEELA CHESS ZERO (GPU TIME!)")
        print("=" * 60)

        # More interesting position for Leela
        complex_fen = "r1bqkb1r/pppp1ppp/2n2n2/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"

        leela_request = {
            "type": "analyze",
            "fen": complex_fen,
            "engine": "leela",
            "depth": 15,  # Will use nodes internally
        }

        print(f"📤 Sending request: {json.dumps(leela_request, indent=2)}")
        await websocket.send(json.dumps(leela_request))

        print("⏳ Waiting for Leela analysis... (Listen for that GPU fan! 🔥)")
        response = await websocket.recv()
        result = json.loads(response)

        print("\n📥 Leela Result:")
        print(json.dumps(result, indent=2))
        print()

        # Test 3: Server Status
        print("=" * 60)
        print("📊 CHECKING SERVER STATUS")
        print("=" * 60)

        status_request = {"type": "status"}
        await websocket.send(json.dumps(status_request))

        response = await websocket.recv()
        status = json.loads(response)

        print("📥 Server Status:")
        print(json.dumps(status, indent=2))
        print()

        print("=" * 60)
        print("✅ ALL TESTS COMPLETE!")
        print("=" * 60)


if __name__ == "__main__":
    try:
        print(
            """
╔═══════════════════════════════════════════════════════════╗
║       Chess Analysis Service - Test Client               ║
║       Testing Stockfish + Leela Chess Zero                ║
╚═══════════════════════════════════════════════════════════╝
"""
        )
        asyncio.run(test_analysis())
        print("\n🎉 Success! Your GPU should have spun up during Leela analysis!")

    except ConnectionRefusedError:
        print("❌ Error: Could not connect to server.")
        print("   Make sure the server is running on ws://localhost:8001")
    except Exception as e:
        print(f"❌ Error: {e}")
