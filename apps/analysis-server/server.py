"""
Chess Analysis Service - WebSocket Server
Handles Stockfish and Leela Chess Zero engine analysis
"""

import asyncio
import json
import logging
import os
from typing import Any

import websockets
from engine_manager import EngineManager
from websockets.server import serve
from auth import authenticate_websocket

# Load environment variables
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / ".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Store active connections
active_connections: set = set()

# Initialize engine manager
engine_manager = EngineManager()


async def handle_client(websocket):
    """Handle individual client WebSocket connection"""
    client_id = id(websocket)

    # Authenticate the connection first
    user_payload = await authenticate_websocket(websocket)
    if not user_payload:
        logger.warning(f"Client {client_id} failed authentication")
        return

    # Authentication successful
    username = user_payload.get('sub')
    user_role = user_payload.get('role', 'user')
    subscription_tier = user_payload.get('subscription_tier', 'free')

    active_connections.add(websocket)
    logger.info(f"Client {client_id} ({username}, {user_role}, {subscription_tier}) connected. Total connections: {len(active_connections)}")

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                logger.info(f"Received from {client_id} ({username}): {data.get('type', 'unknown')}")

                # Route to appropriate handler (pass user info for authorization)
                response = await handle_message(data, websocket, user_payload)

                # Send response back to client
                await websocket.send(json.dumps(response))

            except json.JSONDecodeError:
                error_response = {"type": "error", "message": "Invalid JSON format"}
                await websocket.send(json.dumps(error_response))
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                error_response = {"type": "error", "message": str(e)}
                await websocket.send(json.dumps(error_response))

    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Client {client_id} ({username}) disconnected")
    finally:
        active_connections.remove(websocket)
        logger.info(f"Total connections: {len(active_connections)}")


async def handle_message(data: dict[str, Any], websocket=None, user_payload: dict = None) -> dict[str, Any]:
    """Route and handle different message types"""
    message_type = data.get("type")

    if message_type == "analyze":
        return await handle_analyze(data, websocket, user_payload)
    elif message_type == "ping":
        return {"type": "pong", "timestamp": data.get("timestamp")}
    elif message_type == "status":
        return await handle_status()
    else:
        return {"type": "error", "message": f"Unknown message type: {message_type}"}


async def handle_analyze(data: dict[str, Any], websocket=None, user_payload: dict = None) -> dict[str, Any]:
    """Handle analysis request with authorization checks"""
    try:
        fen = data.get("fen")
        engine = data.get("engine", "stockfish").lower()
        depth = data.get("depth", 20)
        movetime = data.get("movetime")  # milliseconds
        multipv = data.get("multiPV") or data.get(
            "multipv", 1
        )  # Accept both camelCase and lowercase
        stream = data.get("stream", False)  # Enable real-time streaming
        infinite = data.get("infinite", False)  # Infinite analysis mode

        if not fen:
            return {"type": "error", "message": "FEN position required"}

        # Validate engine choice
        if engine not in ["stockfish", "leela", "lc0"]:
            return {
                "type": "error",
                "message": f"Invalid engine: {engine}. Use 'stockfish' or 'leela'",
            }

        # Normalize leela/lc0
        if engine in ["leela", "lc0"]:
            engine = "leela"

        # All authenticated users have full access (for now)
        # TODO: Add subscription-based limits when business requirements are defined

        logger.info(
            f"Analyzing with {engine}: depth={depth}, movetime={movetime}, multipv={multipv}, stream={stream}, infinite={infinite}"
        )

        # Create callback for real-time updates if streaming enabled
        update_callback = None
        if stream and websocket:

            async def send_update(update_data):
                try:
                    await websocket.send(json.dumps(update_data))
                except Exception as e:
                    logger.error(f"Error sending update: {e}")

            update_callback = send_update

        # Run analysis
        result = await engine_manager.analyze(
            fen=fen,
            engine=engine,
            depth=depth,
            movetime=movetime,
            multipv=multipv,
            update_callback=update_callback,
            infinite=infinite,
        )

        return {"type": "analysis_result", "engine": engine, "fen": fen, "result": result}

    except Exception as e:
        logger.error(f"Analysis error: {e}", exc_info=True)
        return {"type": "error", "message": f"Analysis failed: {str(e)}"}


async def handle_status() -> dict[str, Any]:
    """Return server and engine status"""
    return {
        "type": "status",
        "active_connections": len(active_connections),
        "engines": {
            "stockfish": engine_manager.stockfish_available,
            "leela": engine_manager.leela_available,
        },
    }


async def main():
    """Start the WebSocket server"""
    host = os.getenv("ANALYSIS_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("ANALYSIS_SERVER_PORT", "8765"))

    # Initialize engines
    await engine_manager.initialize()

    logger.info(f"Starting Chess Analysis Service on ws://{host}:{port}")
    logger.info(f"Stockfish available: {engine_manager.stockfish_available}")
    logger.info(f"Leela available: {engine_manager.leela_available}")

    async with serve(handle_client, host, port):
        logger.info("Server is running... Press Ctrl+C to stop")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
