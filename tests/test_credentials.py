import json
import logging
import os
import pytest
import aiohttp
import ssl
import certifi


@pytest.mark.asyncio
async def test_google_maps_api_token_validity():
    with open('secrets/secrets_gmap.json') as f:
        api_key = json.load(f)["gmaps_api"]
    if not api_key:
        pytest.fail("GOOGLE_MAPS_API_KEY environment variable is not set")
    base_url = "https://places.googleapis.com/v1/places:searchNearby"
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        try:
            # Request body for Places API v1
            request_body = {
                "locationRestriction": {
                    "circle": {
                        "center": {
                            "latitude": -33.8568,
                            "longitude": 151.2153
                        },
                        "radius": 1000.0
                    }
                },
                "maxResultCount": 1  # Minimum results for a lightweight check
            }
            headers = {
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': api_key,
                'X-Goog-FieldMask': 'places.displayName,places.location'  # Minimal fields for lightweight response
            }

            async with session.post(base_url, json=request_body, headers=headers) as response:
                result = await response.json()
                if response.status != 200:
                    error_message = result.get('error', {}).get('message', 'No error message provided')
                    if response.status == 403:
                        pytest.fail(f"API request denied")
                    else:
                        pytest.fail(f"API request failed with status {response.status}: {error_message}")
                assert 'places' in result, "Response missing 'places' field"
                assert len(result['places']) > 0, "No places returned in response"
                assert 'displayName' in result['places'][0], "Place missing 'displayName'"
                assert 'location' in result['places'][0], "Place missing 'location'"
        except aiohttp.ClientError as e:
            pytest.fail(f"Failed to connect to Google Maps API: {str(e)}")


@pytest.mark.asyncio
async def test_firebase_api_key():
    with open('secrets/secrets_firebase.json') as f:
      api_key = json.load(f)['firebase_api_key']
    if not api_key:
        pytest.fail("FIREBASE_API_KEY environment variable is not set")

    base_url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
    ssl_context = ssl.create_default_context(cafile=certifi.where())

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        try:
            params = {'key': api_key}
            request_data = {
                'returnSecureToken': True,
                'email': '',  # Empty email will trigger expected validation error
                'password': ''
            }

            async with session.post(base_url, params=params, json=request_data) as response:
                result = await response.json()
                assert 'error' in result, "Expected error response for empty credentials"
                error = result['error']
                logging.error(error)
                # Check if we get the expected Firebase auth error
                assert 'message' in error, "Error response missing message field"
                assert error.get('message') in ['INVALID_EMAIL', 'MISSING_EMAIL', 'EMAIL_NOT_FOUND'], \
                    "Unexpected error message. API key might be invalid."
                assert 'code' in error, "Error response missing code field"
                assert error.get('code') in [400, 401], \
                    f"Unexpected error code: {error.get('code')}"

        except aiohttp.ClientError as e:
            pytest.fail(f"Failed to connect to Firebase API: {str(e)}")
        except AssertionError as e:
            pytest.fail(f"Invalid API key or unexpected response: {str(e)}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {str(e)}")