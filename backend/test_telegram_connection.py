
import asyncio
import os

from dotenv import load_dotenv
from telethon import TelegramClient


load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
CHANNEL = os.getenv("TELEGRAM_CHANNEL", "merntech")

SESSION_NAME = "private_storage/jobpilot_telegram"


async def main():

    if not API_ID or not API_HASH:
        raise ValueError(
            "TELEGRAM_API_ID or TELEGRAM_API_HASH is missing."
        )

    os.makedirs("private_storage", exist_ok=True)

    client = TelegramClient(
        SESSION_NAME,
        API_ID,
        API_HASH,
    )

    try:
        await client.start()

        me = await client.get_me()

        print("\nTelegram authentication successful")
        print("Connected account:", me.username or me.first_name)

        channel = await client.get_entity(CHANNEL)

        print("\nChannel access verified")
        print("Channel title:", channel.title)
        print("Channel username:", channel.username)

    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
