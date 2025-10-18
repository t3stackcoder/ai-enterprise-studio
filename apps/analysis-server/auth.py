"""
WebSocket Authentication for Analysis Server
Validates JWT tokens from the auth server
"""

import os
import logging
from urllib.parse import parse_qs
import jwt
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)


class AuthConfig:
    """Authentication configuration - must match auth-server"""
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM = "HS256"
    ISSUER = os.getenv("JWT_ISSUER", "visionscope-api")
    AUDIENCE = os.getenv("JWT_AUDIENCE", "visionscope-users")


async def authenticate_websocket(websocket: WebSocketServerProtocol) -> dict | None:
    """
    Authenticate WebSocket connection via JWT token

    Token can be passed via:
    1. Query parameter: ws://localhost:8765?token=<jwt>
    2. First message: {"type": "auth", "token": "<jwt>"}

    Returns:
        dict: Token payload if valid
        None: If authentication fails (connection will be closed)
    """

    # Try to get token from query parameters first
    query_string = websocket.request.path.split('?', 1)
    if len(query_string) > 1:
        params = parse_qs(query_string[1])
        token = params.get('token', [None])[0]

        if token:
            payload = verify_token(token)
            if payload:
                logger.info(f"WebSocket authenticated via query param: {payload.get('sub')}")
                return payload

    # If no query token, wait for auth message
    try:
        # Give client 5 seconds to send auth message
        import asyncio
        auth_message = await asyncio.wait_for(websocket.recv(), timeout=5.0)

        import json
        data = json.loads(auth_message)

        if data.get('type') == 'auth' and data.get('token'):
            payload = verify_token(data['token'])
            if payload:
                logger.info(f"WebSocket authenticated via auth message: {payload.get('sub')}")
                # Send success response
                await websocket.send(json.dumps({
                    'type': 'auth_success',
                    'user': payload.get('sub')
                }))
                return payload

        # Invalid auth message
        await websocket.send(json.dumps({
            'type': 'error',
            'message': 'Invalid authentication message'
        }))
        await websocket.close(1008, "Authentication failed")
        return None

    except TimeoutError:
        logger.warning("WebSocket auth timeout - no token provided")
        await websocket.send(json.dumps({
            'type': 'error',
            'message': 'Authentication required'
        }))
        await websocket.close(1008, "Authentication timeout")
        return None
    except Exception as e:
        logger.error(f"WebSocket auth error: {e}")
        await websocket.close(1011, "Authentication error")
        return None


def verify_token(token: str) -> dict | None:
    """
    Verify JWT token

    Args:
        token: JWT token string

    Returns:
        dict: Token payload if valid
        None: If token is invalid
    """
    try:
        payload = jwt.decode(
            token,
            AuthConfig.SECRET_KEY,
            algorithms=[AuthConfig.ALGORITHM],
            issuer=AuthConfig.ISSUER,
            audience=AuthConfig.AUDIENCE,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )

        # Verify token type
        if payload.get("type") != "access":
            logger.warning(f"Invalid token type: {payload.get('type')}")
            return None

        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None


# Subscription-based access control functions removed
# Currently all authenticated users have full access
# Add tier-based limits here when business requirements are defined
