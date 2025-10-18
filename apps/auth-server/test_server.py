"""
Quick test script for auth-server
Run this after starting the server to test basic functionality
"""

import asyncio
import json

import httpx


async def test_auth_server():
    """Test auth server endpoints"""
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        print("🧪 Testing Auth Server")
        print("=" * 60)

        # Test health endpoint
        print("\n1️⃣  Testing health endpoint...")
        try:
            response = await client.get(f"{base_url}/health")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
            assert response.status_code == 200
            print("   ✅ Health check passed!")
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
            return

        # Test registration
        print("\n2️⃣  Testing user registration...")
        register_data = {
            "username": "testuser",
            "password": "password123",
            "email_address": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
        }

        try:
            response = await client.post(f"{base_url}/api/auth/register", json=register_data)
            print(f"   Status: {response.status_code}")
            if response.status_code == 201:
                user_data = response.json()
                print(f"   Created user: {user_data.get('username')}")
                print("   ✅ Registration passed!")
            elif response.status_code == 400:
                print("   ℹ️  User already exists (this is OK)")
            else:
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   ❌ Registration failed: {e}")

        # Test login
        print("\n3️⃣  Testing user login...")
        login_data = {"username": "testuser", "password": "password123"}

        try:
            response = await client.post(f"{base_url}/api/auth/login", json=login_data)
            print(f"   Status: {response.status_code}")

            if response.status_code == 200:
                tokens = response.json()
                access_token = tokens["access_token"]
                print(f"   Got access token: {access_token[:50]}...")
                print("   ✅ Login passed!")

                # Test protected endpoint
                print("\n4️⃣  Testing protected endpoint...")
                response = await client.get(
                    f"{base_url}/api/user/profile",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                print(f"   Status: {response.status_code}")
                if response.status_code == 200:
                    profile = response.json()
                    print(f"   Profile: {json.dumps(profile, indent=2)}")
                    print("   ✅ Protected endpoint passed!")
                else:
                    print(f"   ❌ Protected endpoint failed: {response.text}")
            else:
                print(f"   ❌ Login failed: {response.text}")
        except Exception as e:
            print(f"   ❌ Login failed: {e}")

        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("\n📚 API Docs: http://localhost:8000/api/docs")


if __name__ == "__main__":
    print("Make sure the auth server is running on http://localhost:8000")
    print("Starting tests in 2 seconds...\n")

    import time

    time.sleep(2)

    asyncio.run(test_auth_server())
