import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from livekit.api import LiveKitAPI
from livekit.protocol.room import ListRoomsRequest

async def main():
    url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    print(f"Connecting to {url} with key {api_key}...")
    lk = LiveKitAPI(url, api_key, api_secret)
    rooms = await lk.room.list_rooms(ListRoomsRequest())
    print(f"SUCCESS! Connected to LiveKit Cloud. Active rooms: {len(rooms.rooms)}")
    await lk.aclose()

if __name__ == "__main__":
    asyncio.run(main())
