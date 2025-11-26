import asyncio
import os

import aiohttp
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FMP_API_KEY")
BASE_URL_STABLE = "https://financialmodelingprep.com/stable"
SYMBOL = "AAPL"

async def test_endpoint(session, url):
    print(f"Testing {url}...")
    try:
        async with session.get(url) as response:
            print(f"Status: {response.status}")
            if response.status == 200:
                data = await response.json()
                print(f"Data: {str(data)[:100]}...")
                return True
            else:
                print(f"Error: {await response.text()}")
                return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

async def main():
    if not API_KEY:
        print("FMP_API_KEY not found in env")
        return

    async with aiohttp.ClientSession() as session:
        # Test Historical EOD Full
        print("\n--- Test: stable/historical-price-eod/full ---")
        await test_endpoint(session, f"{BASE_URL_STABLE}/historical-price-eod/full?symbol={SYMBOL}&apikey={API_KEY}")

        # Test Historical EOD Light
        print("\n--- Test: stable/historical-price-eod/light ---")
        await test_endpoint(session, f"{BASE_URL_STABLE}/historical-price-eod/light?symbol={SYMBOL}&apikey={API_KEY}")

        # Test Intraday
        print("\n--- Test: stable/historical-chart/1hour ---")
        await test_endpoint(session, f"{BASE_URL_STABLE}/historical-chart/1hour?symbol={SYMBOL}&apikey={API_KEY}")

if __name__ == "__main__":
    asyncio.run(main())
